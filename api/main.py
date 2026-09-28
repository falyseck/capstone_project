"""
FastAPI application for the PPD risk screening system.

Endpoints map directly onto the two sequence diagrams in section 3.6.4 of the proposal:

  Mother flow (3.6.4.a):
    POST /auth/register        - mother registers, picks her facility
    POST /auth/login           - mother logs in
    POST /screening/submit     - submits form -> saves form -> predicts -> checks
                                  self-harm -> saves prediction + crisis check -> returns
                                  result, recommendation, and crisis message if flagged
    GET  /screening/history    - a mother's own screening history

  Healthcare worker flow (3.6.4.b):
    POST /auth/register        - healthcare worker registers, picks their facility
    POST /auth/login           - healthcare worker logs in
    GET  /healthcare/patients  - list of mothers linked to the worker's own facility only
    GET  /healthcare/patients/{mother_id}/history - one mother's full screening history
    POST /healthcare/patients/{mother_id}/report  - generates and saves a report
"""
import json
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import auth
import ml_service
import models as m
import schemas as s
from database import Base, SessionLocal, engine, get_db

app = FastAPI(
    title="PPD Risk Screening API",
    description="Backend for the postpartum depression risk screening system.",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

    # Seed a couple of demo facilities and register the trained model's metadata,
    # so the API is immediately usable after a fresh install.
    db: Session = SessionLocal()
    try:
        if db.query(m.Facility).count() == 0:
            db.add_all([
                m.Facility(name="Centre de Sante Dakar Nord", location="Dakar"),
                m.Facility(name="Centre de Sante Pikine", location="Pikine"),
            ])
            db.commit()

        if db.query(m.MLModel).count() == 0:
            meta = ml_service.model_metadata()
            db.add(m.MLModel(
                algorithm_name=meta["model_name"],
                version="v1",
                accuracy=None,
            ))
            db.commit()
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------- facilities

@app.get("/facilities", response_model=List[s.FacilityOut])
def list_facilities(db: Session = Depends(get_db)):
    return db.query(m.Facility).all()


# ---------------------------------------------------------------- auth

@app.post("/auth/register", response_model=s.UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: s.UserRegister, db: Session = Depends(get_db)):
    if db.query(m.User).filter(m.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")

    facility = db.query(m.Facility).filter(m.Facility.id == payload.facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found.")

    user = m.User(
        name=payload.name,
        email=payload.email,
        hashed_password=auth.hash_password(payload.password),
        role=payload.role,
        facility_id=payload.facility_id,
        date_of_birth=payload.date_of_birth,
        delivery_date=payload.delivery_date,
        license_id=payload.license_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=s.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(m.User).filter(m.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth.create_access_token(data={"sub": user.id, "role": user.role.value})
    return s.Token(access_token=token)


# ---------------------------------------------------------------- mother flow

@app.post("/screening/submit", response_model=s.PredictionOut)
def submit_screening(
    payload: s.ScreeningFormIn,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(auth.require_role(m.RoleEnum.mother)),
):
    # 1. save the form
    form = m.ScreeningForm(
        mother_id=current_user.id,
        responses=json.dumps(payload.model_dump()),
    )
    db.add(form)
    db.flush()  # get form.id without committing yet

    # 2. ML model prediction (self-harm item is never passed to the model)
    risk_level, probability_score = ml_service.predict_risk(payload.model_dump())
    recommendation_text = ml_service.recommendation_for(risk_level)

    latest_model = db.query(m.MLModel).order_by(m.MLModel.trained_at.desc()).first()

    prediction = m.PredictionResult(
        form_id=form.id,
        risk_level=risk_level,
        probability_score=probability_score,
        recommendation_text=recommendation_text,
        model_version=latest_model.id if latest_model else None,
    )
    db.add(prediction)

    # 3. separate, rule-based self-harm / crisis check
    flagged = ml_service.check_self_harm(payload.model_dump())
    crisis_check = m.CrisisCheck(form_id=form.id, flagged=flagged)
    db.add(crisis_check)

    db.commit()
    db.refresh(prediction)

    return s.PredictionOut(
        form_id=form.id,
        risk_level=risk_level,
        probability_score=probability_score,
        recommendation_text=recommendation_text,
        crisis_flagged=flagged,
        crisis_message=ml_service.CRISIS_MESSAGE if flagged else None,
        predicted_at=prediction.predicted_at,
    )


@app.get("/screening/history", response_model=List[s.ScreeningHistoryItem])
def my_screening_history(
    db: Session = Depends(get_db),
    current_user: m.User = Depends(auth.require_role(m.RoleEnum.mother)),
):
    forms = (
        db.query(m.ScreeningForm)
        .filter(m.ScreeningForm.mother_id == current_user.id)
        .order_by(m.ScreeningForm.submission_date.desc())
        .all()
    )
    return [_history_item(f) for f in forms if f.prediction and f.crisis_check]


# ---------------------------------------------------------------- healthcare worker flow

def _get_mother_in_same_facility(mother_id: str, worker: m.User, db: Session) -> m.User:
    mother = db.query(m.User).filter(m.User.id == mother_id).first()
    if not mother or mother.role != m.RoleEnum.mother:
        raise HTTPException(status_code=404, detail="Mother not found.")
    if mother.facility_id != worker.facility_id:
        # A healthcare worker can only see mothers linked to their own facility.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This mother is not linked to your facility.",
        )
    return mother


def _history_item(form: m.ScreeningForm) -> s.ScreeningHistoryItem:
    return s.ScreeningHistoryItem(
        form_id=form.id,
        submission_date=form.submission_date,
        risk_level=form.prediction.risk_level,
        probability_score=form.prediction.probability_score,
        crisis_flagged=form.crisis_check.flagged,
    )


@app.get("/healthcare/patients", response_model=List[s.PatientSummary])
def list_patients(
    db: Session = Depends(get_db),
    current_user: m.User = Depends(auth.require_role(m.RoleEnum.healthcare_worker)),
):
    mothers = (
        db.query(m.User)
        .filter(m.User.role == m.RoleEnum.mother, m.User.facility_id == current_user.facility_id)
        .all()
    )

    summaries = []
    for mother in mothers:
        forms = sorted(mother.screening_forms, key=lambda f: f.submission_date, reverse=True)
        latest = forms[0] if forms else None
        summaries.append(s.PatientSummary(
            mother_id=mother.id,
            name=mother.name,
            latest_risk_level=latest.prediction.risk_level if latest and latest.prediction else None,
            latest_submission_date=latest.submission_date if latest else None,
            total_screenings=len(forms),
        ))
    return summaries


@app.get(
    "/healthcare/patients/{mother_id}/history",
    response_model=List[s.ScreeningHistoryItem],
)
def patient_history(
    mother_id: str,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(auth.require_role(m.RoleEnum.healthcare_worker)),
):
    mother = _get_mother_in_same_facility(mother_id, current_user, db)
    forms = sorted(mother.screening_forms, key=lambda f: f.submission_date, reverse=True)
    return [_history_item(f) for f in forms if f.prediction and f.crisis_check]


@app.post("/healthcare/patients/{mother_id}/report", response_model=s.ReportOut)
def generate_report(
    mother_id: str,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(auth.require_role(m.RoleEnum.healthcare_worker)),
):
    mother = _get_mother_in_same_facility(mother_id, current_user, db)
    forms = sorted(mother.screening_forms, key=lambda f: f.submission_date, reverse=True)

    if not forms:
        raise HTTPException(status_code=404, detail="This mother has no screenings yet.")

    lines = [f"Screening report for {mother.name} ({len(forms)} screening(s) on record)", ""]
    for f in forms:
        if f.prediction:
            lines.append(
                f"- {f.submission_date:%Y-%m-%d}: risk={f.prediction.risk_level.value}, "
                f"probability={f.prediction.probability_score:.2f}, "
                f"crisis_flag={f.crisis_check.flagged if f.crisis_check else 'n/a'}"
            )
    content = "\n".join(lines)

    report = m.Report(
        mother_id=mother.id,
        generated_by=current_user.id,
        content=content,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

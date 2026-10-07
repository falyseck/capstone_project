import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import auth
import ml_service
import models as m
import schemas as s
from database import Base, SessionLocal, engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(m.Facility).count() == 0:
            db.add_all([
                m.Facility(name="Centre de Sante Dakar Nord", location="Dakar"),
                m.Facility(name="Centre de Sante Pikine", location="Pikine"),
            ])
        if db.query(m.MLModel).count() == 0:
            try:
                model_name, trained_on = ml_service.model_metadata()
            except RuntimeError:
                model_name, trained_on = "not_trained_yet", "n/a"
            db.add(m.MLModel(algorithm_name=model_name, version="v1", accuracy=None))
        db.commit()
    finally:
        db.close()
    yield


app = FastAPI(title="PPD Risk Screening API", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/facilities", response_model=List[s.FacilityOut])
def list_facilities(db: Session = Depends(get_db)):
    return db.query(m.Facility).all()


@app.post("/auth/register", response_model=s.UserOut, status_code=201)
def register(payload: s.UserRegister, db: Session = Depends(get_db)):
    existing = db.query(m.User).filter(m.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    facility = db.query(m.Facility).filter(m.Facility.id == payload.facility_id).first()
    if not facility:
        raise HTTPException(status_code=400, detail="Facility not found.")

    user = m.User(
        name=payload.name,
        email=payload.email,
        hashed_password=auth.hash_password(payload.password),
        role=m.RoleEnum(payload.role),
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
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = auth.create_access_token({"sub": user.id, "role": user.role.value})
    return s.Token(access_token=token, role=user.role.value, user_id=user.id, name=user.name)


def _history_item(form: m.ScreeningForm) -> s.ScreeningHistoryItem:
    risk_level = form.prediction.risk_level.value if form.prediction else None
    probability_score = form.prediction.probability_score if form.prediction else None
    crisis_flagged = form.crisis_check.flagged if form.crisis_check else None

    # The most recent independent clinical assessment for this screening, if any.
    # clinical_assessments is already ordered newest-first (see models.py).
    latest_assessment = form.clinical_assessments[0] if form.clinical_assessments else None
    clinical_risk_level = latest_assessment.risk_level.value if latest_assessment else None
    clinical_notes = latest_assessment.notes if latest_assessment else None

    return s.ScreeningHistoryItem(
        form_id=form.id,
        submission_date=form.submission_date,
        risk_level=risk_level,
        probability_score=probability_score,
        crisis_flagged=crisis_flagged,
        clinical_risk_level=clinical_risk_level,
        clinical_notes=clinical_notes,
    )


@app.post("/screening/submit", response_model=s.PredictionOut)
def submit_screening(
    payload: s.ScreeningFormIn,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(auth.require_role(m.RoleEnum.mother)),
):
    responses = payload.model_dump()

    form = m.ScreeningForm(mother_id=current_user.id, responses=json.dumps(responses))
    db.add(form)
    db.flush()  # get form.id without committing yet

    risk_level, probability_score = ml_service.predict_risk(responses)
    recommendation_text = ml_service.recommendation_for(risk_level)

    latest_model = db.query(m.MLModel).order_by(m.MLModel.trained_at.desc()).first()

    prediction = m.PredictionResult(
        form_id=form.id,
        risk_level=m.RiskLevelEnum(risk_level),
        probability_score=probability_score,
        recommendation_text=recommendation_text,
        model_version=latest_model.id if latest_model else None,
    )
    db.add(prediction)

    flagged = ml_service.check_self_harm(responses)
    crisis = m.CrisisCheck(form_id=form.id, flagged=flagged)
    db.add(crisis)

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
def screening_history(
    db: Session = Depends(get_db),
    current_user: m.User = Depends(auth.require_role(m.RoleEnum.mother)),
):
    forms = (
        db.query(m.ScreeningForm)
        .filter(m.ScreeningForm.mother_id == current_user.id)
        .order_by(m.ScreeningForm.submission_date.desc())
        .all()
    )
    return [_history_item(f) for f in forms]


def _get_mother_in_same_facility(mother_id: str, worker: m.User, db: Session) -> m.User:
    mother = db.query(m.User).filter(m.User.id == mother_id).first()
    if not mother or mother.role != m.RoleEnum.mother:
        raise HTTPException(status_code=404, detail="Mother not found.")
    if mother.facility_id != worker.facility_id:
        raise HTTPException(
            status_code=403,
            detail="You can only access mothers registered at your own facility.",
        )
    return mother


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
        forms = (
            db.query(m.ScreeningForm)
            .filter(m.ScreeningForm.mother_id == mother.id)
            .order_by(m.ScreeningForm.submission_date.desc())
            .all()
        )
        latest_risk = None
        if forms and forms[0].prediction:
            latest_risk = forms[0].prediction.risk_level.value
        summaries.append(
            s.PatientSummary(
                mother_id=mother.id,
                name=mother.name,
                email=mother.email,
                latest_risk_level=latest_risk,
                total_screenings=len(forms),
            )
        )
    return summaries


@app.get("/healthcare/patients/{mother_id}/history", response_model=List[s.ScreeningHistoryItem])
def patient_history(
    mother_id: str,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(auth.require_role(m.RoleEnum.healthcare_worker)),
):
    _get_mother_in_same_facility(mother_id, current_user, db)
    forms = (
        db.query(m.ScreeningForm)
        .filter(m.ScreeningForm.mother_id == mother_id)
        .order_by(m.ScreeningForm.submission_date.desc())
        .all()
    )
    return [_history_item(f) for f in forms]


@app.post(
    "/healthcare/screenings/{form_id}/assessment",
    response_model=s.ClinicalAssessmentOut,
    status_code=201,
)
def add_clinical_assessment(
    form_id: str,
    payload: s.ClinicalAssessmentIn,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(auth.require_role(m.RoleEnum.healthcare_worker)),
):
    """
    Records a healthcare worker's independent risk judgment for a screening — deliberately
    separate from the ML prediction on the same form. See models.ClinicalAssessment for why:
    this is what lets future real-world data escape the circular-label problem found in the
    training dataset (Chapter Four / notebook Section 4b).
    """
    form = db.query(m.ScreeningForm).filter(m.ScreeningForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Screening not found.")

    # Reuses the same facility-scoping rule as every other healthcare-worker endpoint.
    _get_mother_in_same_facility(form.mother_id, current_user, db)

    assessment = m.ClinicalAssessment(
        form_id=form_id,
        worker_id=current_user.id,
        risk_level=m.RiskLevelEnum(payload.risk_level),
        notes=payload.notes,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@app.post("/healthcare/patients/{mother_id}/report", response_model=s.ReportOut)
def generate_report(
    mother_id: str,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(auth.require_role(m.RoleEnum.healthcare_worker)),
):
    mother = _get_mother_in_same_facility(mother_id, current_user, db)
    forms = (
        db.query(m.ScreeningForm)
        .filter(m.ScreeningForm.mother_id == mother_id)
        .order_by(m.ScreeningForm.submission_date.desc())
        .all()
    )

    lines = [f"Screening report for {mother.name} ({mother.email})", f"Generated at: {datetime.utcnow().isoformat()}", ""]
    if not forms:
        lines.append("No screenings on record yet.")
    for f in forms:
        risk = f.prediction.risk_level.value if f.prediction else "n/a"
        crisis = "YES" if (f.crisis_check and f.crisis_check.flagged) else "No"
        line = f"- {f.submission_date.isoformat()}: ML risk={risk}, crisis_flag={crisis}"
        if f.clinical_assessments:
            latest = f.clinical_assessments[0]
            line += f", clinical assessment={latest.risk_level.value}"
            if latest.notes:
                line += f" ({latest.notes})"
        lines.append(line)

    content = "\n".join(lines)
    report = m.Report(mother_id=mother_id, generated_by=current_user.id, content=content)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

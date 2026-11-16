from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import auth
import models as m
import schemas as s
from database import get_db
from dependencies import forms_for_mother, history_item, mother_in_same_facility

router = APIRouter(prefix="/healthcare")

worker_only = auth.require_role(m.RoleEnum.healthcare_worker)


@router.get("/patients", response_model=List[s.PatientSummary])
def list_patients(db: Session = Depends(get_db), current_user: m.User = Depends(worker_only)):
    mothers = (
        db.query(m.User)
        .filter(m.User.role == m.RoleEnum.mother, m.User.facility_id == current_user.facility_id)
        .all()
    )
    summaries = []
    for mother in mothers:
        forms = forms_for_mother(db, mother.id)
        latest = forms[0].prediction.risk_level.value if forms and forms[0].prediction else None
        summaries.append(s.PatientSummary(
            mother_id=mother.id, name=mother.name, email=mother.email,
            latest_risk_level=latest, total_screenings=len(forms),
        ))
    return summaries


@router.get("/patients/{mother_id}/history", response_model=List[s.ScreeningHistoryItem])
def patient_history(mother_id: str, db: Session = Depends(get_db), current_user: m.User = Depends(worker_only)):
    mother_in_same_facility(mother_id, current_user, db)
    return [history_item(f) for f in forms_for_mother(db, mother_id)]


@router.post("/screenings/{form_id}/assessment", response_model=s.ClinicalAssessmentOut, status_code=201)
def add_clinical_assessment(
    form_id: str,
    payload: s.ClinicalAssessmentIn,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(worker_only),
):
    """Records a worker's independent risk judgment, deliberately separate from the ML prediction
    (see models.ClinicalAssessment). This is the non-circular label for future retraining."""
    form = db.query(m.ScreeningForm).filter(m.ScreeningForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Screening not found.")
    mother_in_same_facility(form.mother_id, current_user, db)

    assessment = m.ClinicalAssessment(
        form_id=form_id, worker_id=current_user.id,
        risk_level=m.RiskLevelEnum(payload.risk_level), notes=payload.notes,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.post("/patients/{mother_id}/report", response_model=s.ReportOut)
def generate_report(mother_id: str, db: Session = Depends(get_db), current_user: m.User = Depends(worker_only)):
    mother = mother_in_same_facility(mother_id, current_user, db)
    forms = forms_for_mother(db, mother_id)

    lines = [f"Screening report for {mother.name} ({mother.email})",
             f"Generated at: {datetime.utcnow().isoformat()}", ""]
    if not forms:
        lines.append("No screenings on record yet.")
    for f in forms:
        risk = f.prediction.risk_level.value if f.prediction else "n/a"
        ml = f.prediction.ml_risk_level.value if f.prediction and f.prediction.ml_risk_level else risk
        crisis = "YES" if (f.crisis_check and f.crisis_check.flagged) else "No"
        line = f"- {f.submission_date.isoformat()}: risk={risk} (model={ml}), crisis_flag={crisis}"
        if f.clinical_assessments:
            latest = f.clinical_assessments[0]
            line += f", clinical assessment={latest.risk_level.value}"
            if latest.notes:
                line += f" ({latest.notes})"
        lines.append(line)

    report = m.Report(mother_id=mother_id, generated_by=current_user.id, content="\n".join(lines))
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

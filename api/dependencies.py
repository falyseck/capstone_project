"""Shared FastAPI dependencies and data-access helpers used by several routers."""
import json

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

import models as m
import schemas as s
from risk_engine import ScreeningEngine, build_default_engine

_engine = None


def get_engine() -> ScreeningEngine:
    """One shared engine per process (the model is loaded once). Overridable in tests via
    app.dependency_overrides[get_engine]."""
    global _engine
    if _engine is None:
        _engine = build_default_engine()
    return _engine


def forms_for_mother(db: Session, mother_id: str):
    return (
        db.query(m.ScreeningForm)
        .filter(m.ScreeningForm.mother_id == mother_id)
        .order_by(m.ScreeningForm.submission_date.desc())
        .all()
    )


def history_item(form: m.ScreeningForm) -> s.ScreeningHistoryItem:
    # clinical_assessments is ordered newest-first (see models.py)
    latest = form.clinical_assessments[0] if form.clinical_assessments else None
    return s.ScreeningHistoryItem(
        form_id=form.id,
        submission_date=form.submission_date,
        responses=json.loads(form.responses),
        risk_level=form.prediction.risk_level.value if form.prediction else None,
        probability_score=form.prediction.probability_score if form.prediction else None,
        crisis_flagged=form.crisis_check.flagged if form.crisis_check else None,
        clinical_risk_level=latest.risk_level.value if latest else None,
        clinical_notes=latest.notes if latest else None,
    )


def mother_in_same_facility(mother_id: str, worker: m.User, db: Session) -> m.User:
    mother = db.query(m.User).filter(m.User.id == mother_id).first()
    if not mother or mother.role != m.RoleEnum.mother:
        raise HTTPException(status_code=404, detail="Mother not found.")
    if mother.facility_id != worker.facility_id:
        raise HTTPException(status_code=403, detail="You can only access mothers registered at your own facility.")
    return mother

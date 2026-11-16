import json
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import auth
import models as m
import schemas as s
from database import get_db
from dependencies import forms_for_mother, get_engine, history_item
from risk_engine import ScreeningEngine

router = APIRouter(prefix="/screening")

mother_only = auth.require_role(m.RoleEnum.mother)


@router.post("/submit", response_model=s.PredictionOut)
def submit_screening(
    payload: s.ScreeningFormIn,
    db: Session = Depends(get_db),
    current_user: m.User = Depends(mother_only),
    engine: ScreeningEngine = Depends(get_engine),
):
    responses = payload.model_dump()
    form = m.ScreeningForm(mother_id=current_user.id, responses=json.dumps(responses))
    db.add(form)
    db.flush()  # get form.id without committing yet

    # Prediction + safety rule live in the engine; this endpoint only persists the outcome.
    result = engine.assess(responses)
    latest_model = db.query(m.MLModel).order_by(m.MLModel.trained_at.desc()).first()

    prediction = m.PredictionResult(
        form_id=form.id,
        risk_level=m.RiskLevelEnum(result.risk_level),
        ml_risk_level=m.RiskLevelEnum(result.ml_risk_level),
        probability_score=result.probability_score,
        recommendation_text=result.recommendation_text,
        model_version=latest_model.id if latest_model else None,
    )
    db.add(prediction)
    db.add(m.CrisisCheck(form_id=form.id, flagged=result.crisis_flagged))
    db.commit()
    db.refresh(prediction)

    return s.PredictionOut(
        form_id=form.id,
        risk_level=result.risk_level,
        ml_risk_level=result.ml_risk_level,
        probability_score=result.probability_score,
        recommendation_text=result.recommendation_text,
        crisis_flagged=result.crisis_flagged,
        crisis_message=result.crisis_message,
        predicted_at=prediction.predicted_at,
    )


@router.get("/history", response_model=List[s.ScreeningHistoryItem])
def screening_history(db: Session = Depends(get_db), current_user: m.User = Depends(mother_only)):
    return [history_item(f) for f in forms_for_mother(db, current_user.id)]

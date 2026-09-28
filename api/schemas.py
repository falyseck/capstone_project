"""
Pydantic schemas — these define the API's request/response shapes and double as
validation (functional requirement 3.2.1 #4: "validate the form and reject incomplete
submissions").
"""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

Level = Literal["No", "Sometimes", "Yes"]
AgeBracket = Literal["25-30", "30-35", "35-40", "40-45", "45-50"]
Role = Literal["mother", "healthcare_worker"]
RiskLevel = Literal["low", "medium", "high"]


# ---------- Facility ----------

class FacilityOut(BaseModel):
    id: str
    name: str
    location: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Auth / Users ----------

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: Role
    facility_id: str
    # mother-only, optional
    date_of_birth: Optional[str] = None
    delivery_date: Optional[str] = None
    # healthcare-worker-only, optional
    license_id: Optional[str] = None


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Role
    facility_id: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Screening form ----------

class ScreeningFormIn(BaseModel):
    """
    The screening form a mother fills out. All 9 fields (8 symptom items + the
    self-harm item) plus age are required — an incomplete submission is rejected
    automatically by Pydantic before it ever reaches the prediction logic.
    """
    age_bracket: AgeBracket
    feeling_sad: Level
    irritable: Level
    trouble_sleeping: Level
    trouble_concentrating: Level
    appetite_changes: Level
    feeling_anxious: Level
    feeling_guilty: Level
    bonding_difficulty: Level
    self_harm_thoughts: Level


class PredictionOut(BaseModel):
    form_id: str
    risk_level: RiskLevel
    probability_score: float
    recommendation_text: str
    crisis_flagged: bool
    crisis_message: Optional[str] = None
    predicted_at: datetime

    class Config:
        from_attributes = True


class ScreeningHistoryItem(BaseModel):
    form_id: str
    submission_date: datetime
    risk_level: RiskLevel
    probability_score: float
    crisis_flagged: bool

    class Config:
        from_attributes = True


class PatientSummary(BaseModel):
    mother_id: str
    name: str
    latest_risk_level: Optional[RiskLevel] = None
    latest_submission_date: Optional[datetime] = None
    total_screenings: int


# ---------- Reports ----------

class ReportOut(BaseModel):
    id: str
    mother_id: str
    generated_by: str
    generated_at: datetime
    content: str

    class Config:
        from_attributes = True

"""
Pydantic schemas — these define the API's request/response shapes and double as
validation (functional requirement 3.2.1 #4: "validate the form and reject incomplete
submissions").
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

LevelLiteral = Literal["No", "Sometimes", "Yes"]
AgeBracket = Literal["25-30", "30-35", "35-40", "40-45", "45-50"]
Role = Literal["mother", "healthcare_worker"]
RiskLevel = Literal["low", "medium", "high"]


def _unwrap_enum(v):
    """SQLAlchemy returns Enum members (e.g. RoleEnum.mother); pydantic's
    Literal validator rejects them even though they're str subclasses.
    This pulls out the plain string value before validation runs."""
    return v.value if hasattr(v, "value") else v


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

    @field_validator("role", mode="before")
    @classmethod
    def _coerce_role(cls, v):
        return _unwrap_enum(v)

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    user_id: str
    name: str

    @field_validator("role", mode="before")
    @classmethod
    def _coerce_role(cls, v):
        return _unwrap_enum(v)


# ---------- Screening form ----------

class ScreeningFormIn(BaseModel):
    """
    The screening form a mother fills out. All 9 fields (8 symptom items + the
    self-harm item) plus age are required — an incomplete submission is rejected
    automatically by Pydantic before it ever reaches the prediction logic.
    """
    age_bracket: AgeBracket
    feeling_sad: LevelLiteral
    irritable: LevelLiteral
    trouble_sleeping: LevelLiteral
    trouble_concentrating: LevelLiteral
    appetite_changes: LevelLiteral
    feeling_anxious: LevelLiteral
    feeling_guilty: LevelLiteral
    bonding_difficulty: LevelLiteral
    self_harm_thoughts: LevelLiteral


class PredictionOut(BaseModel):
    form_id: str
    risk_level: RiskLevel
    probability_score: float
    recommendation_text: str
    crisis_flagged: bool
    crisis_message: Optional[str] = None
    predicted_at: datetime

    @field_validator("risk_level", mode="before")
    @classmethod
    def _coerce_risk_level(cls, v):
        return _unwrap_enum(v)

    class Config:
        from_attributes = True


class ScreeningHistoryItem(BaseModel):
    form_id: str
    submission_date: datetime
    risk_level: Optional[RiskLevel] = None
    probability_score: Optional[float] = None
    crisis_flagged: Optional[bool] = None
    # The healthcare worker's own independent judgment for this screening, if one has been
    # recorded — deliberately separate from risk_level (the ML prediction) above.
    clinical_risk_level: Optional[RiskLevel] = None
    clinical_notes: Optional[str] = None

    @field_validator("risk_level", "clinical_risk_level", mode="before")
    @classmethod
    def _coerce_risk_level(cls, v):
        return _unwrap_enum(v)

    class Config:
        from_attributes = True


# ---------- Clinical assessment ----------

class ClinicalAssessmentIn(BaseModel):
    """A healthcare worker's independent risk judgment for a screening, recorded separately
    from the ML prediction. Over time, (screening form responses -> clinical_risk_level) pairs
    form a non-circular labeled dataset for a future retrain — unlike the current training
    label, this one isn't derived from the same features used as model input."""
    risk_level: RiskLevel
    notes: Optional[str] = None


class ClinicalAssessmentOut(BaseModel):
    id: str
    form_id: str
    worker_id: str
    risk_level: RiskLevel
    notes: Optional[str] = None
    assessed_at: datetime

    @field_validator("risk_level", mode="before")
    @classmethod
    def _coerce_risk_level(cls, v):
        return _unwrap_enum(v)

    class Config:
        from_attributes = True


class PatientSummary(BaseModel):
    mother_id: str
    name: str
    email: EmailStr
    latest_risk_level: Optional[RiskLevel] = None
    latest_submission_date: Optional[datetime] = None
    total_screenings: int

    @field_validator("latest_risk_level", mode="before")
    @classmethod
    def _coerce_latest_risk_level(cls, v):
        return _unwrap_enum(v)


# ---------- Reports ----------

class ReportOut(BaseModel):
    id: str
    mother_id: str
    generated_by: str
    generated_at: datetime
    content: str

    class Config:
        from_attributes = True

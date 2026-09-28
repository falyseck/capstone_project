"""
SQLAlchemy ORM models.

These map directly onto the ERD in section 3.6.3 and the class diagram in section 3.6.2
of the capstone proposal:

    facilities  ->  Facility
    users       ->  User            (Mother and HealthcareWorker share this table,
                                      distinguished by the `role` column, matching the
                                      User -> Mother / User -> HealthcareWorker
                                      inheritance in the class diagram)
    screening_forms -> ScreeningForm
    predictions     -> PredictionResult
    crisis_checks   -> CrisisCheck
    models          -> MLModel      (metadata about the trained model, not the model
                                      file itself, which lives in trained_model/)
    reports         -> Report
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship

from database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class RoleEnum(str, enum.Enum):
    mother = "mother"
    healthcare_worker = "healthcare_worker"


class RiskLevelEnum(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Facility(Base):
    __tablename__ = "facilities"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    location = Column(String, nullable=True)

    users = relationship("User", back_populates="facility")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)
    facility_id = Column(String, ForeignKey("facilities.id"), nullable=False)
    created_at = Column(DateTime, default=_now)

    # Mother-only fields (nullable for healthcare workers)
    date_of_birth = Column(String, nullable=True)
    delivery_date = Column(String, nullable=True)

    # HealthcareWorker-only field (nullable for mothers)
    license_id = Column(String, nullable=True)

    facility = relationship("Facility", back_populates="users")
    screening_forms = relationship("ScreeningForm", back_populates="mother")
    reports_received = relationship(
        "Report", back_populates="mother", foreign_keys="Report.mother_id"
    )
    reports_generated = relationship(
        "Report", back_populates="generated_by_user", foreign_keys="Report.generated_by"
    )


class ScreeningForm(Base):
    __tablename__ = "screening_forms"

    id = Column(String, primary_key=True, default=_uuid)
    mother_id = Column(String, ForeignKey("users.id"), nullable=False)
    responses = Column(Text, nullable=False)  # JSON-encoded form answers
    submission_date = Column(DateTime, default=_now)

    mother = relationship("User", back_populates="screening_forms")
    prediction = relationship(
        "PredictionResult", back_populates="form", uselist=False
    )
    crisis_check = relationship(
        "CrisisCheck", back_populates="form", uselist=False
    )


class MLModel(Base):
    __tablename__ = "models"

    id = Column(String, primary_key=True, default=_uuid)
    algorithm_name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    accuracy = Column(Float, nullable=True)
    trained_at = Column(DateTime, default=_now)

    predictions = relationship("PredictionResult", back_populates="model")


class PredictionResult(Base):
    __tablename__ = "predictions"

    id = Column(String, primary_key=True, default=_uuid)
    form_id = Column(String, ForeignKey("screening_forms.id"), nullable=False, unique=True)
    risk_level = Column(Enum(RiskLevelEnum), nullable=False)
    probability_score = Column(Float, nullable=False)
    recommendation_text = Column(Text, nullable=False)
    model_version = Column(String, ForeignKey("models.id"), nullable=True)
    predicted_at = Column(DateTime, default=_now)

    form = relationship("ScreeningForm", back_populates="prediction")
    model = relationship("MLModel", back_populates="predictions")


class CrisisCheck(Base):
    __tablename__ = "crisis_checks"

    id = Column(String, primary_key=True, default=_uuid)
    form_id = Column(String, ForeignKey("screening_forms.id"), nullable=False, unique=True)
    flagged = Column(Boolean, nullable=False)
    checked_at = Column(DateTime, default=_now)

    form = relationship("ScreeningForm", back_populates="crisis_check")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=_uuid)
    mother_id = Column(String, ForeignKey("users.id"), nullable=False)
    generated_by = Column(String, ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime, default=_now)
    content = Column(Text, nullable=False)

    mother = relationship("User", back_populates="reports_received", foreign_keys=[mother_id])
    generated_by_user = relationship(
        "User", back_populates="reports_generated", foreign_keys=[generated_by]
    )

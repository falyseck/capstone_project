import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Enum
)
from sqlalchemy.orm import relationship

from database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.utcnow()


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

    # mother-only fields
    date_of_birth = Column(String, nullable=True)
    delivery_date = Column(String, nullable=True)

    # healthcare-worker-only field
    license_id = Column(String, nullable=True)

    facility = relationship("Facility", back_populates="users")
    screening_forms = relationship(
        "ScreeningForm", back_populates="mother", foreign_keys="ScreeningForm.mother_id"
    )
    reports_received = relationship(
        "Report", back_populates="mother", foreign_keys="Report.mother_id"
    )
    reports_generated = relationship(
        "Report", back_populates="worker", foreign_keys="Report.generated_by"
    )


class ScreeningForm(Base):
    __tablename__ = "screening_forms"

    id = Column(String, primary_key=True, default=_uuid)
    mother_id = Column(String, ForeignKey("users.id"), nullable=False)
    responses = Column(Text, nullable=False)  # JSON-encoded
    submission_date = Column(DateTime, default=_now)

    mother = relationship("User", back_populates="screening_forms", foreign_keys=[mother_id])
    prediction = relationship("PredictionResult", back_populates="form", uselist=False)
    crisis_check = relationship("CrisisCheck", back_populates="form", uselist=False)
    clinical_assessments = relationship(
        "ClinicalAssessment", back_populates="form", order_by="ClinicalAssessment.assessed_at.desc()"
    )


class MLModel(Base):
    __tablename__ = "ml_models"

    id = Column(String, primary_key=True, default=_uuid)
    algorithm_name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    accuracy = Column(Float, nullable=True)
    trained_at = Column(DateTime, default=_now)


class PredictionResult(Base):
    __tablename__ = "prediction_results"

    id = Column(String, primary_key=True, default=_uuid)
    form_id = Column(String, ForeignKey("screening_forms.id"), unique=True, nullable=False)
    risk_level = Column(Enum(RiskLevelEnum), nullable=False)
    probability_score = Column(Float, nullable=False)
    recommendation_text = Column(Text, nullable=False)
    model_version = Column(String, ForeignKey("ml_models.id"), nullable=True)
    predicted_at = Column(DateTime, default=_now)

    form = relationship("ScreeningForm", back_populates="prediction")


class CrisisCheck(Base):
    __tablename__ = "crisis_checks"

    id = Column(String, primary_key=True, default=_uuid)
    form_id = Column(String, ForeignKey("screening_forms.id"), unique=True, nullable=False)
    flagged = Column(Boolean, nullable=False)
    checked_at = Column(DateTime, default=_now)

    form = relationship("ScreeningForm", back_populates="crisis_check")


class ClinicalAssessment(Base):
    """
    An independent risk judgment recorded by a healthcare worker after reviewing a mother,
    deliberately kept separate from the ML prediction on the same screening form. This is
    what lets future real-world data avoid the circularity found in the training dataset
    (where the label was a deterministic function of the same features used as model input):
    here, the assessment is an outcome a clinician arrived at independently, not derived from
    the form's own answers, so a (form responses -> clinical_assessment.risk_level) pair is a
    genuine, non-circular training example for a future retrain.
    """
    __tablename__ = "clinical_assessments"

    id = Column(String, primary_key=True, default=_uuid)
    form_id = Column(String, ForeignKey("screening_forms.id"), nullable=False)
    worker_id = Column(String, ForeignKey("users.id"), nullable=False)
    risk_level = Column(Enum(RiskLevelEnum), nullable=False)
    notes = Column(Text, nullable=True)
    assessed_at = Column(DateTime, default=_now)

    form = relationship("ScreeningForm", back_populates="clinical_assessments")
    worker = relationship("User", foreign_keys=[worker_id])


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=_uuid)
    mother_id = Column(String, ForeignKey("users.id"), nullable=False)
    generated_by = Column(String, ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime, default=_now)
    content = Column(Text, nullable=False)

    mother = relationship("User", back_populates="reports_received", foreign_keys=[mother_id])
    worker = relationship("User", back_populates="reports_generated", foreign_keys=[generated_by])

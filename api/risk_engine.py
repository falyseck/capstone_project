"""
Screening engine: the framework-free core of the system (no FastAPI, no database).

Design (SOLID):
  * ModelBundle      loads and caches the trained artefact (single responsibility).
  * FeatureEncoder   turns form answers into the model's numeric row (single responsibility).
  * RiskClassifier   abstract interface; SklearnRiskClassifier is the production implementation,
                     tests inject a fake one (open/closed, dependency inversion).
  * CrisisPolicy     abstract interface; SelfHarmPolicy is the production rule (polymorphism).
  * ScreeningEngine  combines classifier + crisis policy + recommendations into one result.
"""
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Tuple

import joblib
import pandas as pd

DEFAULT_BUNDLE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "trained_model", "model_bundle.joblib"
)

RECOMMENDATIONS = {
    "low": (
        "Your answers show a low level of postpartum depression symptoms right now. "
        "Keep taking care of yourself, and mention how you are feeling at your next checkup."
    ),
    "medium": (
        "Your answers show some signs of postpartum depression. This does not mean something "
        "is wrong with you. Please mention these feelings to your doctor, nurse, or midwife at "
        "your next visit, or sooner if things get harder."
    ),
    "high": (
        "Your answers show a high level of postpartum depression symptoms. We strongly recommend "
        "you see a doctor or health worker soon to talk about how you are feeling. You do not have "
        "to go through this alone."
    ),
}

CRISIS_MESSAGE = (
    "You mentioned thoughts of harming yourself. Your safety matters right now. "
    "Please reach out to a doctor, health worker, or emergency service near you immediately, "
    "or go to the nearest health facility. If you are in danger right now, call the National Mental Health Helpline at +221 33 889 38 00 "
    "You are not alone, and help is available."
)

SELF_HARM_COL = "self_harm_thoughts"


class ModelBundle:
    """Loads the joblib artefact written by the training notebook, once, on first use."""

    def __init__(self, path: str = None):
        self.path = path or os.environ.get("MODEL_BUNDLE_PATH", DEFAULT_BUNDLE_PATH)
        self._data = None

    @property
    def data(self) -> dict:
        if self._data is None:
            if not os.path.exists(self.path):
                raise RuntimeError(
                    f"Model bundle not found at {self.path}. "
                    "Run the training notebook first (notebook/ppd_model_training.ipynb)."
                )
            self._data = joblib.load(self.path)
        return self._data

    def metadata(self) -> Tuple[str, str]:
        return self.data.get("model_name", "unknown"), self.data.get("trained_on", "unknown")


class FeatureEncoder:
    """Maps validated answers onto the ordinal features, using the exact mappings saved at
    training time so inference can never drift from training."""

    def __init__(self, bundle: ModelBundle):
        self._bundle = bundle

    def encode(self, responses: Dict) -> pd.DataFrame:
        d = self._bundle.data
        row = {}
        for col in d["feature_cols"]:
            if col == "age_bracket":
                row[col] = d["age_map"][responses["age_bracket"]]
            else:
                row[col] = d["ordinal_map"][responses[col]]
        return pd.DataFrame([row], columns=d["feature_cols"])


class RiskClassifier(ABC):
    @abstractmethod
    def predict(self, responses: Dict) -> Tuple[str, float]:
        """Returns (risk_level, confidence) for one set of form answers."""


class SklearnRiskClassifier(RiskClassifier):
    def __init__(self, bundle: ModelBundle):
        self._bundle = bundle
        self._encoder = FeatureEncoder(bundle)

    def predict(self, responses: Dict) -> Tuple[str, float]:
        d = self._bundle.data
        model, label_encoder = d["model"], d["label_encoder"]
        X = self._encoder.encode(responses)
        level = label_encoder.inverse_transform([model.predict(X)[0]])[0]
        confidence = float(max(model.predict_proba(X)[0])) if hasattr(model, "predict_proba") else 1.0
        return level, confidence


class CrisisPolicy(ABC):
    @abstractmethod
    def is_crisis(self, responses: Dict) -> bool:
        """True when the answers require an immediate safety alert."""


class SelfHarmPolicy(CrisisPolicy):
    """Deterministic and independent of the ML model. Anything other than an explicit "No"
    (including "Sometimes", which is also what a declined answer is mapped to) raises the alert,
    so a missing or declined answer is never treated as safe."""

    def is_crisis(self, responses: Dict) -> bool:
        return responses.get(SELF_HARM_COL) != "No"


@dataclass(frozen=True)
class ScreeningResult:
    ml_risk_level: str       # the model's own output (kept for evaluation / retraining)
    risk_level: str          # the level shown to the user (raised to "high" on a crisis)
    probability_score: float
    crisis_flagged: bool
    recommendation_text: str
    crisis_message: str = None


class ScreeningEngine:
    def __init__(self, classifier: RiskClassifier, crisis_policy: CrisisPolicy, bundle: ModelBundle = None):
        self._classifier = classifier
        self._crisis_policy = crisis_policy
        self._bundle = bundle

    def assess(self, responses: Dict) -> ScreeningResult:
        ml_level, probability = self._classifier.predict(responses)
        crisis = self._crisis_policy.is_crisis(responses)
        shown = "high" if crisis else ml_level
        return ScreeningResult(
            ml_risk_level=ml_level,
            risk_level=shown,
            probability_score=probability,
            crisis_flagged=crisis,
            recommendation_text=RECOMMENDATIONS[shown],
            crisis_message=CRISIS_MESSAGE if crisis else None,
        )

    def model_metadata(self) -> Tuple[str, str]:
        return self._bundle.metadata()


def build_default_engine() -> ScreeningEngine:
    bundle = ModelBundle()
    return ScreeningEngine(SklearnRiskClassifier(bundle), SelfHarmPolicy(), bundle)

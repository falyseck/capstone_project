import os
from typing import Dict, Tuple

import joblib
import pandas as pd

MODEL_BUNDLE_PATH = os.environ.get(
    "MODEL_BUNDLE_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trained_model", "model_bundle.joblib"),
)

_bundle = None

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
    "or go to the nearest health facility. If you are in danger right now, call your local "
    "emergency number. You are not alone, and help is available."
)

SYMPTOM_COLS = [
    "feeling_sad",
    "irritable",
    "trouble_sleeping",
    "trouble_concentrating",
    "appetite_changes",
    "feeling_anxious",
    "feeling_guilty",
    "bonding_difficulty",
]
SELF_HARM_COL = "self_harm_thoughts"


def _load_bundle():
    global _bundle
    if _bundle is None:
        if not os.path.exists(MODEL_BUNDLE_PATH):
            raise RuntimeError(
                f"Model bundle not found at {MODEL_BUNDLE_PATH}. "
                "Run the training notebook first (notebook/ppd_model_training.ipynb)."
            )
        _bundle = joblib.load(MODEL_BUNDLE_PATH)
    return _bundle


def encode_form(responses: Dict) -> pd.DataFrame:
    """Turns validated form responses into the ordinal feature row the model expects,
    using the exact mappings saved during training so inference always matches training.
    Loops over `feature_cols` from the saved bundle (rather than hardcoding column names
    here) so this never drifts out of sync with whatever the notebook was trained on."""
    bundle = _load_bundle()
    ordinal_map = bundle["ordinal_map"]
    age_map = bundle["age_map"]
    feature_cols = bundle["feature_cols"]

    row = {}
    for col in feature_cols:
        if col == "age_bracket":
            row[col] = age_map[responses["age_bracket"]]
        else:
            row[col] = ordinal_map[responses[col]]

    return pd.DataFrame([row], columns=feature_cols)


def predict_risk(responses: Dict) -> Tuple[str, float]:
    bundle = _load_bundle()
    model = bundle["model"]
    label_encoder = bundle["label_encoder"]

    X = encode_form(responses)
    pred_encoded = model.predict(X)[0]
    risk_level = label_encoder.inverse_transform([pred_encoded])[0]

    proba = None
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X)[0]
        proba = float(max(probs))
    else:
        proba = 1.0

    return risk_level, proba


def recommendation_for(risk_level: str) -> str:
    return RECOMMENDATIONS.get(risk_level, RECOMMENDATIONS["medium"])


def check_self_harm(responses: Dict) -> bool:
    # Deliberately independent of the ML model: a fixed, deterministic rule.
    return responses.get(SELF_HARM_COL) != "No"


def model_metadata():
    bundle = _load_bundle()
    return bundle.get("model_name", "unknown"), bundle.get("trained_on", "unknown")

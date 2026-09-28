"""
ML inference module (matches the "ML inference module" box inside the Backend layer in
the section 3.5.1 architecture diagram).

Two things happen here, and they are deliberately kept separate, per section 3.5.3 of the
proposal:

1. `predict_risk()` — the trained ML model classifies overall risk (low/medium/high) from
   the 8 symptom items + age. It NEVER sees the self-harm item.
2. `check_self_harm()` — a simple, fixed rule, run independently of the model, exactly as
   specified: "The self-harm question is not handled by the ML model. It is checked
   separately with a simple rule, since a fixed check on this one item is more reliable
   and immediate than waiting on a model's overall prediction."
"""
import os
import numpy as np
import pandas as pd
import joblib

MODEL_BUNDLE_PATH = os.environ.get(
    "MODEL_BUNDLE_PATH",
    os.path.join(os.path.dirname(__file__), "..", "trained_model", "model_bundle.joblib"),
)

_bundle = None


def _load_bundle():
    global _bundle
    if _bundle is None:
        if not os.path.exists(MODEL_BUNDLE_PATH):
            raise RuntimeError(
                f"No trained model found at {MODEL_BUNDLE_PATH}. "
                "Run the training notebook first (notebook/ppd_model_training.ipynb)."
            )
        _bundle = joblib.load(MODEL_BUNDLE_PATH)
    return _bundle


RECOMMENDATIONS = {
    "low": (
        "Your responses suggest a low likelihood of postpartum depression right now. "
        "Keep an eye on how you're feeling, and don't hesitate to check in with a health "
        "worker if that changes."
    ),
    "medium": (
        "Your responses suggest some signs worth paying attention to. Consider mentioning "
        "this to a doctor or health worker at your next visit."
    ),
    "high": (
        "Your responses suggest a higher likelihood of postpartum depression. We strongly "
        "recommend seeing a doctor or health worker as soon as you can."
    ),
}

CRISIS_MESSAGE = (
    "You indicated thoughts of self-harm. This is serious, and support is available right "
    "now. Please reach out to a crisis line or emergency service in your area, or go to "
    "the nearest health facility immediately. You do not have to go through this alone."
)


def encode_form(responses: dict) -> pd.DataFrame:
    """Turns validated form responses into the ordinal feature row the model expects,
    using the exact mappings saved during training so inference always matches training.
    Returned as a one-row DataFrame with the training-time column names/order, so the
    model sees the same shape it was fitted on."""
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


def predict_risk(responses: dict) -> tuple[str, float]:
    """Returns (risk_level, probability_score) using the trained ML model only.
    The self-harm item is never passed in here."""
    bundle = _load_bundle()
    model = bundle["model"]
    le = bundle["label_encoder"]

    X = encode_form(responses)
    pred_encoded = model.predict(X)[0]
    proba = model.predict_proba(X)[0]

    risk_level = le.inverse_transform([pred_encoded])[0]
    probability_score = float(proba[pred_encoded])
    return risk_level, probability_score


def recommendation_for(risk_level: str) -> str:
    return RECOMMENDATIONS[risk_level]


def check_self_harm(responses: dict) -> bool:
    """Rule-based check, independent of the ML model. Flags True unless the mother
    answered 'No'."""
    return responses.get("self_harm_thoughts") != "No"


def model_metadata() -> dict:
    bundle = _load_bundle()
    return {
        "model_name": bundle.get("model_name"),
        "trained_on": bundle.get("trained_on"),
    }

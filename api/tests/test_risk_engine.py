"""Unit tests for the framework-free engine (no HTTP, no database)."""
import pytest

from risk_engine import (CrisisPolicy, FeatureEncoder, ModelBundle, RiskClassifier,
                         ScreeningEngine, SelfHarmPolicy, SklearnRiskClassifier, build_default_engine)


class FakeClassifier(RiskClassifier):
    def __init__(self, level):
        self.level = level

    def predict(self, responses):
        return self.level, 0.9


@pytest.mark.parametrize("answer,expected", [("No", False), ("Sometimes", True), ("Yes", True), (None, True)])
def test_self_harm_policy(answer, expected):
    assert SelfHarmPolicy().is_crisis({"self_harm_thoughts": answer}) is expected


def test_crisis_raises_shown_level_but_keeps_model_output(answers):
    answers["self_harm_thoughts"] = "Yes"
    result = ScreeningEngine(FakeClassifier("low"), SelfHarmPolicy()).assess(answers)
    assert result.risk_level == "high"
    assert result.ml_risk_level == "low"
    assert result.crisis_flagged and result.crisis_message


def test_no_crisis_shows_model_output(answers):
    result = ScreeningEngine(FakeClassifier("medium"), SelfHarmPolicy()).assess(answers)
    assert result.risk_level == result.ml_risk_level == "medium"
    assert not result.crisis_flagged and result.crisis_message is None


def test_engine_accepts_any_crisis_policy(answers):
    class Never(CrisisPolicy):
        def is_crisis(self, responses):
            return False
    answers["self_harm_thoughts"] = "Yes"
    assert ScreeningEngine(FakeClassifier("low"), Never()).assess(answers).risk_level == "low"


def test_encoder_uses_saved_mappings(answers):
    answers.update(feeling_sad="Yes", irritable="Sometimes", age_bracket="45-50")
    row = FeatureEncoder(ModelBundle()).encode(answers).iloc[0]
    assert row["feeling_sad"] == 2 and row["irritable"] == 1 and row["age_bracket"] == 4


def test_real_model_extremes(answers):
    engine = build_default_engine()
    assert engine.assess(answers).ml_risk_level == "low"
    worst = {k: ("Yes" if k not in ("age_bracket", "self_harm_thoughts") else v) for k, v in answers.items()}
    assert engine.assess(worst).ml_risk_level == "high"


def test_missing_bundle_gives_clear_error(tmp_path):
    with pytest.raises(RuntimeError, match="Run the training notebook"):
        SklearnRiskClassifier(ModelBundle(str(tmp_path / "nope.joblib"))).predict({})

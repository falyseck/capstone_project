import pytest

from api.ml_service import adjust_risk_for_self_harm, check_self_harm


@pytest.mark.parametrize(
    ("model_risk", "self_harm_response", "expected"),
    [
        ("low", "No", "low"),
        ("medium", "No", "medium"),
        ("high", "No", "high"),
        ("low", "Sometimes", "medium"),
        ("medium", "Sometimes", "medium"),
        ("high", "Sometimes", "high"),
        ("low", "Yes", "high"),
        ("medium", "Yes", "high"),
        ("high", "Yes", "high"),
    ],
)
def test_adjust_risk_for_self_harm(model_risk, self_harm_response, expected):
    responses = {"self_harm_thoughts": self_harm_response}

    assert adjust_risk_for_self_harm(model_risk, responses) == expected


@pytest.mark.parametrize(
    ("self_harm_response", "expected"),
    [("No", False), ("Sometimes", True), ("Yes", True)],
)
def test_self_harm_crisis_check_remains_separate(self_harm_response, expected):
    responses = {"self_harm_thoughts": self_harm_response}

    assert check_self_harm(responses) is expected

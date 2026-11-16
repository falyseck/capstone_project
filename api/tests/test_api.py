"""Integration tests: HTTP layer + database + role-based access control + validation."""
import pytest

from conftest import register_and_login


@pytest.fixture(scope="module")
def world(client):
    fac = client.get("/facilities").json()
    mother_h, mother_id = register_and_login(client, "Mother A", "ma@x.org", "mother", fac[0]["id"])
    worker_h, _ = register_and_login(client, "Worker A", "wa@x.org", "healthcare_worker", fac[0]["id"])
    other_h, _ = register_and_login(client, "Worker B", "wb@x.org", "healthcare_worker", fac[1]["id"])
    return dict(mother=mother_h, worker=worker_h, other=other_h, mother_id=mother_id)


def test_duplicate_email_rejected(client, world):
    fac = client.get("/facilities").json()[0]["id"]
    r = client.post("/auth/register", json={"name": "Dup", "email": "ma@x.org", "password": "secret123",
                                            "role": "healthcare_worker", "facility_id": fac, "license_id": "L"})
    assert r.status_code == 400


def test_wrong_password_rejected(client, world):
    r = client.post("/auth/login", data={"username": "ma@x.org", "password": "wrong"})
    assert r.status_code == 401


def test_submit_requires_login(client, answers):
    assert client.post("/screening/submit", json=answers).status_code == 401


def test_worker_cannot_submit_screening(client, world, answers):
    assert client.post("/screening/submit", json=answers, headers=world["worker"]).status_code == 403


def test_mother_cannot_list_patients(client, world):
    assert client.get("/healthcare/patients", headers=world["mother"]).status_code == 403


def test_invalid_answer_rejected(client, world, answers):
    answers["feeling_sad"] = "Always"
    assert client.post("/screening/submit", json=answers, headers=world["mother"]).status_code == 422


def test_missing_field_rejected(client, world, answers):
    del answers["feeling_sad"]
    assert client.post("/screening/submit", json=answers, headers=world["mother"]).status_code == 422


def test_crisis_answer_gives_high_and_alert(client, world, answers):
    answers["self_harm_thoughts"] = "Yes"
    r = client.post("/screening/submit", json=answers, headers=world["mother"])
    body = r.json()
    assert r.status_code == 200 and body["crisis_flagged"] and body["risk_level"] == "high"
    assert body["crisis_message"]


def test_facility_scoping(client, world):
    mid = world["mother_id"]
    assert client.get(f"/healthcare/patients/{mid}/history", headers=world["worker"]).status_code == 200
    assert client.get(f"/healthcare/patients/{mid}/history", headers=world["other"]).status_code == 403
    assert client.get("/healthcare/patients", headers=world["other"]).json() == []


def test_clinical_assessment_and_report(client, world, answers):
    form_id = client.post("/screening/submit", json=answers, headers=world["mother"]).json()["form_id"]
    r = client.post(f"/healthcare/screenings/{form_id}/assessment", headers=world["worker"],
                    json={"risk_level": "medium", "notes": "seen in clinic"})
    assert r.status_code == 201
    assert client.post(f"/healthcare/screenings/{form_id}/assessment", headers=world["other"],
                       json={"risk_level": "low"}).status_code == 403
    report = client.post(f"/healthcare/patients/{world['mother_id']}/report", headers=world["worker"]).json()
    assert "clinical assessment=medium" in report["content"]

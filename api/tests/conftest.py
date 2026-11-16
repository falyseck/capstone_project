import os
import sys
import tempfile

# Isolated database + importable api modules, set before the app is imported.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


ANSWERS_NO = {
    "age_bracket": "30-35", "feeling_sad": "No", "irritable": "No", "trouble_sleeping": "No",
    "trouble_concentrating": "No", "appetite_changes": "No", "feeling_anxious": "No",
    "feeling_guilty": "No", "bonding_difficulty": "No", "self_harm_thoughts": "No",
}


@pytest.fixture
def answers():
    return dict(ANSWERS_NO)


def register_and_login(client, name, email, role, facility_id, **extra):
    body = {"name": name, "email": email, "password": "secret123", "role": role, "facility_id": facility_id}
    if role == "mother":
        body.update(date_of_birth="1995-04-10", delivery_date="2026-06-01")
    else:
        body.update(license_id="LIC-1")
    body.update(extra)
    r = client.post("/auth/register", json=body)
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", data={"username": email, "password": "secret123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user_id"]

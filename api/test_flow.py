"""
Quick end-to-end smoke test for the API, using FastAPI's TestClient (no server needed).
Run with: python3 test_flow.py
"""
import os
os.environ["DATABASE_URL"] = "sqlite:///./test_ppd.db"

if os.path.exists("./test_ppd.db"):
    os.remove("./test_ppd.db")

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
client.__enter__()  # trigger startup event (creates tables, seeds facilities)


def login(email, password):
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


print("1. Listing seeded facilities...")
r = client.get("/facilities")
assert r.status_code == 200, r.text
facilities = r.json()
assert len(facilities) >= 2
facility_a, facility_b = facilities[0]["id"], facilities[1]["id"]
print(f"   OK - {len(facilities)} facilities found.")

print("2. Registering a mother at facility A...")
r = client.post("/auth/register", json={
    "name": "Awa Diop", "email": "awa@example.com", "password": "supersecret1",
    "role": "mother", "facility_id": facility_a,
})
assert r.status_code == 201, r.text
mother_id = r.json()["id"]
print(f"   OK - mother id {mother_id}")

print("3. Registering a healthcare worker at facility A...")
r = client.post("/auth/register", json={
    "name": "Dr. Fall", "email": "fall@example.com", "password": "supersecret2",
    "role": "healthcare_worker", "facility_id": facility_a, "license_id": "LIC-001",
})
assert r.status_code == 201, r.text
worker_id = r.json()["id"]

print("4. Registering a second healthcare worker at facility B (should NOT see facility A's mothers)...")
r = client.post("/auth/register", json={
    "name": "Dr. Ba", "email": "ba@example.com", "password": "supersecret3",
    "role": "healthcare_worker", "facility_id": facility_b, "license_id": "LIC-002",
})
assert r.status_code == 201, r.text

print("5. Mother logs in and submits a LOW risk screening form...")
mother_token = login("awa@example.com", "supersecret1")
low_risk_form = {
    "age_bracket": "25-30",
    "feeling_sad": "No", "irritable": "No", "trouble_sleeping": "No",
    "trouble_concentrating": "No", "appetite_changes": "No", "feeling_anxious": "No",
    "feeling_guilty": "No", "bonding_difficulty": "No", "self_harm_thoughts": "No",
}
r = client.post("/screening/submit", json=low_risk_form, headers=auth_headers(mother_token))
assert r.status_code == 200, r.text
result = r.json()
print(f"   OK - risk_level={result['risk_level']}, crisis_flagged={result['crisis_flagged']}")
assert result["crisis_flagged"] is False

print("6. Same mother submits a form WITH self-harm thoughts flagged (regardless of other answers)...")
crisis_form = dict(low_risk_form)
crisis_form["self_harm_thoughts"] = "Yes"
r = client.post("/screening/submit", json=crisis_form, headers=auth_headers(mother_token))
assert r.status_code == 200, r.text
result = r.json()
print(f"   OK - risk_level={result['risk_level']}, crisis_flagged={result['crisis_flagged']}")
assert result["crisis_flagged"] is True
assert result["crisis_message"] is not None
print(f"   Crisis message shown: \"{result['crisis_message'][:60]}...\"")

print("7. Submitting an incomplete form (missing fields) should be rejected...")
r = client.post("/screening/submit", json={"age_bracket": "25-30"}, headers=auth_headers(mother_token))
assert r.status_code == 422, r.text
print("   OK - rejected with 422 as expected.")

print("8. Mother checks her own screening history...")
r = client.get("/screening/history", headers=auth_headers(mother_token))
assert r.status_code == 200, r.text
assert len(r.json()) == 2
print(f"   OK - {len(r.json())} screenings on record.")

print("9. Healthcare worker at facility A views patient list (should see the mother)...")
worker_token = login("fall@example.com", "supersecret2")
r = client.get("/healthcare/patients", headers=auth_headers(worker_token))
assert r.status_code == 200, r.text
patients = r.json()
assert len(patients) == 1
assert patients[0]["mother_id"] == mother_id
assert patients[0]["total_screenings"] == 2
print(f"   OK - sees {len(patients)} patient(s), total_screenings={patients[0]['total_screenings']}")

print("10. Healthcare worker at facility B tries to view facility A's mother (should be forbidden)...")
worker_b_token = login("ba@example.com", "supersecret3")
r = client.get(f"/healthcare/patients/{mother_id}/history", headers=auth_headers(worker_b_token))
assert r.status_code == 403, r.text
print("   OK - correctly forbidden (403), facility scoping works.")

print("11. Healthcare worker at facility A generates a report for the mother...")
r = client.post(f"/healthcare/patients/{mother_id}/report", headers=auth_headers(worker_token))
assert r.status_code == 200, r.text
report = r.json()
assert report["mother_id"] == mother_id
assert report["generated_by"] == worker_id
print("   OK - report generated:")
print("   ---")
for line in report["content"].splitlines():
    print("  ", line)
print("   ---")

print()
print("ALL CHECKS PASSED.")

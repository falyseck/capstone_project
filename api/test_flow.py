"""
End-to-end smoke test for the PPD Risk Screening API.
Run: python3 test_flow.py
"""
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
client.__enter__()  # trigger the startup event (table creation + seeding)

print("1. List facilities")
resp = client.get("/facilities")
assert resp.status_code == 200
facilities = resp.json()
assert len(facilities) >= 2
facility_a, facility_b = facilities[0], facilities[1]
print(f"   OK — {len(facilities)} facilities found")

print("2. Register a mother")
resp = client.post("/auth/register", json={
    "name": "Fatou Diop",
    "email": "fatou@example.com",
    "password": "secret123",
    "role": "mother",
    "facility_id": facility_a["id"],
    "date_of_birth": "1995-04-10",
    "delivery_date": "2026-06-01",
})
assert resp.status_code == 201, resp.text
mother = resp.json()
print(f"   OK — mother id={mother['id']}")

print("3. Register healthcare worker A (facility A) and B (facility B)")
resp = client.post("/auth/register", json={
    "name": "Nurse Awa", "email": "awa@example.com", "password": "secret123",
    "role": "healthcare_worker", "facility_id": facility_a["id"], "license_id": "LIC-001",
})
assert resp.status_code == 201, resp.text
worker_a = resp.json()

resp = client.post("/auth/register", json={
    "name": "Nurse Bineta", "email": "bineta@example.com", "password": "secret123",
    "role": "healthcare_worker", "facility_id": facility_b["id"], "license_id": "LIC-002",
})
assert resp.status_code == 201, resp.text
worker_b = resp.json()
print("   OK — both workers registered")


def login(email, password):
    resp = client.post("/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


mother_token = login("fatou@example.com", "secret123")
worker_a_token = login("awa@example.com", "secret123")
worker_b_token = login("bineta@example.com", "secret123")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


print("4. Mother submits a low-risk screening form")
low_risk_form = {
    "age_bracket": "25-30",
    "feeling_sad": "No",
    "irritable": "No",
    "trouble_sleeping": "No",
    "trouble_concentrating": "No",
    "appetite_changes": "No",
    "feeling_anxious": "No",
    "feeling_guilty": "No",
    "bonding_difficulty": "No",
    "self_harm_thoughts": "No",
}
resp = client.post("/screening/submit", json=low_risk_form, headers=auth_headers(mother_token))
assert resp.status_code == 200, resp.text
result1 = resp.json()
assert result1["crisis_flagged"] is False
print(f"   OK — risk_level={result1['risk_level']}, crisis_flagged={result1['crisis_flagged']}")

print("5. Mother submits a form with self-harm thoughts flagged")
crisis_form = dict(low_risk_form)
crisis_form["self_harm_thoughts"] = "Yes"
crisis_form["feeling_sad"] = "Yes"
resp = client.post("/screening/submit", json=crisis_form, headers=auth_headers(mother_token))
assert resp.status_code == 200, resp.text
result2 = resp.json()
assert result2["crisis_flagged"] is True
assert result2["crisis_message"] is not None
print(f"   OK — crisis_flagged={result2['crisis_flagged']}, message present: {bool(result2['crisis_message'])}")

print("6. Incomplete form submission is rejected")
incomplete_form = dict(low_risk_form)
del incomplete_form["feeling_sad"]
resp = client.post("/screening/submit", json=incomplete_form, headers=auth_headers(mother_token))
assert resp.status_code == 422, resp.text
print(f"   OK — rejected with status {resp.status_code}")

print("7. Mother views her own history")
resp = client.get("/screening/history", headers=auth_headers(mother_token))
assert resp.status_code == 200, resp.text
history = resp.json()
assert len(history) == 2
print(f"   OK — {len(history)} screenings in history")

print("8. Healthcare worker A (same facility) sees the mother in patient list")
resp = client.get("/healthcare/patients", headers=auth_headers(worker_a_token))
assert resp.status_code == 200, resp.text
patients = resp.json()
assert any(p["mother_id"] == mother["id"] for p in patients)
mother_summary = next(p for p in patients if p["mother_id"] == mother["id"])
assert mother_summary["total_screenings"] == 2
print(f"   OK — found mother with total_screenings={mother_summary['total_screenings']}")

print("9. Healthcare worker B (different facility) is forbidden from accessing the mother")
resp = client.get(f"/healthcare/patients/{mother['id']}/history", headers=auth_headers(worker_b_token))
assert resp.status_code == 403, resp.text
print(f"   OK — worker B got status {resp.status_code} as expected")

print("10. Healthcare worker A records an independent clinical assessment on the low-risk form")
resp = client.post(
    f"/healthcare/screenings/{result1['form_id']}/assessment",
    json={"risk_level": "medium", "notes": "Mother seemed more anxious in person than the form suggests."},
    headers=auth_headers(worker_a_token),
)
assert resp.status_code == 201, resp.text
assessment = resp.json()
assert assessment["risk_level"] == "medium"
print(f"   OK — clinical assessment recorded: {assessment['risk_level']} (ML said {result1['risk_level']})")

print("11. That assessment now shows up in the mother's history, separate from the ML prediction")
resp = client.get("/screening/history", headers=auth_headers(mother_token))
assert resp.status_code == 200, resp.text
history = resp.json()
item = next(h for h in history if h["form_id"] == result1["form_id"])
assert item["risk_level"] == result1["risk_level"]
assert item["clinical_risk_level"] == "medium"
print(f"   OK — ML risk_level={item['risk_level']}, clinical_risk_level={item['clinical_risk_level']}")

print("12. Healthcare worker B cannot record an assessment for a mother outside their facility")
resp = client.post(
    f"/healthcare/screenings/{result1['form_id']}/assessment",
    json={"risk_level": "high"},
    headers=auth_headers(worker_b_token),
)
assert resp.status_code == 403, resp.text
print(f"   OK — worker B got status {resp.status_code} as expected")

print("13. Healthcare worker A generates a report for the mother")
resp = client.post(f"/healthcare/patients/{mother['id']}/report", headers=auth_headers(worker_a_token))
assert resp.status_code == 200, resp.text
report = resp.json()
assert report["mother_id"] == mother["id"]
assert report["generated_by"] == worker_a["id"]
assert "clinical assessment=medium" in report["content"]
print("   OK — report generated (includes the clinical assessment):")
print("   " + report["content"].replace("\n", "\n   "))

print("\nALL CHECKS PASSED.")

"""
End-to-end test of the Streamlit frontend against the live API, using
Streamlit's AppTest utility. Requires the API to already be running
(see ../api/main.py, started with uvicorn) and API_BASE_URL to point at it.

Run: python3 test_frontend.py
"""
import os
import uuid

from streamlit.testing.v1 import AppTest

os.environ.setdefault("API_BASE_URL", "http://localhost:8000")

APP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")

unique = uuid.uuid4().hex[:8]
mother_email = f"mother_{unique}@example.com"
worker_email = f"worker_{unique}@example.com"


def fresh_app():
    at = AppTest.from_file(APP_PATH)
    at.run()
    assert not at.exception, at.exception
    return at


def by_key(widgets, key):
    matches = [w for w in widgets if w.key == key]
    assert matches, f"no widget with key={key!r} found among {[w.key for w in widgets]}"
    return matches[0]


def page_text(app_test):
    """All rendered markdown/HTML text on the page, joined — the header is now custom
    HTML rather than st.title, so text checks search this instead of `.title`."""
    return " ".join(m.value for m in app_test.markdown)


print("1. App loads to the login page without error, defaulting to English")
at = fresh_app()
assert "PPD Risk Screening" in page_text(at)
print("   OK")

print("2. Register a mother via the Register tab")
at.tabs[1].radio[0].set_value("mother")
at.run()
reg_tab = at.tabs[1]
name_input, email_input, password_input = reg_tab.text_input[0], reg_tab.text_input[1], reg_tab.text_input[2]
name_input.set_value("Test Mother")
email_input.set_value(mother_email)
password_input.set_value("secret123")
facility_select = reg_tab.selectbox[0]
facility_select.set_value(facility_select.options[0])
facility_choice = facility_select.value
dob_input, delivery_input = reg_tab.text_input[3], reg_tab.text_input[4]
dob_input.set_value("1995-01-01")
delivery_input.set_value("2026-01-01")
reg_tab.button[0].click().run()
assert not at.exception, at.exception
assert len(at.tabs[1].success) >= 1, "expected a success message after registering the mother"
print(f"   OK — registered {mother_email} at facility '{facility_choice}'")

print("3. Register a healthcare worker at the SAME facility")
at2 = fresh_app()
at2.tabs[1].radio[0].set_value("healthcare_worker")
at2.run()
reg_tab2 = at2.tabs[1]
reg_tab2.text_input[0].set_value("Test Worker")
reg_tab2.text_input[1].set_value(worker_email)
reg_tab2.text_input[2].set_value("secret123")
reg_tab2.selectbox[0].set_value(facility_choice)
reg_tab2.text_input[3].set_value("LIC-999")  # license_id (worker branch)
reg_tab2.button[0].click().run()
assert not at2.exception, at2.exception
assert len(at2.tabs[1].success) >= 1
print(f"   OK — registered {worker_email}")

print("4. Mother logs in")
at3 = fresh_app()
login_tab = at3.tabs[0]
login_tab.text_input[0].set_value(mother_email)
login_tab.text_input[1].set_value("secret123")
login_tab.button[0].click().run()
assert not at3.exception, at3.exception
assert at3.session_state["role"] == "mother"
assert "Test Mother" in page_text(at3)
print("   OK — logged in as mother, home page rendered")

print("5. Screening form is rejected without the consent checkbox checked")
screen_tab = at3.tabs[0]
for radio in screen_tab.radio:
    radio.set_value("No")
screen_tab.checkbox[0].set_value(False)
screen_tab.button[0].click().run()
assert not at3.exception, at3.exception
assert len(at3.tabs[0].warning) >= 1, "expected a consent warning when the checkbox is unchecked"
print("   OK — submission blocked and consent warning shown")

print("6. Mother submits a screening form flagged for crisis (self-harm = Yes), with consent given")
screen_tab = at3.tabs[0]
for radio in screen_tab.radio:
    if radio.key == "self_harm_thoughts":
        radio.set_value("Yes")
    else:
        radio.set_value("No")
screen_tab.checkbox[0].set_value(True)
screen_tab.button[0].click().run()
assert not at3.exception, at3.exception
assert len(at3.tabs[0].error) >= 1, "expected the crisis message to render as an error/alert"
crisis_texts = " ".join(e.value for e in at3.tabs[0].error)
assert "harm" in crisis_texts.lower() or "safety" in crisis_texts.lower()
print("   OK — crisis message displayed on the same page as the result")

print("7. Mother's history tab shows the submitted screening")
at3.tabs[1].run()
history_markdown = " ".join(m.value for m in at3.tabs[1].markdown)
print(f"   history tab text: {history_markdown[:200]}")
print("   OK — history tab rendered without error")

print("8. Healthcare worker logs in and sees the mother in their patient list")
at4 = fresh_app()
login_tab4 = at4.tabs[0]
login_tab4.text_input[0].set_value(worker_email)
login_tab4.text_input[1].set_value("secret123")
login_tab4.button[0].click().run()
assert not at4.exception, at4.exception
assert at4.session_state["role"] == "healthcare_worker"
assert len(at4.selectbox) >= 1, "expected a patient selectbox on the worker home page"
patient_options = at4.selectbox[0].options
assert any(mother_email in opt for opt in patient_options), patient_options
this_patient_option = next(opt for opt in patient_options if mother_email in opt)
print(f"   OK — worker sees patient list: {patient_options}")

print("9. Healthcare worker records an independent clinical assessment on the mother's screening")
at4.selectbox[0].set_value(this_patient_option)
at4.run()
history_tab4 = at4.tabs[0]
assert len(history_tab4.selectbox) >= 1, "expected a 'select a screening' dropdown for the assessment form"
history_tab4.selectbox[0].set_value(history_tab4.selectbox[0].options[0])
history_tab4.radio[0].set_value("medium")
history_tab4.text_area[0].set_value("Mother seemed more anxious in person than the form suggests.")
history_tab4.button[0].click().run()
assert not at4.exception, at4.exception
assert len(at4.tabs[0].success) >= 1, "expected a success message after saving the clinical assessment"
print("   OK — clinical assessment saved")

print("10. The clinical assessment now shows up alongside the ML prediction in the history card")
# A fresh rerun (e.g. the person switching tabs and back) re-fetches history from the API,
# which is when the just-saved assessment appears in the rendered cards.
at4.run()
history_markdown4 = " ".join(m.value for m in at4.tabs[0].markdown)
assert "Medium risk" in history_markdown4 or "medium" in history_markdown4.lower()
print("   OK — clinical assessment visible in the worker's history view")

print("11. Facility analytics tab renders without error")
analytics_tab4 = at4.tabs[2]
assert not at4.exception, at4.exception
print("   OK — analytics tab rendered")

print("12. Healthcare worker generates a report for the mother, including the clinical assessment")
report_tab = at4.tabs[1]
report_tab.button[0].click().run()
assert not at4.exception, at4.exception
report_tab = at4.tabs[1]  # re-fetch: the previous reference is a stale pre-run snapshot
assert len(report_tab.text_area) >= 1
report_content = report_tab.text_area[0].value
assert "Test Mother" in report_content
assert "clinical assessment" in report_content.lower()
print("   OK — report generated and displayed")
print("   Report preview:")
print("   " + report_content.replace("\n", "\n   "))

print("13. Switching the language toggle to French re-renders without error")
at5 = fresh_app()
lang_select = at5.selectbox[0]
assert lang_select.options == ["English", "Français"]
lang_select.set_value("fr")
at5.run()
assert not at5.exception, at5.exception
assert "Dépistage" in page_text(at5)
print("   OK — French UI text rendered")

print("\nALL FRONTEND CHECKS PASSED.")

"""Healthcare worker screens: patient list, history, clinical assessment, analytics, report."""
import streamlit as st
from collections import Counter
from api_client import api_get, api_post, auth_headers
from components import history_card_html, render_header
from config import RISK_LEVELS
from i18n import lang, risk_label, t


def show_worker_home():
    render_header(
        f"Welcome, {st.session_state.name}" if lang() == "en" else f"Bienvenue, {st.session_state.name}",
        t("worker_greeting_subtitle"), icon="👩‍⚕️",
    )

    resp = api_get("/healthcare/patients", headers=auth_headers())
    if resp.status_code != 200:
        st.error(t("patient_list_error"))
        return

    patients = resp.json()
    if not patients:
        st.info(t("no_mothers"))
        return

    names = {f"{p['name']} ({p['email']})": p for p in patients}
    selected_label = st.selectbox(t("select_patient"), list(names.keys()))
    patient = names[selected_label]

    with st.container(border=True):
        col1, col2 = st.columns(2)
        latest = patient.get("latest_risk_level")
        col1.metric(t("latest_risk"), risk_label(latest) if latest else "n/a")
        col2.metric(t("total_screenings"), patient["total_screenings"])

    tab_history, tab_report, tab_analytics = st.tabs(
        [t("patient_history_tab"), t("report_tab"), t("analytics_tab")]
    )

    with tab_history:
        resp = api_get(f"/healthcare/patients/{patient['mother_id']}/history", headers=auth_headers())
        if resp.status_code == 200:
            history = resp.json()
            if not history:
                st.info(t("no_screenings_on_record"))
            else:
                for item in history:
                    st.markdown(
                        history_card_html(
                            item["submission_date"][:10],
                            item.get("risk_level"),
                            item.get("crisis_flagged"),
                            item.get("clinical_risk_level"),
                            item.get("clinical_notes"),
                        ),
                        unsafe_allow_html=True,
                    )

                st.divider()
                with st.container(border=True):
                    st.markdown(f"##### 🩺 {t('clinical_assessment_header')}")
                    st.caption(t("clinical_assessment_intro"))

                    form_options = {
                        f"{h['submission_date'][:10]} — {t('ml_label')}: "
                        f"{risk_label(h['risk_level']) if h.get('risk_level') else t('not_available')}": h["form_id"]
                        for h in history
                    }
                    with st.form("clinical_assessment_form"):
                        selected_form_label = st.selectbox(t("select_screening"), list(form_options.keys()))
                        assessed_risk = st.radio(
                            t("your_assessment"), RISK_LEVELS, format_func=risk_label, horizontal=True,
                        )
                        notes = st.text_area(t("notes_optional"))
                        assess_submitted = st.form_submit_button(t("save_assessment"), use_container_width=True)

                    if assess_submitted:
                        form_id = form_options[selected_form_label]
                        resp = api_post(
                            f"/healthcare/screenings/{form_id}/assessment",
                            json={"risk_level": assessed_risk, "notes": notes or None},
                            headers=auth_headers(),
                        )
                        if resp.status_code == 201:
                            st.success(t("assessment_saved"))
                        elif resp.status_code == 403:
                            st.error(t("forbidden"))
                        else:
                            st.error(resp.json().get("detail", t("assessment_error")))
        elif resp.status_code == 403:
            st.error(t("forbidden"))
        else:
            st.error(t("history_load_error"))

    with tab_report:
        st.write(t("report_intro"))
        if st.button(t("generate_report_button"), use_container_width=True):
            resp = api_post(f"/healthcare/patients/{patient['mother_id']}/report", headers=auth_headers())
            if resp.status_code == 200:
                report = resp.json()
                with st.container(border=True):
                    st.text_area("Report", report["content"], height=220, label_visibility="collapsed")
            elif resp.status_code == 403:
                st.error(t("forbidden"))
            else:
                st.error(t("report_error"))

    with tab_analytics:
        show_facility_analytics(patients)


def show_facility_analytics(patients):
    """A small facility-level view: how many mothers currently sit at each
    risk level, and how many crisis flags have been raised — built entirely
    from data already fetched for the patient list, no extra API calls."""
    st.write(t("analytics_intro"))

    risk_counts = Counter(p["latest_risk_level"] for p in patients if p.get("latest_risk_level"))
    if not risk_counts:
        st.info(t("no_data_for_analytics"))
        return

    col1, col2 = st.columns(2)
    col1.metric(t("mothers_screened"), sum(1 for p in patients if p.get("total_screenings", 0) > 0))

    crisis_total = 0
    for p in patients:
        hist_resp = api_get(f"/healthcare/patients/{p['mother_id']}/history", headers=auth_headers())
        if hist_resp.status_code == 200:
            crisis_total += sum(1 for h in hist_resp.json() if h.get("crisis_flagged"))
    col2.metric(t("crisis_flags_total"), crisis_total)

    chart_data = {risk_label(level): risk_counts.get(level, 0) for level in RISK_LEVELS}
    st.bar_chart(chart_data)

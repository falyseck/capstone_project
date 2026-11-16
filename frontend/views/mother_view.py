"""Mother screens: consent, screening form, result and history."""
import streamlit as st
from api_client import api_get, api_post, auth_headers
from components import history_card_html, render_header, risk_badge
from config import AGE_OPTIONS, LEVEL_OPTIONS, SELF_HARM_QUESTION, SYMPTOM_QUESTIONS
from i18n import lang, level_option_label, t


def show_mother_home():
    render_header(f"Hi, {st.session_state.name}" if lang() == "en" else f"Bonjour, {st.session_state.name}",
                  t("mother_greeting_subtitle"), icon="🌸")

    tab_screen, tab_history = st.tabs([t("new_screening_tab"), t("history_tab")])

    with tab_screen:
        with st.container(border=True):
            st.write(t("screening_intro"))
            with st.form("screening_form"):
                age_bracket = st.selectbox(t("age_label"), AGE_OPTIONS)
                st.markdown("&nbsp;", unsafe_allow_html=True)
                responses = {}
                for key, question_en, question_fr, emoji in SYMPTOM_QUESTIONS:
                    question = question_en if lang() == "en" else question_fr
                    st.markdown(f"**{emoji} {question}**")
                    responses[key] = st.radio(
                        question, LEVEL_OPTIONS, horizontal=True, key=key,
                        format_func=level_option_label, label_visibility="collapsed",
                    )

                st.divider()
                st.markdown(t("self_harm_intro"))
                sh_key, sh_question_en, sh_question_fr = SELF_HARM_QUESTION
                sh_question = sh_question_en if lang() == "en" else sh_question_fr
                responses[sh_key] = st.radio(
                    sh_question, LEVEL_OPTIONS, horizontal=True, key=sh_key,
                    format_func=level_option_label,
                )

                st.divider()
                consent_given = st.checkbox(t("consent_text"))

                submitted = st.form_submit_button(t("submit_screening"), use_container_width=True)

        if submitted:
            if not consent_given:
                st.warning(t("consent_required_warning"))
            else:
                payload = {"age_bracket": age_bracket, **responses}
                resp = api_post("/screening/submit", json=payload, headers=auth_headers())
                if resp.status_code == 200:
                    result = resp.json()

                    st.write("")
                    if result["crisis_flagged"]:
                        st.error(f"⚠️ {result['crisis_message']}")

                    with st.container(border=True):
                        st.markdown(f"##### {t('your_result')}")
                        risk_badge(result["risk_level"])
                        st.write(result["recommendation_text"])
                elif resp.status_code == 401:
                    st.error(t("session_expired"))
                else:
                    st.error(resp.json().get("detail", t("submit_error")))

    with tab_history:
        resp = api_get("/screening/history", headers=auth_headers())
        if resp.status_code == 200:
            history = resp.json()
            if not history:
                st.info(t("no_screenings_yet"))
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
        else:
            st.error(t("history_load_error"))

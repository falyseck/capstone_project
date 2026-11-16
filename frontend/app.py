"""
Streamlit frontend for the PPD Risk Screening System.

A mother can register, log in, give consent, fill out a short screening form,
and see her result on the same page — including any independent clinical
assessment a healthcare worker has since recorded for that screening. A
healthcare worker can register, log in, see the mothers registered at their
own facility, view a mother's screening history, record their own clinical
assessment on a screening, see facility-level risk analytics, and generate a
report. The interface is available in English and French. No app download is
needed — it works from a phone or computer browser.

Run with:
    streamlit run app.py

Configure the API location with the API_BASE_URL environment variable
(defaults to http://localhost:8000).
"""
import streamlit as st

from components import language_toggle
from i18n import t
from session import init_state, logout
from styles import inject_css
from views.auth_view import show_login
from views.mother_view import show_mother_home
from views.worker_view import show_worker_home


def main():
    init_state()
    inject_css()

    if st.session_state.token is None:
        show_login()
        return

    with st.sidebar:
        initials = "".join([p[0] for p in st.session_state.name.split()][:2]).upper()
        role_display = t("mother") if st.session_state.role == "mother" else t("healthcare_worker")
        st.markdown(
            f"""
            <div class="user-card">
                <div class="avatar">{initials}</div>
                <div><strong>{st.session_state.name}</strong></div>
                <div class="role-pill">{role_display}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        language_toggle("lang_select_sidebar")
        if st.button(t("logout"), use_container_width=True):
            logout()
            st.rerun()

    if st.session_state.role == "mother":
        show_mother_home()
    else:
        show_worker_home()


if __name__ == "__main__":
    main()

"""Login and registration screens."""
import streamlit as st
import requests
from api_client import api_post, get_facilities
from components import language_toggle, render_header
from config import API_BASE_URL
from i18n import lang, t


def show_login():
    top_left, top_right = st.columns([3, 1])
    with top_right:
        language_toggle("lang_select_login")

    render_header(t("app_title"), t("app_subtitle"))
    st.write("")

    tab_login, tab_register = st.tabs([t("login_tab"), t("register_tab")])

    with tab_login:
        with st.container(border=True):
            with st.form("login_form"):
                st.markdown(f"##### {t('welcome_back')}")
                email = st.text_input(t("email"), placeholder="you@example.com")
                password = st.text_input(t("password"), type="password", placeholder="••••••••")
                submitted = st.form_submit_button(t("login_button"), use_container_width=True)
        if submitted:
            try:
                resp = api_post("/auth/login", data={"username": email, "password": password})
            except requests.exceptions.ConnectionError:
                st.error(t("api_unreachable", url=API_BASE_URL))
                return
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.token = data["access_token"]
                st.session_state.role = data["role"]
                st.session_state.user_id = data["user_id"]
                st.session_state.name = data["name"]
                st.session_state.page = "home"
                st.rerun()
            else:
                st.error(resp.json().get("detail", t("login_failed")))

    with tab_register:
        try:
            facilities = get_facilities()
        except requests.exceptions.ConnectionError:
            st.error(t("api_unreachable", url=API_BASE_URL))
            return
        facility_names = {f["name"]: f["id"] for f in facilities}

        role_label = st.radio(
            t("register_as"),
            ["mother", "healthcare_worker"],
            format_func=lambda v: t("mother") if v == "mother" else t("healthcare_worker"),
            horizontal=True,
        )
        role = role_label

        with st.container(border=True):
            with st.form("register_form"):
                role_display = t("mother") if role == "mother" else t("healthcare_worker")
                st.markdown(f"##### {t('create_account_title', role=role_display.lower())}")
                name = st.text_input(t("full_name"))
                email = st.text_input(t("email"), key="reg_email")
                password = st.text_input(
                    t("password"), type="password", key="reg_password",
                    help="At least 8 characters." if lang() == "en" else "Au moins 8 caractères.",
                )
                facility_name = st.selectbox(t("facility"), list(facility_names.keys()))

                date_of_birth = None
                delivery_date = None
                license_id = None
                if role == "mother":
                    col_a, col_b = st.columns(2)
                    date_of_birth = col_a.text_input(t("dob"))
                    delivery_date = col_b.text_input(t("delivery_date"))
                else:
                    license_id = st.text_input(t("license_id"))

                submitted = st.form_submit_button(t("create_account_button"), use_container_width=True)

        if submitted:
            payload = {
                "name": name,
                "email": email,
                "password": password,
                "role": role,
                "facility_id": facility_names[facility_name],
                "date_of_birth": date_of_birth or None,
                "delivery_date": delivery_date or None,
                "license_id": license_id or None,
            }
            resp = api_post("/auth/register", json=payload)
            if resp.status_code == 201:
                st.success(t("registration_success"))
            else:
                st.error(resp.json().get("detail", t("registration_failed")))

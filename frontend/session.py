"""Session-state helpers (who is logged in, which language, which page)."""
import streamlit as st

def init_state():
    defaults = {
        "token": None,
        "role": None,
        "user_id": None,
        "name": None,
        "page": "login",
        "lang": "en",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def logout():
    for key in ["token", "role", "user_id", "name"]:
        st.session_state[key] = None
    st.session_state.page = "login"

"""All HTTP calls to the backend API go through here."""
import requests
import streamlit as st
from config import API_BASE_URL

def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def api_get(path, **kwargs):
    return requests.get(f"{API_BASE_URL}{path}", timeout=kwargs.pop("timeout", 60), **kwargs)


def api_post(path, **kwargs):
    return requests.post(f"{API_BASE_URL}{path}", timeout=kwargs.pop("timeout", 60), **kwargs)


@st.cache_data(ttl=60)
def get_facilities():
    resp = api_get("/facilities")
    resp.raise_for_status()
    return resp.json()

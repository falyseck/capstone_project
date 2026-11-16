"""Constants shared by the UI: API location, answer options, question text, risk colours."""
import os

import streamlit as st

def _api_url():
    """API address: environment variable first, then Streamlit secrets (Streamlit Cloud), then localhost."""
    url = os.environ.get("API_BASE_URL")
    if not url:
        try:
            url = st.secrets["API_BASE_URL"]
        except Exception:
            url = "http://localhost:8000"
    return url.rstrip("/")


API_BASE_URL = _api_url()

# Values sent to the API never change with the language toggle — only the
# labels shown to the person do. LEVEL_OPTIONS below stays in English and is
# rendered through format_func wherever the person sees it.
LEVEL_OPTIONS = ["No", "Sometimes", "Yes"]
AGE_OPTIONS = ["25-30", "30-35", "35-40", "40-45", "45-50"]
RISK_LEVELS = ["low", "medium", "high"]

SYMPTOM_QUESTIONS = [
    ("feeling_sad", "Have you been feeling sad or tearful?",
     "Avez-vous ressenti de la tristesse ou des larmes ?", "😔"),
    ("irritable", "Have you felt irritable towards your baby or partner?",
     "Avez-vous été irritable envers votre bébé ou votre partenaire ?", "😤"),
    ("trouble_sleeping", "Have you had trouble sleeping at night?",
     "Avez-vous eu du mal à dormir la nuit ?", "🌙"),
    ("trouble_concentrating", "Have you had problems concentrating or making decisions?",
     "Avez-vous eu des problèmes de concentration ou de prise de décision ?", "💭"),
    ("appetite_changes", "Have you noticed overeating or a loss of appetite?",
     "Avez-vous remarqué une suralimentation ou une perte d'appétit ?", "🍽️"),
    ("feeling_anxious", "Have you been feeling anxious?",
     "Vous êtes-vous sentie anxieuse ?", "💓"),
    ("feeling_guilty", "Have you had feelings of guilt?",
     "Avez-vous ressenti de la culpabilité ?", "🌧️"),
    ("bonding_difficulty", "Have you had problems bonding with your baby?",
     "Avez-vous eu des difficultés à créer un lien avec votre bébé ?", "🤝"),
]
SELF_HARM_QUESTION = (
    "self_harm_thoughts",
    "Have you had any thoughts of harming yourself?",
    "Avez-vous eu des pensées de vous faire du mal ?",
)

RISK_STYLE = {
    "low": {"color": "#2E7D4F", "bg": "#E8F6EE", "icon": "🟢"},
    "medium": {"color": "#B4740E", "bg": "#FFF4E0", "icon": "🟡"},
    "high": {"color": "#C23B3B", "bg": "#FDEAEA", "icon": "🔴"},
}

st.set_page_config(page_title="PPD Risk Screening", page_icon="🤱", layout="centered")

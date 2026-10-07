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
import os
from collections import Counter

import requests
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

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


# ---------------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------------
TRANSLATIONS = {
    "app_title": {"en": "PPD Risk Screening", "fr": "Dépistage du risque de DPP"},
    "app_subtitle": {
        "en": "A simple, private screening tool for postpartum depression risk.",
        "fr": "Un outil de dépistage simple et privé pour le risque de dépression post-partum.",
    },
    "login_tab": {"en": "🔑  Log in", "fr": "🔑  Connexion"},
    "register_tab": {"en": "📝  Register", "fr": "📝  Inscription"},
    "welcome_back": {"en": "Welcome back", "fr": "Content de vous revoir"},
    "email": {"en": "Email", "fr": "E-mail"},
    "password": {"en": "Password", "fr": "Mot de passe"},
    "login_button": {"en": "Log in", "fr": "Se connecter"},
    "login_failed": {"en": "Login failed.", "fr": "Échec de la connexion."},
    "api_unreachable": {
        "en": "Could not reach the API at {url}. Is it running?",
        "fr": "Impossible de joindre l'API à {url}. Est-elle en cours d'exécution ?",
    },
    "register_as": {"en": "I am registering as a", "fr": "Je m'inscris en tant que"},
    "mother": {"en": "Mother", "fr": "Mère"},
    "healthcare_worker": {"en": "Healthcare worker", "fr": "Professionnel de santé"},
    "create_account_title": {"en": "Create your {role} account", "fr": "Créez votre compte {role}"},
    "full_name": {"en": "Full name", "fr": "Nom complet"},
    "facility": {"en": "Facility", "fr": "Établissement"},
    "dob": {"en": "Date of birth (YYYY-MM-DD)", "fr": "Date de naissance (AAAA-MM-JJ)"},
    "delivery_date": {"en": "Delivery date (YYYY-MM-DD)", "fr": "Date d'accouchement (AAAA-MM-JJ)"},
    "license_id": {"en": "License / staff ID", "fr": "Numéro de licence / identifiant"},
    "create_account_button": {"en": "Create account", "fr": "Créer un compte"},
    "registration_success": {
        "en": "✅ Registration successful. You can now log in from the Log in tab.",
        "fr": "✅ Inscription réussie. Vous pouvez maintenant vous connecter depuis l'onglet Connexion.",
    },
    "registration_failed": {"en": "Registration failed.", "fr": "Échec de l'inscription."},

    "mother_greeting_subtitle": {
        "en": "Your wellbeing matters. Take a moment for yourself.",
        "fr": "Votre bien-être compte. Prenez un moment pour vous.",
    },
    "new_screening_tab": {"en": "🩺  New screening", "fr": "🩺  Nouveau dépistage"},
    "history_tab": {"en": "📖  My history", "fr": "📖  Mon historique"},
    "screening_intro": {
        "en": "Please answer honestly. This takes about two minutes, and your answers stay private.",
        "fr": "Merci de répondre honnêtement. Cela prend environ deux minutes et vos réponses restent privées.",
    },
    "age_label": {"en": "Your age range", "fr": "Votre tranche d'âge"},
    "self_harm_intro": {
        "en": "🕊️ **This last question is important. Please answer honestly — your answer "
              "will not change how you are treated, and help is always available.**",
        "fr": "🕊️ **Cette dernière question est importante. Merci de répondre honnêtement — "
              "votre réponse ne changera pas la façon dont vous êtes traitée, et de l'aide est "
              "toujours disponible.**",
    },
    "consent_text": {
        "en": "I understand that my answers will be used to assess my risk of postpartum "
              "depression, that my results may be seen by a healthcare worker at my facility "
              "to support my care, and that my data is kept private. I consent to this.",
        "fr": "Je comprends que mes réponses seront utilisées pour évaluer mon risque de "
              "dépression post-partum, que mes résultats pourront être consultés par un "
              "professionnel de santé de mon établissement afin de m'accompagner, et que mes "
              "données restent privées. J'y consens.",
    },
    "consent_required_warning": {
        "en": "Please confirm the consent checkbox before submitting.",
        "fr": "Veuillez cocher la case de consentement avant de soumettre.",
    },
    "submit_screening": {"en": "Submit screening", "fr": "Soumettre le dépistage"},
    "your_result": {"en": "Your result", "fr": "Votre résultat"},
    "session_expired": {
        "en": "Your session has expired. Please log in again.",
        "fr": "Votre session a expiré. Veuillez vous reconnecter.",
    },
    "submit_error": {
        "en": "Something went wrong submitting your form.",
        "fr": "Une erreur s'est produite lors de l'envoi de votre formulaire.",
    },
    "no_screenings_yet": {
        "en": "You have no screenings yet — your first one will show up here.",
        "fr": "Vous n'avez pas encore de dépistage — le premier apparaîtra ici.",
    },
    "history_load_error": {"en": "Could not load your history.", "fr": "Impossible de charger votre historique."},

    "worker_greeting_subtitle": {
        "en": "Mothers registered at your facility.",
        "fr": "Mères inscrites dans votre établissement.",
    },
    "patient_list_error": {
        "en": "Could not load your patient list.",
        "fr": "Impossible de charger la liste des patientes.",
    },
    "no_mothers": {
        "en": "No mothers are registered at your facility yet.",
        "fr": "Aucune mère n'est encore inscrite dans votre établissement.",
    },
    "select_patient": {"en": "Select a patient", "fr": "Sélectionner une patiente"},
    "latest_risk": {"en": "Latest risk level", "fr": "Dernier niveau de risque"},
    "total_screenings": {"en": "Total screenings", "fr": "Total des dépistages"},
    "report_tab": {"en": "📄  Generate report", "fr": "📄  Générer un rapport"},
    "analytics_tab": {"en": "📊  Facility analytics", "fr": "📊  Statistiques de l'établissement"},
    "report_intro": {
        "en": "Generate a written summary of this patient's screening history.",
        "fr": "Générer un résumé écrit de l'historique de dépistage de cette patiente.",
    },
    "generate_report_button": {"en": "Generate report", "fr": "Générer le rapport"},
    "forbidden": {
        "en": "You can only access mothers registered at your own facility.",
        "fr": "Vous ne pouvez accéder qu'aux mères inscrites dans votre propre établissement.",
    },
    "report_error": {"en": "Could not generate the report.", "fr": "Impossible de générer le rapport."},
    "no_screenings_on_record": {"en": "No screenings on record.", "fr": "Aucun dépistage enregistré."},

    "clinical_assessment_header": {
        "en": "Add your clinical assessment",
        "fr": "Ajouter votre évaluation clinique",
    },
    "clinical_assessment_intro": {
        "en": "Record your own independent judgment for a screening, kept separate from the "
              "ML prediction. This is what lets future data train a stronger, non-circular model.",
        "fr": "Enregistrez votre propre jugement indépendant pour un dépistage, distinct de la "
              "prédiction du modèle. C'est ce qui permettra aux futures données d'entraîner un "
              "modèle plus solide et non circulaire.",
    },
    "select_screening": {"en": "Select a screening", "fr": "Sélectionner un dépistage"},
    "your_assessment": {"en": "Your risk assessment", "fr": "Votre évaluation du risque"},
    "notes_optional": {"en": "Notes (optional)", "fr": "Remarques (facultatif)"},
    "save_assessment": {"en": "Save assessment", "fr": "Enregistrer l'évaluation"},
    "assessment_saved": {"en": "✅ Clinical assessment saved.", "fr": "✅ Évaluation clinique enregistrée."},
    "assessment_error": {"en": "Could not save the assessment.", "fr": "Impossible d'enregistrer l'évaluation."},
    "clinical_label": {"en": "Clinical assessment", "fr": "Évaluation clinique"},
    "ml_label": {"en": "ML prediction", "fr": "Prédiction du modèle"},
    "not_yet_assessed": {"en": "not yet reviewed by staff", "fr": "pas encore examiné par le personnel"},

    "analytics_intro": {
        "en": "Risk level distribution across all mothers at your facility, based on each "
              "mother's latest screening.",
        "fr": "Répartition des niveaux de risque parmi toutes les mères de votre établissement, "
              "d'après le dernier dépistage de chacune.",
    },
    "no_data_for_analytics": {
        "en": "Not enough data yet to show analytics.",
        "fr": "Pas encore assez de données pour afficher les statistiques.",
    },
    "mothers_screened": {"en": "Mothers screened", "fr": "Mères dépistées"},
    "crisis_flags_total": {"en": "Crisis flags raised", "fr": "Alertes de crise déclenchées"},

    "logout": {"en": "Log out", "fr": "Déconnexion"},
    "language_label": {"en": "Language", "fr": "Langue"},
    "not_available": {"en": "Not available", "fr": "Non disponible"},
    "crisis_note": {"en": "crisis check flagged", "fr": "alerte de crise déclenchée"},
}

RISK_LABELS = {
    "low": {"en": "Low risk", "fr": "Risque faible"},
    "medium": {"en": "Medium risk", "fr": "Risque moyen"},
    "high": {"en": "High risk", "fr": "Risque élevé"},
}

LEVEL_OPTION_LABELS = {
    "No": {"en": "No", "fr": "Non"},
    "Sometimes": {"en": "Sometimes", "fr": "Parfois"},
    "Yes": {"en": "Yes", "fr": "Oui"},
}


def lang() -> str:
    return st.session_state.get("lang", "en")


def t(key: str, **kwargs) -> str:
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    text = entry.get(lang(), entry.get("en", key))
    return text.format(**kwargs) if kwargs else text


def risk_label(risk_level: str) -> str:
    entry = RISK_LABELS.get(risk_level)
    if not entry:
        return t("not_available")
    return entry.get(lang(), entry.get("en"))


def level_option_label(value: str) -> str:
    entry = LEVEL_OPTION_LABELS.get(value, {})
    return entry.get(lang(), value)


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
def inject_css():
    st.markdown(
        """
        <style>
        :root {
            --rose-50: #FFF7F9;
            --rose-100: #FDEEF2;
            --rose-500: #D8768F;
            --rose-600: #C25776;
            --plum-700: #4A2E44;
            --ink: #3A2E3E;
            --muted: #8A7A87;
            --card-border: #F0DDE3;
        }

        .stApp {
            background: linear-gradient(180deg, var(--rose-50) 0%, #FFFFFF 320px);
        }

        /* Headings */
        h1, h2, h3 { color: var(--plum-700) !important; }

        /* Buttons */
        .stButton > button, .stFormSubmitButton > button {
            background: linear-gradient(135deg, var(--rose-500), var(--rose-600));
            color: white;
            border: none;
            border-radius: 10px;
            padding: 0.55rem 1rem;
            font-weight: 600;
            transition: opacity 0.15s ease;
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover {
            opacity: 0.9;
            color: white;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] { gap: 4px; }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            padding: 8px 18px;
            color: var(--muted);
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            color: var(--rose-600) !important;
            border-bottom: 3px solid var(--rose-500) !important;
        }

        /* Cards (st.container(border=True)) */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 14px !important;
            border: 1px solid var(--card-border) !important;
            background: white;
            box-shadow: 0 2px 10px rgba(196, 88, 120, 0.06);
        }

        /* Radio pills laid out horizontally */
        div[role="radiogroup"] {
            gap: 6px;
        }
        div[role="radiogroup"] label {
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 4px 14px !important;
            background: var(--rose-50);
        }

        /* App header */
        .app-header {
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 0.25rem;
        }
        .app-header .logo {
            width: 46px; height: 46px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--rose-500), #E39BB0);
            display: flex; align-items: center; justify-content: center;
            font-size: 22px;
        }
        .app-header .titles h1 {
            margin: 0; font-size: 1.5rem; line-height: 1.2;
        }
        .app-header .titles p {
            margin: 0; color: var(--muted); font-size: 0.9rem;
        }

        /* Risk badge */
        .risk-badge {
            display: inline-flex; align-items: center; gap: 8px;
            padding: 10px 18px; border-radius: 12px;
            font-weight: 700; font-size: 1.05rem;
            margin: 6px 0 10px 0;
        }

        /* History timeline card */
        .history-card {
            border-left: 4px solid var(--rose-500);
            background: var(--rose-50);
            border-radius: 8px;
            padding: 10px 14px;
            margin-bottom: 8px;
        }
        .history-card .date { font-weight: 700; color: var(--plum-700); }
        .history-card .meta { color: var(--muted); font-size: 0.85rem; }
        .history-card .clinical { color: var(--plum-700); font-size: 0.85rem; margin-top: 2px; }

        /* Sidebar user card */
        .user-card {
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 14px;
            background: var(--rose-50);
            text-align: center;
            margin-bottom: 10px;
        }
        .user-card .avatar {
            width: 52px; height: 52px; border-radius: 50%;
            background: linear-gradient(135deg, var(--rose-500), #E39BB0);
            color: white; display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 1.1rem; margin: 0 auto 8px auto;
        }
        .role-pill {
            display: inline-block; margin-top: 4px;
            background: white; border: 1px solid var(--card-border);
            border-radius: 20px; padding: 2px 10px; font-size: 0.78rem; color: var(--rose-600);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(title: str, subtitle: str, icon: str = "🤱"):
    st.markdown(
        f"""
        <div class="app-header">
            <div class="logo">{icon}</div>
            <div class="titles">
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def risk_badge(risk_level: str):
    style = RISK_STYLE.get(risk_level, RISK_STYLE["medium"])
    st.markdown(
        f"""
        <div class="risk-badge" style="background:{style['bg']}; color:{style['color']};">
            {style['icon']} {risk_label(risk_level)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def history_card_html(date_str, risk_level, crisis_flagged, clinical_risk_level=None, clinical_notes=None):
    style = RISK_STYLE.get(risk_level, {"icon": "⚪"})
    crisis_note = f" · ⚠️ {t('crisis_note')}" if crisis_flagged else ""
    ml_label_text = risk_label(risk_level) if risk_level else t("not_available")

    clinical_html = ""
    if clinical_risk_level:
        note_suffix = f" — “{clinical_notes}”" if clinical_notes else ""
        clinical_html = (
            f"<div class='clinical'>🩺 {t('clinical_label')}: "
            f"<strong>{risk_label(clinical_risk_level)}</strong>{note_suffix}</div>"
        )

    return f"""
    <div class="history-card">
        <div class="date">{style.get('icon', '⚪')} {date_str}</div>
        <div class="meta">{t('ml_label')}: {ml_label_text}{crisis_note}</div>
        {clinical_html}
    </div>
    """


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------
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


def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def logout():
    for key in ["token", "role", "user_id", "name"]:
        st.session_state[key] = None
    st.session_state.page = "login"


def api_get(path, **kwargs):
    return requests.get(f"{API_BASE_URL}{path}", **kwargs)


def api_post(path, **kwargs):
    return requests.post(f"{API_BASE_URL}{path}", **kwargs)


@st.cache_data(ttl=60)
def get_facilities():
    resp = api_get("/facilities")
    resp.raise_for_status()
    return resp.json()


def language_toggle(key: str):
    options = ["en", "fr"]
    labels = {"en": "English", "fr": "Français"}
    choice = st.selectbox(
        t("language_label"),
        options,
        index=options.index(st.session_state.lang),
        format_func=lambda v: labels[v],
        key=key,
    )
    if choice != st.session_state.lang:
        st.session_state.lang = choice
        st.rerun()


# ---------------------------------------------------------------------------
# Auth screens
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Mother screens
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Healthcare worker screens
# ---------------------------------------------------------------------------
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
        [t("history_tab"), t("report_tab"), t("analytics_tab")]
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
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

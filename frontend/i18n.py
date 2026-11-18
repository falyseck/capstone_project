"""English/French strings and the helpers that look them up for the active language."""
import streamlit as st

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
    "patient_history_tab": {"en": "📖  Screening history", "fr": "📖  Historique des dépistages"},
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
    "recommendation_low": {
        "en": "Your answers show a low level of postpartum depression symptoms right now. "
              "Keep taking care of yourself, and mention how you are feeling at your next checkup.",
        "fr": "Vos réponses indiquent actuellement un faible niveau de symptômes de dépression "
              "post-partum. Continuez à prendre soin de vous et parlez de votre état lors de "
              "votre prochain rendez-vous médical.",
    },
    "recommendation_medium": {
        "en": "Your answers show some signs of postpartum depression. This does not mean something "
              "is wrong with you. Please mention these feelings to your doctor, nurse, or midwife at "
              "your next visit, or sooner if things get harder.",
        "fr": "Vos réponses indiquent certains signes de dépression post-partum. Cela ne signifie "
              "pas qu'il y a quelque chose qui ne va pas chez vous. Parlez-en à votre médecin, "
              "infirmier ou sage-femme lors de votre prochain rendez-vous, ou plus tôt si votre "
              "état s'aggrave.",
    },
    "recommendation_high": {
        "en": "Your answers show a high level of postpartum depression symptoms. We strongly recommend "
              "you see a doctor or health worker soon to talk about how you are feeling. You do not have "
              "to go through this alone.",
        "fr": "Vos réponses indiquent un niveau élevé de symptômes de dépression post-partum. Nous "
              "vous recommandons vivement de consulter bientôt un médecin ou un professionnel de "
              "santé pour parler de votre état. Vous n'avez pas à traverser cette situation seule.",
    },
    "crisis_message": {
        "en": "You mentioned thoughts of harming yourself. Your safety matters right now. "
              "Please reach out to a doctor, health worker, or emergency service near you immediately, "
              "or go to the nearest health facility. If you are in danger right now, call the National "
              "Mental Health Helpline at +221 33 889 38 00. You are not alone, and help is available.",
        "fr": "Vous avez mentionné des pensées de vous faire du mal. Votre sécurité est importante "
              "en ce moment. Contactez immédiatement un médecin, un professionnel de santé ou les "
              "services d'urgence près de chez vous, ou rendez-vous au centre de santé le plus proche. "
              "Si vous êtes en danger immédiat, appelez la ligne nationale d'écoute en santé mentale "
              "au +221 33 889 38 00. Vous n'êtes pas seule, de l'aide est disponible.",
    },
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
    "submitted_answers": {
        "en": "Patient's answers",
        "fr": "Réponses de la patiente",
    },
    "age_range": {"en": "Age range", "fr": "Tranche d'âge"},
    "select_screening": {"en": "Select a screening", "fr": "Sélectionner un dépistage"},
    "your_assessment": {"en": "Your risk assessment", "fr": "Votre évaluation du risque"},
    "notes_optional": {"en": "Notes (optional)", "fr": "Remarques (facultatif)"},
    "save_assessment": {"en": "Save assessment", "fr": "Enregistrer l'évaluation"},
    "assessment_saved": {"en": "✅ Clinical assessment saved.", "fr": "✅ Évaluation clinique enregistrée."},
    "assessment_error": {"en": "Could not save the assessment.", "fr": "Impossible d'enregistrer l'évaluation."},
    "clinical_label": {"en": "Clinical assessment", "fr": "Évaluation clinique"},
    "ml_label": {"en": "Screening result", "fr": "Résultat du dépistage"},
    "not_yet_assessed": {"en": "not yet reviewed by staff", "fr": "pas encore examiné par le personnel"},

    "analytics_intro": {
        "en": "Risk level distribution across all screenings at your facility. Each screening "
              "submission is counted, including multiple screenings by the same mother.",
        "fr": "Répartition des niveaux de risque pour tous les dépistages de votre établissement. "
              "Chaque dépistage est compté, y compris les dépistages répétés d'une même mère.",
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

"""Small reusable UI pieces: header, risk badge, history card, language toggle."""
import streamlit as st
from config import RISK_STYLE
from i18n import risk_label, t

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

"""Global CSS for the Streamlit app."""
import streamlit as st

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

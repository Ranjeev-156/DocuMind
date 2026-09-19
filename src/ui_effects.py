import streamlit as st


def apply_ui_effects():
    """Apply DocuMind's visual design and lightweight animations."""


    st.markdown(
        """
        <style>

        /* =========================================
           GLOBAL
           ========================================= */

        .stApp {
            animation: documindFade 0.45s ease-out;
        }

        @keyframes documindFade {
            from {
                opacity: 0;
                transform: translateY(8px);
            }

            to {
                opacity: 1;
                transform: translateY(0);
            }
        }


        /* =========================================
           MAIN CONTENT
           ========================================= */

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }


        /* =========================================
           HEADINGS
           ========================================= */

        h1 {
            letter-spacing: -0.03em;
            font-weight: 750;
        }

        h2 {
            letter-spacing: -0.02em;
            font-weight: 700;
        }

        h3 {
            font-weight: 650;
        }


        /* =========================================
           METRIC CARDS
           ========================================= */

        [data-testid="stMetric"] {
            padding: 1.15rem 1.25rem;
            border-radius: 16px;
            border: 1px solid rgba(128, 128, 128, 0.18);
            background: rgba(128, 128, 128, 0.045);
            transition:
                transform 0.22s ease,
                box-shadow 0.22s ease,
                border-color 0.22s ease;
        }

        [data-testid="stMetric"]:hover {
            transform: translateY(-4px);
            box-shadow:
                0 12px 30px rgba(0, 0, 0, 0.10);
            border-color: rgba(128, 128, 128, 0.35);
        }

        [data-testid="stMetricValue"] {
            font-weight: 750;
            letter-spacing: -0.02em;
        }


        /* =========================================
           CARDS
           ========================================= */

        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 18px;
            transition:
                transform 0.25s ease,
                box-shadow 0.25s ease,
                border-color 0.25s ease;
        }

        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            transform: translateY(-4px);
            box-shadow:
                0 14px 35px rgba(0, 0, 0, 0.10);
        }


        /* =========================================
           BUTTONS
           ========================================= */

        .stButton > button {
            border-radius: 12px;
            font-weight: 600;
            transition:
                transform 0.18s ease,
                box-shadow 0.18s ease;
        }

        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow:
                0 8px 20px rgba(0, 0, 0, 0.12);
        }

        .stButton > button:active {
            transform: translateY(0);
        }


        /* =========================================
           INPUTS
           ========================================= */

        .stTextInput input,
        .stTextArea textarea {
            border-radius: 12px;
            transition:
                border-color 0.2s ease,
                box-shadow 0.2s ease;
        }

        .stTextInput input:focus,
        .stTextArea textarea:focus {
            box-shadow:
                0 0 0 2px rgba(100, 100, 255, 0.12);
        }


        /* =========================================
           FILE UPLOADER
           ========================================= */

        [data-testid="stFileUploader"] {
            border-radius: 16px;
            transition:
                transform 0.2s ease,
                box-shadow 0.2s ease;
        }

        [data-testid="stFileUploader"]:hover {
            transform: translateY(-2px);
            box-shadow:
                0 10px 28px rgba(0, 0, 0, 0.08);
        }


        /* =========================================
           ALERTS
           ========================================= */

        [data-testid="stAlert"] {
            border-radius: 12px;
        }


        /* =========================================
           SIDEBAR
           ========================================= */

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(128, 128, 128, 0.16);
        }

        [data-testid="stSidebar"] .stRadio label {
            transition:
                transform 0.15s ease;
        }

        [data-testid="stSidebar"] .stRadio label:hover {
            transform: translateX(3px);
        }


        /* =========================================
           DIVIDERS
           ========================================= */

        hr {
            margin-top: 1.5rem;
            margin-bottom: 1.5rem;
            opacity: 0.35;
        }


        /* =========================================
           REDUCE MOTION
           ========================================= */

        @media (prefers-reduced-motion: reduce) {

            *,
            *::before,
            *::after {
                animation: none !important;
                transition: none !important;
            }

        }

        </style>
        """,
        unsafe_allow_html=True,
    )
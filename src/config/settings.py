import streamlit as st


def get_secret(name: str, default=None):
    """Safely read a value from Streamlit secrets."""
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default
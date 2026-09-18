import streamlit as st

from src.auth.auth import (
    get_current_user,
    is_logged_in,
    login_user,
    logout_user,
)
from src.ui import render_sidebar

# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="DocuMind AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)




# -----------------------------
# Login page
# -----------------------------
def login_page():
    st.title("📚 DocuMind AI")
    st.subheader("Intelligent Document Analytics")

    st.write("Sign in to continue.")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", type="primary"):
        if username and password:
            login_user(username)
            st.rerun()
            st.rerun()
        else:
            st.error("Please enter both username and password.")


# -----------------------------
# Dashboard
# -----------------------------
def dashboard():
    page = render_sidebar()
    st.title("🏠 DocuMind Dashboard")

    username = get_current_user()

    st.success(f"Welcome, {username}!")

    st.write("Your DocuMind workspace is ready.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Documents", "0")

    with col2:
        st.metric("Questions", "0")

    with col3:
        st.metric("Sources", "0")

    st.divider()

    st.subheader("Get started")

    st.info(
        "Upload a document or paste text to start building your "
        "AI-powered knowledge base."
    )

    if st.button("Logout"):
        logout_user()
        st.rerun()


# -----------------------------
# Application router
# -----------------------------
if is_logged_in():
    dashboard()
else:
    login_page()
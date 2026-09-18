from src.ui import render_sidebar
import streamlit as st

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
# Session state
# -----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


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
            st.session_state.logged_in = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Please enter both username and password.")


# -----------------------------
# Dashboard
# -----------------------------
def dashboard():
    page = render_sidebar()
    st.title("🏠 DocuMind Dashboard")

    username = st.session_state.get("username", "User")

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
        st.session_state.clear()
        st.rerun()


# -----------------------------
# Application router
# -----------------------------
if st.session_state.logged_in:
    dashboard()
else:
    login_page()
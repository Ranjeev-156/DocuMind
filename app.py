from src.documents.loader import (
    get_file_size_mb,
    get_file_type,
    is_supported_file,
)

import streamlit as st

from src.auth.auth import (
    get_current_user,
    is_logged_in,
    login_user,
    logout_user,
)
from src.ui import render_sidebar
MAX_FILE_MB = 15
MAX_FILES = 5
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

    username = get_current_user()

    if page == "🏠 Dashboard":
        st.title("🏠 DocuMind Dashboard")

        st.success(f"Welcome, {username}!")

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

    elif page == "📄 Documents":
        st.title("📄 Documents")

        st.write("Upload documents to build your knowledge base.")

        uploaded_files = st.file_uploader(
            "Choose documents",
            type=["pdf", "txt", "md", "csv", "xlsx"],
            accept_multiple_files=True,
            help=f"Maximum {MAX_FILES} files, {MAX_FILE_MB} MB per file.",
        )

        if uploaded_files:

            if len(uploaded_files) > MAX_FILES:
                st.error(
                    f"You selected {len(uploaded_files)} files. "
                    f"The maximum allowed is {MAX_FILES}."
                )
                uploaded_files = uploaded_files[:MAX_FILES]

                st.success(f"{len(uploaded_files)} document(s) selected.")

            for uploaded_file in uploaded_files:

                file_size_mb = get_file_size_mb(
                    uploaded_file.getvalue()
                )

                col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.write(f"📄 **{uploaded_file.name}**")

            with col2:
                st.write(f"{file_size_mb:.2f} MB")

            with col3:
                st.write(get_file_type(uploaded_file.name))

            if file_size_mb > MAX_FILE_MB:
                st.error(
                    f"File is too large. Maximum size is "
                    f"{MAX_FILE_MB} MB."
                )

            elif not is_supported_file(uploaded_file.name):
                st.error("Unsupported file type.")

            else:
                st.success("✓ File accepted")
    elif page == "💬 AI Chat":
        st.title("💬 AI Chat")

        st.info("AI chat system coming soon.")

    elif page == "📊 Analytics":
        st.title("📊 Analytics")

        st.info("Analytics system coming soon.")

    elif page == "⚙️ Settings":
        st.title("⚙️ Settings")

        st.info("Application settings coming soon.")

    st.divider()

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
import streamlit as st


def is_logged_in() -> bool:
    """Check whether the current user is authenticated."""
    return st.session_state.get("logged_in", False)


def login_user(username: str):
    """Create the current login session."""
    st.session_state.logged_in = True
    st.session_state.username = username


def logout_user():
    """Clear the current login session."""
    st.session_state.clear()


def get_current_user() -> str:
    """Return the currently logged-in username."""
    return st.session_state.get("username", "User")
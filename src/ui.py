import streamlit as st


def render_sidebar():
    with st.sidebar:
        st.markdown("## 📚 DocuMind AI")
        st.caption("Intelligent Document Analytics")

        st.divider()

        page = st.radio(
            "Navigation",
            [
                "🏠 Dashboard",
                "📄 Documents",
                "💬 AI Chat",
                "📊 Analytics",
                "⚙️ Settings",
            ],
        )

        st.divider()

        st.caption("DocuMind-v7")
        st.caption("AI-powered document intelligence")

    return page
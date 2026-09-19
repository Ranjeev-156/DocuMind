import re

import streamlit as st
from streamlit_js_eval import streamlit_js_eval

from src.workspace import (
    create_workspace,
    generate_workspace_id,
    get_workspace,
    workspace_exists,
)

from src.documents.extractor import extract_document

from src.documents.loader import (
    get_file_size_mb,
    get_file_type,
    is_supported_file,
)

from src.rag.ingest import ingest_document

from src.rag.vector_store import (
    delete_document,
    get_document_count,
    list_documents,
    search_documents,
)

from src.rag.generator import (
    build_retrieval_query,
    generate_answer,
)

from src.ui import render_sidebar
from src.ui_effects import apply_ui_effects


# =========================================================
# CONFIGURATION
# =========================================================

MAX_FILE_MB = 15
MAX_FILES = 5

# Number of chunks retrieved for one question.
MAX_RESULTS = 8

# Maximum retrieved text sent to the AI.
MAX_CONTEXT_CHARS = 24000

# Maximum previous conversation sent to the AI.
MAX_CONVERSATION_CHARS = 6000

REMEMBER_WORKSPACE_KEY = "documind_remembered_workspace"


# =========================================================
# AI OPTIONS
# =========================================================

PROVIDER_SMART = "Smart Mode"
PROVIDER_LOCAL = "Local AI — Llama 3.2"
PROVIDER_OPENROUTER = "OpenRouter — Free"

ANSWER_MODE_GROUNDED = "Grounded Mode"
ANSWER_MODE_ADAPTIVE = "Adaptive Mode"


PROVIDER_LABELS = {
    PROVIDER_SMART: "⚡ Smart AI",
    PROVIDER_LOCAL: "🖥️ Local AI — Llama 3.2",
    PROVIDER_OPENROUTER: "☁️ OpenRouter — Free",
}


ANSWER_MODE_LABELS = {
    ANSWER_MODE_GROUNDED: "📚 Grounded Mode",
    ANSWER_MODE_ADAPTIVE: "🧠 Adaptive Mode",
}


# =========================================================
# CONVERSATION CONTEXT
# =========================================================

def build_conversation_context(
    chat_history,
    max_chars=MAX_CONVERSATION_CHARS,
):
    """
    Build a compact conversation context for follow-up
    questions.

    Example:

    User: What is velocity?
    Assistant: Velocity is...

    User: Is it a vector quantity?

    The generator can therefore understand that "it"
    refers to velocity.
    """

    if not chat_history:
        return ""

    lines = []

    # Use only the most recent messages.
    recent_messages = chat_history[-8:]

    for message in recent_messages:

        role = message.get("role", "")
        content = str(
            message.get("content", "")
        ).strip()

        if not content:
            continue

        if role == "user":
            label = "User"
        elif role == "assistant":
            label = "Assistant"
        else:
            continue

        lines.append(
            f"{label}: {content}"
        )

    conversation = "\n\n".join(lines).strip()

    if len(conversation) > max_chars:
        conversation = (
            conversation[
                -max_chars:
            ]
        )

    return conversation


# =========================================================
# WORKSPACE MEMORY
# =========================================================

def get_remembered_workspace():
    """Read the remembered Workspace ID from this browser."""

    try:
        value = streamlit_js_eval(
            js_expressions=(
                f'localStorage.getItem("{REMEMBER_WORKSPACE_KEY}")'
            ),
            want_output=True,
            key="read_remembered_workspace",
        )

        if value and str(value).strip():
            return str(value).strip()

    except Exception:
        pass

    return None


def remember_workspace(workspace_id):
    """Store only the Workspace ID in browser localStorage."""

    if not workspace_id:
        return

    safe_id = (
        str(workspace_id)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
    )

    try:
        streamlit_js_eval(
            js_expressions=(
                f'localStorage.setItem('
                f'"{REMEMBER_WORKSPACE_KEY}", '
                f'"{safe_id}")'
            ),
            want_output=False,
            key="save_remembered_workspace",
        )

    except Exception:
        pass


def forget_workspace():
    """Remove the remembered Workspace ID from this browser."""

    try:
        streamlit_js_eval(
            js_expressions=(
                f'localStorage.removeItem('
                f'"{REMEMBER_WORKSPACE_KEY}")'
            ),
            want_output=False,
            key="forget_remembered_workspace",
        )

    except Exception:
        pass


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="DocuMind AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# UI EFFECTS
# =========================================================

apply_ui_effects()


# =========================================================
# WORKSPACE SYSTEM
# =========================================================

if "workspace_id" not in st.session_state:
    st.session_state.workspace_id = None

if "logged_out" not in st.session_state:
    st.session_state.logged_out = False


# =========================================================
# OPEN EXISTING WORKSPACE
# =========================================================

if (
    st.session_state.workspace_id is None
    and not st.session_state.logged_out
):

    remembered_id = get_remembered_workspace()

    if remembered_id:

        remembered_data = get_workspace(
            remembered_id
        )

        if remembered_data is not None:

            st.session_state.workspace_id = (
                remembered_id
            )

            st.rerun()

        else:

            forget_workspace()


# =========================================================
# CREATE / OPEN WORKSPACE
# =========================================================

if st.session_state.workspace_id is None:

    st.markdown(
        "<div style='height: 8vh;'></div>",
        unsafe_allow_html=True,
    )

    left, center, right = st.columns(
        [1, 2, 1]
    )

    with center:

        with st.container(border=True):

            st.markdown(
                "# 📚 DocuMind AI"
            )

            st.subheader(
                "Welcome 👋"
            )

            st.write(
                "Create your personal DocuMind workspace."
            )

            st.divider()

            st.markdown(
                "### Enter your name"
            )

            name = st.text_input(
                "Your name",
                placeholder="Enter your name",
                label_visibility="collapsed",
            )

            st.markdown(
                "### Create a unique Workspace ID"
            )

            workspace_id = st.text_input(
                "Workspace ID",
                placeholder="example: ranjeev_physics_27",
                label_visibility="collapsed",
            )

            st.caption(
                "Your Workspace ID identifies your "
                "documents and chat history."
            )

            st.info(
                "Workspace ID must use lowercase letters only. "
                "Example: `ranjeev156`"
            )

            remember_this_workspace = st.checkbox(
                "Remember this workspace on this browser",
                value=True,
                help=(
                    "Stores only the Workspace ID in this "
                    "browser so you can reopen it "
                    "automatically next time."
                ),
            )

            if not workspace_id:

                generated_id = generate_workspace_id()

                st.info(
                    f"💡 Suggested ID: `{generated_id}`"
                )

            if st.button(
                "🚀 Create Workspace",
                type="primary",
                use_container_width=True,
            ):

                if not name.strip():

                    st.warning(
                        "Please enter your name."
                    )

                elif not workspace_id.strip():

                    st.warning(
                        "Please enter a Workspace ID."
                    )

                elif workspace_id != workspace_id.lower():

                    st.error(
                        "Please enter your Workspace ID "
                        "using lowercase letters only. "
                        "Example: `ranjeev156`"
                    )

                elif not re.fullmatch(
                    r"[a-z0-9_]+",
                    workspace_id,
                ):

                    st.error(
                        "Workspace ID can contain only "
                        "lowercase letters, numbers, "
                        "and underscores."
                    )

                elif workspace_exists(
                    workspace_id
                ):

                    st.error(
                        "That Workspace ID already exists. "
                        "Please choose another one."
                    )

                else:

                    try:

                        created_id = create_workspace(
                            name,
                            workspace_id,
                        )

                        st.session_state.workspace_id = (
                            created_id
                        )

                        st.session_state.logged_out = False

                        if remember_this_workspace:

                            remember_workspace(
                                created_id
                            )

                        else:

                            forget_workspace()

                        st.rerun()

                    except Exception as error:

                        st.error(
                            f"Could not create workspace: "
                            f"{error}"
                        )

            st.divider()

            st.markdown(
                "### 🔑 Already have a Workspace ID?"
            )

            existing_id = st.text_input(
                "Existing Workspace ID",
                placeholder="Enter your Workspace ID",
                key="existing_workspace_id",
            )

            if st.button(
                "Open Workspace →",
                use_container_width=True,
            ):

                existing_id = existing_id.strip()

                if not existing_id:

                    st.warning(
                        "Please enter your Workspace ID."
                    )

                else:

                    existing_workspace = get_workspace(
                        existing_id
                    )

                    if existing_workspace is None:

                        st.error(
                            "Workspace not found. "
                            "Check the Workspace ID exactly "
                            "as it was created."
                        )

                    else:

                        canonical_id = (
                            existing_workspace[
                                "workspace_id"
                            ]
                        )

                        st.session_state.workspace_id = (
                            canonical_id
                        )

                        st.session_state.logged_out = False

                        if remember_this_workspace:

                            remember_workspace(
                                canonical_id
                            )

                        else:

                            forget_workspace()

                        st.rerun()

    st.stop()


# =========================================================
# CURRENT WORKSPACE
# =========================================================

workspace = get_workspace(
    st.session_state.workspace_id
)

if workspace is None:

    forget_workspace()

    st.session_state.workspace_id = None
    st.session_state.logged_out = True

    st.error(
        "This workspace could not be found. "
        "Please open it again with a valid Workspace ID."
    )

    st.stop()


WORKSPACE_ID = workspace["workspace_id"]
USER_NAME = workspace["name"]


# =========================================================
# SESSION STATE
# =========================================================

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "questions_count" not in st.session_state:
    st.session_state.questions_count = 0

if "ai_provider" not in st.session_state:
    st.session_state.ai_provider = PROVIDER_SMART

if "answer_mode" not in st.session_state:
    st.session_state.answer_mode = ANSWER_MODE_ADAPTIVE

if "extracted_pdf_text" not in st.session_state:
    st.session_state.extracted_pdf_text = ""

if "extracted_pdf_name" not in st.session_state:
    st.session_state.extracted_pdf_name = ""


# =========================================================
# SIDEBAR
# =========================================================

page = render_sidebar()


# =========================================================
# DASHBOARD
# =========================================================

if page == "🏠 Dashboard":

    st.title("📚 DocuMind AI")

    st.subheader(
        f"Welcome back, {USER_NAME} 👋"
    )

    st.subheader(
        "Intelligent Document Analytics"
    )

    st.write(
        "Understand, search and chat with your documents "
        "using AI."
    )

    st.divider()

    st.subheader("🚀 Get started")

    col1, col2 = st.columns(2)

    with col1:

        with st.container(border=True):

            st.markdown(
                "### 📄 Add documents"
            )

            st.write(
                "Upload documents and build your "
                "AI-powered knowledge base."
            )

            st.caption(
                "PDF, TXT, MD, CSV and XLSX supported."
            )

            if st.button(
                "📄 Add Documents →",
                key="dashboard_documents",
                use_container_width=True,
                type="primary",
            ):

                st.info(
                    "Open **📄 Documents** from the "
                    "sidebar to upload your files."
                )

    with col2:

        with st.container(border=True):

            st.markdown(
                "### 💬 Ask your documents"
            )

            st.write(
                "Ask questions and get answers based "
                "on your stored documents."
            )

            st.caption(
                "Choose Smart AI, Local AI, or OpenRouter Free."
            )

            if st.button(
                "💬 Ask Questions →",
                key="dashboard_chat",
                use_container_width=True,
            ):

                st.info(
                    "Open **💬 AI Chat** from the "
                    "sidebar to start asking questions."
                )

    st.divider()

    st.subheader(
        "📋 Paste Your Text"
    )

    with st.container(border=True):

        pasted_text_dashboard = st.text_area(
            "Paste your text",
            height=180,
            placeholder=(
                "Paste notes, articles, study material, "
                "documentation, or any other text..."
            ),
            key="dashboard_paste_text",
        )

        if st.button(
            "➕ Add Text to Knowledge Base",
            key="dashboard_add_text",
            type="primary",
            use_container_width=True,
        ):

            if not pasted_text_dashboard.strip():

                st.warning(
                    "Please paste some text first."
                )

            else:

                try:

                    with st.spinner(
                        "Processing your text..."
                    ):

                        chunk_count = ingest_document(
                            WORKSPACE_ID,
                            "Pasted Text",
                            pasted_text_dashboard,
                        )

                    st.success(
                        "✓ Text added to your knowledge base."
                    )

                    st.info(
                        f"Created {chunk_count} "
                        "document chunk(s)."
                    )

                except Exception as error:

                    st.error(
                        f"Could not add text: {error}"
                    )

    st.divider()

    st.subheader(
        "📊 Workspace"
    )

    documents = list_documents(
        WORKSPACE_ID
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Documents",
            len(documents),
        )

    with col2:

        st.metric(
            "Indexed Chunks",
            get_document_count(
                WORKSPACE_ID
            ),
        )

    with col3:

        st.metric(
            "Questions",
            st.session_state.questions_count,
        )


# =========================================================
# DOCUMENTS
# =========================================================

elif page == "📄 Documents":

    st.title(
        "📄 Documents"
    )

    st.write(
        "Upload documents or paste text into your "
        "DocuMind knowledge base."
    )

    st.divider()

    st.subheader(
        "📄 Document Input"
    )

    uploaded_files = st.file_uploader(
        "Choose documents",
        type=[
            "pdf",
            "txt",
            "md",
            "csv",
            "xlsx",
        ],
        accept_multiple_files=True,
        help=(
            f"Maximum {MAX_FILES} files, "
            f"{MAX_FILE_MB} MB per file."
        ),
    )

    if uploaded_files:

        if len(uploaded_files) > MAX_FILES:

            st.error(
                f"You selected {len(uploaded_files)} files. "
                f"The maximum allowed is {MAX_FILES}."
            )

            uploaded_files = uploaded_files[
                :MAX_FILES
            ]

        st.success(
            f"{len(uploaded_files)} document(s) selected."
        )

        for uploaded_file in uploaded_files:

            file_bytes = uploaded_file.getvalue()

            file_size_mb = get_file_size_mb(
                file_bytes
            )

            file_type = get_file_type(
                uploaded_file.name
            )

            with st.container(border=True):

                col1, col2, col3 = st.columns(
                    [4, 1, 1]
                )

                with col1:

                    st.write(
                        f"📄 **{uploaded_file.name}**"
                    )

                with col2:

                    st.write(
                        f"{file_size_mb:.2f} MB"
                    )

                with col3:

                    st.write(
                        file_type.upper()
                    )

                if file_size_mb > MAX_FILE_MB:

                    st.error(
                        f"File is too large. "
                        f"Maximum size is "
                        f"{MAX_FILE_MB} MB."
                    )

                elif not is_supported_file(
                    uploaded_file.name
                ):

                    st.error(
                        "Unsupported file type."
                    )

                else:

                    st.success(
                        "✓ File accepted"
                    )

                    if st.button(
                        f"Process {uploaded_file.name}",
                        key=f"process_{uploaded_file.name}",
                        type="primary",
                        use_container_width=True,
                    ):

                        try:

                            with st.spinner(
                                "Extracting and indexing..."
                            ):

                                extracted_text = (
                                    extract_document(
                                        uploaded_file.name,
                                        file_bytes,
                                    )
                                )

                                if not extracted_text.strip():

                                    st.warning(
                                        "No readable text "
                                        "was found in this "
                                        "document."
                                    )

                                else:

                                    chunk_count = (
                                        ingest_document(
                                            WORKSPACE_ID,
                                            uploaded_file.name,
                                            extracted_text,
                                        )
                                    )

                                    st.success(
                                        f"✓ {uploaded_file.name} "
                                        "processed successfully."
                                    )

                                    st.info(
                                        f"Created {chunk_count} "
                                        "document chunk(s)."
                                    )

                        except Exception as error:

                            st.error(
                                f"Could not process document: "
                                f"{error}"
                            )

    st.divider()

    st.subheader(
        "📋 Text & PDF Tools"
    )

    tool_col1, tool_col2 = st.columns(2)

    with tool_col1:

        with st.container(border=True):

            st.markdown(
                "### 📋 Paste Your Text"
            )

            tool_text = st.text_area(
                "Paste your text...",
                height=220,
                placeholder=(
                    "Paste notes, articles, "
                    "study material..."
                ),
                key="document_tool_text",
            )

            tool_text_name = st.text_input(
                "Document name",
                value="Pasted Text",
                key="document_tool_name",
            )

            if st.button(
                "➕ Add to Knowledge Base",
                key="tool_add_text",
                type="primary",
                use_container_width=True,
            ):

                if not tool_text.strip():

                    st.warning(
                        "Please paste some text first."
                    )

                else:

                    try:

                        with st.spinner(
                            "Adding text..."
                        ):

                            chunk_count = (
                                ingest_document(
                                    WORKSPACE_ID,
                                    tool_text_name.strip()
                                    or "Pasted Text",
                                    tool_text,
                                )
                            )

                        st.success(
                            "✓ Added to knowledge base."
                        )

                        st.info(
                            f"{chunk_count} chunk(s) created."
                        )

                    except Exception as error:

                        st.error(
                            f"Could not add text: "
                            f"{error}"
                        )

    with tool_col2:

        with st.container(border=True):

            st.markdown(
                "### 🔎 PDF Text Extractor"
            )

            pdf_file = st.file_uploader(
                "Choose PDF",
                type=["pdf"],
                key="pdf_text_extractor",
            )

            if pdf_file:

                if st.button(
                    "🔎 Extract Text",
                    key="extract_pdf_button",
                    use_container_width=True,
                ):

                    try:

                        with st.spinner(
                            "Extracting PDF text..."
                        ):

                            pdf_bytes = (
                                pdf_file.getvalue()
                            )

                            extracted_text = (
                                extract_document(
                                    pdf_file.name,
                                    pdf_bytes,
                                )
                            )

                        st.session_state.extracted_pdf_text = (
                            extracted_text
                        )

                        st.session_state.extracted_pdf_name = (
                            pdf_file.name
                        )

                        st.success(
                            "✓ PDF text extracted."
                        )

                    except Exception as error:

                        st.error(
                            f"Could not extract PDF: "
                            f"{error}"
                        )

            if st.session_state.extracted_pdf_text:

                st.text_area(
                    "Extracted text",
                    value=(
                        st.session_state
                        .extracted_pdf_text
                    ),
                    height=220,
                    key="pdf_extracted_display",
                )

                download_name = (
                    st.session_state
                    .extracted_pdf_name
                    .rsplit(".", 1)[0]
                    + ".txt"
                )

                st.download_button(
                    "⬇️ Download TXT",
                    data=(
                        st.session_state
                        .extracted_pdf_text
                    ),
                    file_name=download_name,
                    mime="text/plain",
                    use_container_width=True,
                )

    st.divider()

    st.subheader(
        "📚 Document Library"
    )

    documents = list_documents(
        WORKSPACE_ID
    )

    if not documents:

        st.info(
            "No documents have been added yet."
        )

    else:

        for document in documents:

            filename = document["filename"]
            chunks = document["chunks"]

            with st.container(border=True):

                col1, col2, col3 = st.columns(
                    [4, 2, 1]
                )

                with col1:

                    st.write(
                        f"📄 **{filename}**"
                    )

                with col2:

                    st.caption(
                        f"{chunks} chunks"
                    )

                with col3:

                    if st.button(
                        "Delete",
                        key=f"delete_{filename}",
                    ):

                        try:

                            deleted = delete_document(
                                WORKSPACE_ID,
                                filename,
                            )

                            st.success(
                                f"Deleted {deleted} chunks."
                            )

                            st.rerun()

                        except Exception as error:

                            st.error(
                                f"Delete failed: "
                                f"{error}"
                            )


# =========================================================
# AI CHAT
# =========================================================

elif page == "💬 AI Chat":

    st.title(
        "💬 AI Chat"
    )

    st.write(
        "Ask questions, request explanations, "
        "create notes, or control the answer format."
    )

    st.caption(
        "Examples: "
        "`Explain velocity in 200 words` • "
        "`Make 5 exam-ready points on velocity` • "
        "`Elaborate on velocity`"
    )

    st.divider()


    # =====================================================
    # CHAT HISTORY
    # =====================================================

    if not st.session_state.chat_history:

        with st.container(border=True):

            st.subheader(
                "👋 Ask your documents"
            )

            st.write(
                "DocuMind finds relevant information from "
                "your knowledge base and then uses the "
                "selected Answer Mode to construct the answer."
            )

            st.info(
                "💡 You can ask for a specific length, "
                "number of points, exam-ready notes, "
                "detailed explanations, summaries, "
                "tables, or other formats."
            )

    else:

        for message in st.session_state.chat_history:

            with st.chat_message(
                message["role"]
            ):

                st.markdown(
                    message["content"]
                )

                sources = message.get(
                    "sources",
                    [],
                )

                if sources:

                    with st.expander(
                        "📚 Sources"
                    ):

                        for source in sources:

                            st.write(
                                f"📄 "
                                f"{source['filename']} "
                                f"— chunk "
                                f"{source['chunk_index']}"
                            )


    if st.button(
        "🗑️ Clear Chat",
        key="clear_chat",
    ):

        st.session_state.chat_history = []

        st.rerun()


    # =====================================================
    # AI CONTROLS
    # =====================================================

    st.subheader(
        "🤖 AI Controls"
    )

    control_col1, control_col2 = st.columns(2)


    # =====================================================
    # AI PROVIDER
    # =====================================================

    with control_col1:

        st.markdown(
            "#### AI Provider"
        )

        st.selectbox(
            "Choose the AI provider",
            [
                PROVIDER_SMART,
                PROVIDER_LOCAL,
                PROVIDER_OPENROUTER,
            ],
            key="ai_provider",
            format_func=lambda value: (
                PROVIDER_LABELS.get(
                    value,
                    value,
                )
            ),
            help=(
                "Smart AI tries OpenRouter first and "
                "automatically falls back to local "
                "Llama 3.2 if OpenRouter is unavailable."
            ),
        )


    # =====================================================
    # ANSWER MODE
    # =====================================================

    with control_col2:

        st.markdown(
            "#### Answer Mode"
        )

        st.selectbox(
            "Choose how answers should be produced",
            [
                ANSWER_MODE_GROUNDED,
                ANSWER_MODE_ADAPTIVE,
            ],
            key="answer_mode",
            format_func=lambda value: (
                ANSWER_MODE_LABELS.get(
                    value,
                    value,
                )
            ),
            help=(
                "Grounded Mode stays strictly within the "
                "retrieved documents. Adaptive Mode uses "
                "the documents as the foundation and can "
                "add general explanations when the retrieved "
                "material is short."
            ),
        )


    # =====================================================
    # CURRENT SETTINGS DISPLAY
    # =====================================================

    provider = st.session_state.ai_provider
    answer_mode = st.session_state.answer_mode

    if provider == PROVIDER_SMART:

        st.caption(
            "⚡ **Smart AI:** OpenRouter first → "
            "Local Llama 3.2 fallback."
        )

    elif provider == PROVIDER_LOCAL:

        st.caption(
            "🖥️ **Local AI:** Uses your local "
            "Ollama `llama3.2:latest` model."
        )

    elif provider == PROVIDER_OPENROUTER:

        st.caption(
            "☁️ **OpenRouter:** Uses the configured "
            "OpenRouter free-model route."
        )


    if answer_mode == ANSWER_MODE_GROUNDED:

        st.info(
            "📚 **Grounded Mode:** Answers are restricted "
            "to information supported by your retrieved "
            "knowledge-base content."
        )

    else:

        st.info(
            "🧠 **Adaptive Mode:** Your documents remain "
            "the primary source. When the retrieved "
            "information is short, the AI may use general "
            "knowledge to explain or elaborate without "
            "inventing document-specific facts."
        )


    st.divider()


    # =====================================================
    # QUESTION INPUT
    # =====================================================

    question = st.chat_input(
        "Ask a question about your documents..."
    )

    if question:

        question = question.strip()

        if not question:
            st.stop()


        # =================================================
        # BUILD PREVIOUS CONVERSATION CONTEXT
        # =================================================

        # Do this BEFORE saving the current question so
        # the current question isn't duplicated.
        conversation_context = (
            build_conversation_context(
                st.session_state.chat_history
            )
        )


        # =================================================
        # SAVE USER QUESTION
        # =================================================

        st.session_state.chat_history.append(
            {
                "role": "user",
                "content": question,
            }
        )


        try:

            # =================================================
            # BUILD TOPIC-FOCUSED RETRIEVAL QUERY
            # =================================================

            search_query = build_retrieval_query(
                question,
                conversation_context,
            )

            if not search_query.strip():

                search_query = question


            # =================================================
            # SEARCH DOCUMENTS
            # =================================================

            with st.spinner(
                "🔎 Searching your documents..."
            ):

                results = search_documents(
                    WORKSPACE_ID,
                    search_query,
                    n_results=MAX_RESULTS,
                )


            if not isinstance(
                results,
                dict,
            ):

                results = {}


            documents_found = results.get(
                "documents",
                [],
            )

            metadatas_found = results.get(
                "metadatas",
                [],
            )


            # =================================================
            # NORMALIZE DOCUMENT RESULTS
            # =================================================

            if (
                documents_found
                and isinstance(
                    documents_found[0],
                    list,
                )
            ):

                retrieved_documents = (
                    documents_found[0]
                )

            elif isinstance(
                documents_found,
                list,
            ):

                retrieved_documents = (
                    documents_found
                )

            else:

                retrieved_documents = []


            # =================================================
            # NORMALIZE METADATA RESULTS
            # =================================================

            if (
                metadatas_found
                and isinstance(
                    metadatas_found[0],
                    list,
                )
            ):

                retrieved_metadatas = (
                    metadatas_found[0]
                )

            elif isinstance(
                metadatas_found,
                list,
            ):

                retrieved_metadatas = (
                    metadatas_found
                )

            else:

                retrieved_metadatas = []


            # =================================================
            # REMOVE EMPTY DOCUMENTS
            # =================================================

            cleaned_documents = []
            cleaned_metadatas = []

            for index, document in enumerate(
                retrieved_documents
            ):

                if not document:
                    continue

                document = str(
                    document
                ).strip()

                if not document:
                    continue

                cleaned_documents.append(
                    document
                )

                if index < len(
                    retrieved_metadatas
                ):

                    metadata = (
                        retrieved_metadatas[index]
                        or {}
                    )

                else:

                    metadata = {}

                cleaned_metadatas.append(
                    metadata
                )


            retrieved_documents = (
                cleaned_documents
            )

            retrieved_metadatas = (
                cleaned_metadatas
            )


            # =================================================
            # BUILD CONTEXT
            # =================================================

            context = ""
            sources = []


            if retrieved_documents:

                context_parts = []

                for index, document in enumerate(
                    retrieved_documents
                ):

                    metadata = {}

                    if index < len(
                        retrieved_metadatas
                    ):

                        metadata = (
                            retrieved_metadatas[index]
                            or {}
                        )

                    filename = metadata.get(
                        "filename",
                        "Unknown document",
                    )

                    chunk_index = metadata.get(
                        "chunk_index",
                        index,
                    )

                    context_parts.append(
                        f"""
SOURCE:
{filename}

CHUNK:
{chunk_index}

CONTENT:
{document}
"""
                    )


                context = "\n\n".join(
                    context_parts
                ).strip()


                # =================================================
                # LIMIT CONTEXT SIZE
                # =================================================

                if len(context) > MAX_CONTEXT_CHARS:

                    context = (
                        context[
                            :MAX_CONTEXT_CHARS
                        ]
                        + "\n\n"
                        "[Additional retrieved context "
                        "was truncated for speed.]"
                    )


                # =================================================
                # UNIQUE SOURCES
                # =================================================

                seen_sources = set()

                for metadata in (
                    retrieved_metadatas
                ):

                    if not metadata:
                        continue

                    filename = metadata.get(
                        "filename",
                        "Unknown",
                    )

                    chunk_index = metadata.get(
                        "chunk_index",
                        "?",
                    )

                    source_key = (
                        str(filename),
                        str(chunk_index),
                    )

                    if source_key in seen_sources:
                        continue

                    seen_sources.add(
                        source_key
                    )

                    sources.append(
                        {
                            "filename": filename,
                            "chunk_index": chunk_index,
                        }
                    )


            # =================================================
            # GENERATE ANSWER
            # =================================================

            provider_display = (
                PROVIDER_LABELS.get(
                    provider,
                    provider,
                )
            )

            with st.spinner(
                f"{provider_display} is generating..."
            ):

                answer = generate_answer(
                    question,
                    context,
                    conversation_context,
                    answer_mode,
                )


            # =================================================
            # COUNT QUESTION
            # =================================================

            st.session_state.questions_count += 1


            # =================================================
            # SAVE ASSISTANT ANSWER
            # =================================================

            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                }
            )


        except Exception as error:

            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": (
                        "I couldn't generate an answer "
                        "right now.\n\n"
                        f"**Error:** `{error}`"
                    ),
                    "sources": [],
                }
            )


        st.rerun()


# =========================================================
# ANALYTICS
# =========================================================

elif page == "📊 Analytics":

    st.title(
        "📊 Analytics"
    )

    st.write(
        "Overview of your DocuMind workspace."
    )

    st.divider()

    documents = list_documents(
        WORKSPACE_ID
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Documents",
            len(documents),
        )

    with col2:

        st.metric(
            "Indexed Chunks",
            get_document_count(
                WORKSPACE_ID
            ),
        )

    with col3:

        st.metric(
            "Questions",
            st.session_state.questions_count,
        )

    st.divider()

    st.subheader(
        "📄 Documents"
    )

    if documents:

        for document in documents:

            with st.container(border=True):

                st.write(
                    f"📄 **{document['filename']}**"
                )

                st.caption(
                    f"{document['chunks']} "
                    "indexed chunks"
                )

    else:

        st.info(
            "No documents available."
        )


# =========================================================
# SETTINGS
# =========================================================

elif page == "⚙️ Settings":

    st.title(
        "⚙️ Settings"
    )

    st.write(
        "DocuMind configuration and workspace information."
    )

    st.divider()


    # =====================================================
    # WORKSPACE
    # =====================================================

    st.subheader(
        "👤 Workspace"
    )

    st.write(
        f"Name: **{USER_NAME}**"
    )

    st.write(
        f"Workspace ID: `{WORKSPACE_ID}`"
    )

    st.caption(
        "Your Workspace ID is the key used to reopen "
        "this workspace. Anyone who knows it can open "
        "the workspace, so keep it private."
    )


    # =====================================================
    # AI PROVIDERS
    # =====================================================

    st.divider()

    st.subheader(
        "🤖 AI Providers"
    )

    st.info(
        "DocuMind supports Smart AI, Local AI with "
        "Llama 3.2, and OpenRouter Free."
    )

    st.write(
        f"Current provider: "
        f"**{PROVIDER_LABELS.get(provider, provider)}**"
    )

    st.write(
        f"Current answer mode: "
        f"**{ANSWER_MODE_LABELS.get(answer_mode, answer_mode)}**"
    )

    st.caption(
        "Smart AI tries OpenRouter first and "
        "falls back to local Llama 3.2 if "
        "OpenRouter is unavailable."
    )


    # =====================================================
    # LIMITS
    # =====================================================

    st.divider()

    st.subheader(
        "📦 Limits"
    )

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Maximum file size",
            f"{MAX_FILE_MB} MB",
        )

    with col2:

        st.metric(
            "Maximum files",
            MAX_FILES,
        )


    # =====================================================
    # API SECURITY
    # =====================================================

    st.divider()

    st.subheader(
        "🔐 API Security"
    )

    st.info(
        "Keep GEMINI_API_KEY and OPENROUTER_API_KEY "
        "inside Streamlit Secrets. Never commit API "
        "keys to GitHub."
    )


    # =====================================================
    # SESSION
    # =====================================================

    st.divider()

    st.subheader(
        "🚪 Session"
    )

    if st.button(
        "🚪 Logout",
        use_container_width=True,
    ):

        st.session_state.workspace_id = None
        st.session_state.logged_out = True
        st.session_state.chat_history = []
        st.session_state.questions_count = 0
        st.session_state.ai_provider = PROVIDER_SMART
        st.session_state.answer_mode = ANSWER_MODE_ADAPTIVE
        st.session_state.extracted_pdf_text = ""
        st.session_state.extracted_pdf_name = ""

        st.rerun()


    if st.button(
        "🧹 Forget this workspace on this browser",
        use_container_width=True,
    ):

        forget_workspace()

        st.session_state.workspace_id = None
        st.session_state.logged_out = True
        st.session_state.chat_history = []
        st.session_state.questions_count = 0
        st.session_state.ai_provider = PROVIDER_SMART
        st.session_state.answer_mode = ANSWER_MODE_ADAPTIVE
        st.session_state.extracted_pdf_text = ""
        st.session_state.extracted_pdf_name = ""

        st.rerun()


    # =====================================================
    # ABOUT
    # =====================================================

    st.divider()

    st.subheader(
        "ℹ️ About"
    )

    st.write(
        "**DocuMind AI**"
    )

    st.caption(
        "AI-powered document intelligence and "
        "retrieval system."
    )
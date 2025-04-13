import streamlit as st
from typing import List, Dict, Any

# ----- Chat UI Components -----

def display_chat_history(chat_history: List[Any]):
    """Display the chat history in the Streamlit UI"""
    for entry in chat_history:
        if isinstance(entry, dict):
            st.chat_message("user").markdown(entry["query"])
            st.chat_message("assistant").markdown(entry["response"])
        elif isinstance(entry, (list, tuple)) and len(entry) == 2:
            user_msg, assistant_msg = entry
            st.chat_message("user").markdown(user_msg)
            st.chat_message("assistant").markdown(assistant_msg)

def create_chat_input(placeholder: str = "Ask a question..."):
    """Create a chat input and return the user query"""
    return st.chat_input(placeholder)

def display_user_message(message: str):
    """Display a user message in the chat UI"""
    st.chat_message("user").markdown(message)

def display_assistant_message(message: str):
    """Display an assistant message in the chat UI"""
    st.chat_message("assistant").markdown(message)

# ----- Filter & Search Functionality -----

def create_filters(vectorstore):
    """Create search filters based on user selections in the sidebar"""
    # Don't show filters during questionnaires
    if st.session_state.get("questionnaire_active", False) and st.session_state.get("current_task") != "free":
        return None

    metadata, courses, semesters, lectures = get_filter_options(vectorstore)

    selected_courses = st.sidebar.multiselect("Select Courses", options=courses, default=None)

    available_lectures = []
    if selected_courses:
        for course in selected_courses:
            available_lectures.extend([m["lecture"] for m in metadata if m.get("course") == course])
        available_lectures = sorted(set(available_lectures))
    else:
        available_lectures = lectures

    selected_lectures = st.sidebar.multiselect("Select Lectures", options=available_lectures, default=None)

    filters = {}
    if selected_lectures:
        filters = {"lecture": {'$in': selected_lectures}}
    elif selected_courses:
        filters = {"course": {'$in': selected_courses}}

    return filters if filters else None

@st.cache_data
def get_filter_options(_vectorstore):
    """Get filter options from the vector store metadata"""
    metadata = _vectorstore._collection.get(include=['metadatas'])['metadatas']
    courses = sorted(set(m.get("course", "") for m in metadata if "course" in m))
    semesters = sorted(set(m.get("semester", "") for m in metadata if "semester" in m))
    lectures = sorted(set(m.get("lecture", "") for m in metadata if "lecture" in m))
    return metadata, courses, semesters, lectures

# ----- Query Processing -----

def process_query(pipeline, query: str, search_mode: str, filters: Dict[str, Any]):
    """Process a query with the pipeline and return the result"""
    try:
        result = pipeline.process_query(query, search_mode, filters)
        return result
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}

def get_response_text(result):
    """Extract response text from result object"""
    return result.content.strip() if hasattr(result, "content") else str(result)

def handle_chat_interaction(pipeline, method, vectorstore, prompt_text, task_id):
    """Handle a complete chat interaction cycle with the user"""
    st.session_state.selected_filters = create_filters(vectorstore)

    if task_id not in st.session_state.chat_history:
        st.session_state.chat_history[task_id] = []

    display_chat_history(st.session_state.chat_history[task_id])

    query = create_chat_input(prompt_text)
    if query:
        display_user_message(query)
        filters_snapshot = st.session_state.get("selected_filters")

        if not filters_snapshot or not any(filters_snapshot.values()):
            filters_snapshot = None

        flat_filters = {
            key: val["$in"] if isinstance(val, dict) and "$in" in val else val
            for key, val in (filters_snapshot or {}).items()
        }

        result = process_query(pipeline, query, method, filters_snapshot)
        response_text = get_response_text(result)
        display_assistant_message(response_text)

        st.session_state.chat_history[task_id].append({
            "query": query,
            "response": response_text,
            "filters": flat_filters
        })

        # store for logs
        st.session_state.last_query = query
        st.session_state.last_response = response_text
        st.session_state.last_task = task_id
        st.session_state.last_method = method
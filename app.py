"""
AI Quiz Platform - Main Application
Version: 1.2.0
Changelog: 
- Added localStorage username persistence (Issue 4)
- "Change User" button only visible when logged in
- Safe logout (keeps database, clears browser storage)
"""

import streamlit as st

# CRITICAL: set_page_config MUST be the first Streamlit command
st.set_page_config(
    page_title="AI Quiz Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Now import other modules after set_page_config
from config.settings import settings
from utils.auth import check_admin_authentication, logout_admin
from utils.validators import validate_username
from services.user_service import user_service

# Import localStorage library
try:
    from streamlit_js_eval import streamlit_js_eval
    LOCALSTORAGE_AVAILABLE = True
except ImportError:
    LOCALSTORAGE_AVAILABLE = False
    st.warning("⚠️ streamlit-js-eval not installed. Username persistence disabled. Install with: pip install streamlit-js-eval")

# Initialize session state
def initialize_session():
    """Initialize session state variables"""
    if 'username' not in st.session_state:
        st.session_state.username = None
        st.session_state.user_id = None
    
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if 'current_quiz_attempt' not in st.session_state:
        st.session_state.current_quiz_attempt = None
    
    if 'quiz_questions' not in st.session_state:
        st.session_state.quiz_questions = []
    
    if 'current_question_index' not in st.session_state:
        st.session_state.current_question_index = 0
    
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = {}
    
    if 'question_feedback' not in st.session_state:
        st.session_state.question_feedback = {}

    if 'skipped_questions' not in st.session_state:
        st.session_state.skipped_questions = set()
    
    # localStorage initialization flag
    if 'localstorage_checked' not in st.session_state:
        st.session_state.localstorage_checked = False

initialize_session()

# Check localStorage for username (only once per session)
if LOCALSTORAGE_AVAILABLE and not st.session_state.localstorage_checked:
    try:
        stored_username = streamlit_js_eval(js_expressions="localStorage.getItem('quiz_username')", key="get_username")
        
        if stored_username and stored_username != "null" and not st.session_state.username:
            # Auto-load username from localStorage
            user_id = user_service.get_or_create_user(stored_username)
            if user_id:
                st.session_state.username = stored_username
                st.session_state.user_id = user_id
        
        st.session_state.localstorage_checked = True
    except Exception as e:
        if settings.DEBUG_MODE:
            st.error(f"localStorage error: {str(e)}")

# Sidebar
def render_sidebar():
    """Render sidebar with navigation"""
    st.sidebar.title("🎓 " + settings.APP_NAME)
    
    # User identification
    if not st.session_state.username:
        st.sidebar.markdown("### Welcome!")
        username_input = st.sidebar.text_input("Enter your username to start")
        
        if username_input:
            is_valid, error_msg = validate_username(username_input)
            if is_valid:
                user_id = user_service.get_or_create_user(username_input)
                if user_id:
                    st.session_state.username = username_input
                    st.session_state.user_id = user_id
                    
                    # Save to localStorage
                    if LOCALSTORAGE_AVAILABLE:
                        try:
                            streamlit_js_eval(
                                js_expressions=f"localStorage.setItem('quiz_username', '{username_input}')",
                                key=f"set_username_{username_input}"
                            )
                        except Exception as e:
                            if settings.DEBUG_MODE:
                                st.sidebar.error(f"Failed to save to localStorage: {str(e)}")
                    
                    st.rerun()
                else:
                    st.sidebar.error("Failed to create/retrieve user")
            else:
                st.sidebar.error(error_msg)
        
        st.sidebar.info("💡 Enter a username (3-50 characters) to get started")
        return None
    
    else:
        st.sidebar.success(f"👤 Logged in as: **{st.session_state.username}**")
        
        # "Change User" button (only visible when logged in)
        if st.sidebar.button("👤 Change User"):
            # Clear localStorage
            if LOCALSTORAGE_AVAILABLE:
                try:
                    streamlit_js_eval(
                        js_expressions="localStorage.removeItem('quiz_username')",
                        key="clear_username"
                    )
                except Exception as e:
                    if settings.DEBUG_MODE:
                        st.sidebar.error(f"Failed to clear localStorage: {str(e)}")
            
            # Clear session state (but keep database intact)
            st.session_state.username = None
            st.session_state.user_id = None
            st.session_state.current_quiz_attempt = None
            st.session_state.localstorage_checked = False
            st.rerun()
        
        st.sidebar.markdown("---")
        
        # Navigation
        page = st.sidebar.radio(
            "Navigate",
            ["🎯 Take Quiz", "📊 My Performance", "⚙️ Admin Panel"],
            key="nav_page"
        )
        
        return page

# Main content
page = render_sidebar()

if not st.session_state.username:
    # Show welcome page
    st.title("🎓 Welcome to " + settings.APP_NAME)
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🎯 Take Quizzes")
        st.markdown("Select from various topics and difficulty levels")
    
    with col2:
        st.markdown("### 🤖 AI-Powered Feedback")
        st.markdown("Get instant explanations from 2 AI models (Claude & GPT)")
    
    with col3:
        st.markdown("### 📈 Track Progress")
        st.markdown("Monitor your improvement over time")
    
    st.markdown("---")
    st.info("👈 Enter your username in the sidebar to get started!")

elif page == "🎯 Take Quiz":
    from components.user.quiz_selector import render_quiz_selector
    from components.user.question_card import render_question_card
    from components.user.results_view import render_results_view
    
    # Check quiz state
    if st.session_state.current_quiz_attempt:
        # Quiz in progress
        if st.session_state.current_question_index < len(st.session_state.quiz_questions):
            render_question_card()
        else:
            render_results_view()
    else:
        # Quiz selection
        render_quiz_selector()

elif page == "📊 My Performance":
    from components.user.analytics_view import render_analytics_view
    render_analytics_view()

elif page == "⚙️ Admin Panel":
    # Check authentication
    if check_admin_authentication():
        st.title("⚙️ Admin Panel")
        
        # Admin navigation (inline, no logout button)
        admin_view = st.radio(
            "Admin",
            ["➕ Add Question", "📚 Manage Quizzes", "⚠️ Review Queue", "🚪 Logout"],
            horizontal=True,
            label_visibility="collapsed",
            key="admin_view"
        )
        # Reset add-question form when leaving the tab
        last_admin_view = st.session_state.get("last_admin_view")
        if last_admin_view == "➕ Add Question" and admin_view != "➕ Add Question":
            st.session_state.reset_form = True
            for key in [
                "validation_result",
                "question_data_validated",
                "form_submitted",
                "save_action",
                "final_answer",
                "final_action",
                "skip_ai_validation",
                "validation_snapshot",
                "validation_expired"
            ]:
                if key in st.session_state:
                    del st.session_state[key]
        st.session_state.last_admin_view = admin_view

        if admin_view == "➕ Add Question":
            from components.admin.question_form import render_question_form
            render_question_form()
        elif admin_view == "📚 Manage Quizzes":
            from components.admin.quiz_manager import render_quiz_manager
            render_quiz_manager()
        elif admin_view == "⚠️ Review Queue":
            from components.admin.review_queue import render_review_queue
            render_review_queue()
        else:
            logout_admin()

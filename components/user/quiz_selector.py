"""
AI Quiz Platform - Quiz Selector Component
Version: 1.0.0
"""

import streamlit as st
from services.quiz_service import quiz_service
from config.settings import settings
import uuid

def render_quiz_selector():
    """Render quiz selection interface"""
    
    st.title("🎯 Take a Quiz")
    st.markdown("Select a quiz and customize your experience")
    st.markdown("---")
    
    # Get all quizzes
    quizzes = quiz_service.get_all_quizzes()
    
    if not quizzes:
        st.warning("⚠️ No quizzes available yet. Please contact an administrator.")
        st.info("💡 Administrators can create quizzes in the Admin Panel")
        return
    
    # Quiz selection form
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Quiz dropdown
        quiz_options = {f"{q['quiz_name']} ({q['topic_domain']})": q for q in quizzes}
        selected_quiz_display = st.selectbox(
            "Select Quiz",
            list(quiz_options.keys()),
            help="Choose the quiz you want to take"
        )
        
        selected_quiz = quiz_options[selected_quiz_display]
        
        # Show quiz details
        with st.expander("📋 Quiz Details", expanded=True):
            st.markdown(f"**Topic:** {selected_quiz['topic_domain']}")
            st.markdown(f"**Level:** {selected_quiz['target_level']}")
            if selected_quiz['cert_reference']:
                st.markdown(f"**Certification:** {selected_quiz['cert_reference']}")
            
            # Get stats
            stats = quiz_service.get_quiz_stats(selected_quiz['quiz_id'])
            st.markdown(f"**Available Questions:** {stats['total']}")
            st.markdown(f"- Easy: {stats['Easy']} | Medium: {stats['Medium']} | Hard: {stats['Hard']}")
    
    with col2:
        st.markdown("### Quiz Settings")
        
        # Check if quiz has questions
        if stats['total'] == 0:
            st.error("⚠️ This quiz has no questions yet!")
            st.info("Please contact an administrator to add questions to this quiz.")
            return
        
        # Number of questions
        max_questions = min(25, stats['total'])
        available_counts = [q for q in settings.QUESTION_COUNTS if q <= max_questions]
        
        if not available_counts:
            st.error(f"Not enough questions in this quiz (only {stats['total']} available)")
            return
        
        num_questions = st.selectbox(
            "Number of Questions",
            available_counts,
            help="How many questions do you want to answer?"
        )
        
        # Difficulty
        difficulty = st.selectbox(
            "Difficulty Focus",
            settings.DIFFICULTY_LEVELS,
            index=1,  # Default to Medium
            help="Primary difficulty level (will include a mix)"
        )
        
        st.info(f"💡 Questions will be mixed:\n- 70% {difficulty}\n- 20% other levels\n- 10% remaining")
    
    st.markdown("---")
    
    # Start button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start Quiz", use_container_width=True, type="primary"):
            if stats['total'] < num_questions:
                st.error(f"Not enough questions! Quiz has only {stats['total']} questions.")
                return
            
            # Select questions
            with st.spinner("Selecting questions for you..."):
                question_ids = quiz_service.select_questions_for_attempt(
                    selected_quiz['quiz_id'],
                    num_questions,
                    difficulty,
                    st.session_state.user_id
                )
            
            if not question_ids:
                st.error("Failed to select questions. Please try again.")
                return
            
            # Create quiz attempt
            session_id = str(uuid.uuid4())
            quiz_attempt_id = quiz_service.create_quiz_attempt(
                st.session_state.user_id,
                selected_quiz['quiz_id'],
                question_ids,
                difficulty,
                session_id
            )
            
            if not quiz_attempt_id:
                st.error("Failed to create quiz attempt. Please try again.")
                return
            
            # Load questions
            questions = []
            for qid in question_ids:
                from services.question_service import question_service
                q = question_service.get_question_by_id(qid)
                if q:
                    questions.append(q)
            
            # Initialize session state
            st.session_state.current_quiz_attempt = quiz_attempt_id
            st.session_state.quiz_questions = questions
            st.session_state.current_question_index = 0
            st.session_state.user_answers = {}
            st.session_state.question_feedback = {}
            st.session_state.skipped_questions = set()
            st.session_state.quiz_metadata = {
                'quiz_name': selected_quiz['quiz_name'],
                'topic_domain': selected_quiz['topic_domain'],
                'target_level': selected_quiz['target_level'],
                'cert_reference': selected_quiz.get('cert_reference')
            }
            
            st.success("✅ Quiz started! Loading first question...")
            st.rerun()

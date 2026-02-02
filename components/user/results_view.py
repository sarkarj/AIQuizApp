"""
AI Quiz Platform - Results View Component
Version: 1.0.1
Changelog:
- Fixed score calculation (recalculate if quiz wasn't properly completed)
- Fixed duplicate question handling (deduplicate and prefer answered over skipped)
- Auto-complete quiz if status is still in_progress
"""

import streamlit as st
from services.quiz_service import quiz_service
from utils.helpers import calculate_percentage, get_performance_emoji, get_motivational_message

def render_results_view():
    """Render quiz results summary"""
    
    st.title("🏁 Quiz Complete!")
    st.markdown("---")
    
    # Safety check
    if not st.session_state.current_quiz_attempt:
        st.error("No quiz attempt found. Please start a new quiz.")
        if st.button("Go to Quiz Selection"):
            st.rerun()
        return
    
    # Get quiz attempt details
    attempt = quiz_service.get_quiz_attempt_details(st.session_state.current_quiz_attempt)
    question_attempts = quiz_service.get_attempt_question_details(st.session_state.current_quiz_attempt)
    
    if not attempt:
        st.error("Could not load quiz results")
        if st.button("Return to Quiz Selection"):
            st.session_state.current_quiz_attempt = None
            st.session_state.quiz_questions = []
            st.session_state.current_question_index = 0
            st.rerun()
        return
    
    # FIXED: If quiz wasn't completed, complete it now and recalculate score
    if attempt['status'] != 'completed':
        quiz_service.complete_quiz_attempt(st.session_state.current_quiz_attempt)
        # Reload attempt data
        attempt = quiz_service.get_quiz_attempt_details(st.session_state.current_quiz_attempt)
    
    # FIXED: Deduplicate question attempts (prefer answered over skipped, take most recent)
    question_attempts = deduplicate_question_attempts(question_attempts)
    
    # Calculate stats
    total_questions = attempt['total_questions']
    correct_count = attempt['correct_count']
    
    # FIXED: If correct_count is None or 0 but there are correct answers, recalculate
    actual_correct = sum(1 for qa in question_attempts if qa['is_correct'] and not qa['skipped'])
    if correct_count != actual_correct:
        correct_count = actual_correct
    
    percentage = calculate_percentage(correct_count, total_questions)
    emoji = get_performance_emoji(percentage)
    
    # Summary cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Score", f"{correct_count}/{total_questions}")
    
    with col2:
        st.metric("Percentage", f"{percentage}%")
    
    with col3:
        st.metric("Correct", correct_count, delta=None)
    
    with col4:
        incorrect_count = len([qa for qa in question_attempts if not qa['is_correct'] and not qa['skipped']])
        st.metric("Incorrect", incorrect_count, delta=None)
    
    # Performance message
    st.markdown(f"## {emoji} {get_motivational_message(percentage, 1)}")
    
    st.markdown("---")
    
    # Detailed results
    st.subheader("📋 Detailed Results")
    
    correct_questions = []
    incorrect_questions = []
    skipped_questions = []
    
    for qa in question_attempts:
        if qa['skipped']:
            skipped_questions.append(qa)
        elif qa['is_correct']:
            correct_questions.append(qa)
        else:
            incorrect_questions.append(qa)
    
    # Tabs for different categories
    tab1, tab2, tab3 = st.tabs([
        f"✅ Correct ({len(correct_questions)})",
        f"❌ Incorrect ({len(incorrect_questions)})",
        f"⏭️ Skipped ({len(skipped_questions)})"
    ])
    
    with tab1:
        if correct_questions:
            for qa in correct_questions:
                render_question_result(qa, "correct")
        else:
            st.info("No correct answers")
    
    with tab2:
        if incorrect_questions:
            for qa in incorrect_questions:
                render_question_result(qa, "incorrect")
        else:
            st.success("No incorrect answers!")
    
    with tab3:
        if skipped_questions:
            for qa in skipped_questions:
                render_question_result(qa, "skipped")
        else:
            st.success("No skipped questions!")
    
    st.markdown("---")
    
    # Action buttons
    col1 = st.columns(1)[0]
    
    with col1:
        if st.button("🔄 Take Another Quiz", use_container_width=True, type="primary"):
            # Clear quiz state
            st.session_state.current_quiz_attempt = None
            st.session_state.quiz_questions = []
            st.session_state.current_question_index = 0
            st.session_state.user_answers = {}
            st.session_state.question_feedback = {}
            st.rerun()
    
    # Removed View My Performance button per request

def deduplicate_question_attempts(question_attempts):
    """
    FIXED: Handle duplicate question attempts (e.g., Q12 skipped then answered)
    Strategy: Keep the most recent non-skipped attempt, or the most recent if all are skipped
    """
    # Group by question_id
    question_map = {}
    
    for qa in question_attempts:
        q_id = qa['question_id']
        
        if q_id not in question_map:
            question_map[q_id] = qa
        else:
            existing = question_map[q_id]
            
            # Prefer non-skipped over skipped
            if existing['skipped'] and not qa['skipped']:
                question_map[q_id] = qa
            # If both skipped or both answered, take most recent (by answered_at)
            elif existing['skipped'] == qa['skipped']:
                if qa['answered_at'] > existing['answered_at']:
                    question_map[q_id] = qa
    
    return list(question_map.values())

def render_question_result(qa, status):
    """Render individual question result"""
    
    with st.expander(f"{qa['question_text'][:100]}..."):
        st.markdown(f"**Question:** {qa['question_text']}")
        
        if status != "skipped":
            st.markdown("**Options:**")
            options = qa.get('options_text', '')
            correct = set((qa.get('correct_answer') or '').replace(' ', '').split(','))
            user_answer = set((qa.get('user_answer') or '').replace(' ', '').split(','))
            for line in options.split('\n'):
                line = line.strip()
                if not line:
                    continue
                letter = line[0].upper()
                if letter in correct:
                    st.success(f"✅ {line}")
                elif letter in user_answer:
                    st.error(f"❌ {line}")
                else:
                    st.markdown(line)
            
            if qa['llm_explanation']:
                st.markdown("**Explanation:**")
                st.info(qa['llm_explanation'])
            
            if qa['llm_references']:
                st.markdown("**References:**")
                for ref in qa['llm_references'].split('\n'):
                    if ref.strip():
                        st.markdown(f"- {ref}")
        else:
            st.markdown("**Options:**")
            options = qa.get('options_text', '')
            correct = set((qa.get('correct_answer') or '').replace(' ', '').split(','))
            for line in options.split('\n'):
                line = line.strip()
                if not line:
                    continue
                letter = line[0].upper()
                if letter in correct:
                    st.success(f"✅ {line}")
                else:
                    st.markdown(line)
            
            if qa['llm_explanation']:
                st.markdown("**Explanation:**")
                st.info(qa['llm_explanation'])
            
            if qa['llm_references']:
                st.markdown("**References:**")
                for ref in qa['llm_references'].split('\n'):
                    if ref.strip():
                        st.markdown(f"- {ref}")

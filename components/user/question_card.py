"""
AI Quiz Platform - Question Card Component
Version: 1.1.0
Changelog: 
- Shows both Claude and GPT explanations side-by-side
- NO LLM calls during quiz (uses pre-saved validation_data)
- Displays comprehensive explanations with why_wrong for each option
"""

import streamlit as st
import json
from utils.helpers import parse_options, check_answer_correctness
from services.quiz_service import quiz_service

def render_question_card():
    """Render current question card"""
    
    current_index = st.session_state.current_question_index
    total_questions = len(st.session_state.quiz_questions)
    
    # Safety check
    if current_index >= total_questions:
        st.error("Invalid question index. Returning to quiz selection.")
        st.session_state.current_quiz_attempt = None
        st.session_state.quiz_questions = []
        st.session_state.current_question_index = 0
        if st.button("Return to Quiz Selection"):
            st.rerun()
        return
    
    current_question = st.session_state.quiz_questions[current_index]
    
    # Rebuild skipped/answered state from DB if missing
    if not st.session_state.get("skipped_questions") and st.session_state.current_quiz_attempt:
        state = quiz_service.get_attempt_state(st.session_state.current_quiz_attempt)
        st.session_state.skipped_questions = state["skipped"]
        # Restore answered feedback keys to avoid navigation dead-ends
        for q in st.session_state.quiz_questions:
            qid = q['question_id']
            if qid in state["answered"] and qid not in st.session_state.question_feedback:
                st.session_state.question_feedback[qid] = {
                    'is_correct': False,
                    'user_answer': None,
                    'explanations': {'has_claude': False, 'has_gpt': False}
                }

    # Progress bar
    progress = (current_index + 1) / total_questions
    st.progress(progress)
    
    # Header
    st.title(f"Question {current_index + 1} of {total_questions}")
    
    st.markdown("---")
    
    # Check if already answered
    q_id = current_question['question_id']
    already_answered = q_id in st.session_state.question_feedback
    
    if already_answered:
        # Show feedback (NO LLM call, use stored data)
        render_question_feedback(current_question)
    else:
        # Show question for answering
        render_question_form(current_question)

def _find_prev_skipped_index(current_index):
    skipped = st.session_state.get("skipped_questions", set())
    for idx in range(current_index - 1, -1, -1):
        qid = st.session_state.quiz_questions[idx]['question_id']
        if qid in skipped:
            return idx
    return None

def _find_next_skipped_index(current_index):
    skipped = st.session_state.get("skipped_questions", set())
    for idx in range(current_index + 1, len(st.session_state.quiz_questions)):
        qid = st.session_state.quiz_questions[idx]['question_id']
        if qid in skipped:
            return idx
    return None

def _find_next_unanswered_index(current_index):
    skipped = st.session_state.get("skipped_questions", set())
    answered = set(st.session_state.get("question_feedback", {}).keys())
    for idx in range(current_index + 1, len(st.session_state.quiz_questions)):
        qid = st.session_state.quiz_questions[idx]['question_id']
        if qid in skipped or qid not in answered:
            return idx
    return None

def _find_next_unanswered_any_index(current_index):
    skipped = st.session_state.get("skipped_questions", set())
    answered = set(st.session_state.get("question_feedback", {}).keys())
    total = len(st.session_state.quiz_questions)
    for idx in range(current_index + 1, total):
        qid = st.session_state.quiz_questions[idx]['question_id']
        if qid in skipped or qid not in answered:
            return idx
    for idx in range(0, current_index):
        qid = st.session_state.quiz_questions[idx]['question_id']
        if qid in skipped or qid not in answered:
            return idx
    return None

def render_question_form(question):
    """Render question with answer options"""
    
    # Question text
    st.markdown(f"### {question['question_text']}")
    st.markdown("---")
    
    # Parse options
    options = parse_options(question['options_text'])
    
    # Response type
    q_id = question['question_id']
    
    if question['response_type'] == 'single':
        # Radio buttons
        st.markdown("**Select one answer:**")
        
        user_selection = st.radio(
            "Options",
            options=[f"{letter}. {text}" for letter, text in options],
            key=f"question_{q_id}",
            label_visibility="collapsed"
        )
        
        # Extract letter
        if user_selection:
            user_answer = user_selection.split('.')[0].strip()
        else:
            user_answer = None
    
    else:  # multiple
        # Checkboxes
        expected_count = question.get('expected_count', 2)
        st.info(f"ℹ️ Select exactly **{expected_count}** options")
        
        selected_options = []
        for letter, text in options:
            if st.checkbox(f"{letter}. {text}", key=f"question_{q_id}_{letter}"):
                selected_options.append(letter)
        
        user_answer = ','.join(sorted(selected_options)) if selected_options else None
        
        # Validation message
        if selected_options and len(selected_options) != expected_count:
            st.warning(f"⚠️ Please select exactly {expected_count} options (currently selected: {len(selected_options)})")
    
    st.markdown("---")
    
    # Navigation buttons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        prev_skipped = _find_prev_skipped_index(st.session_state.current_question_index)
        if prev_skipped is not None:
            if st.button("⬅️ Previous Question", use_container_width=True):
                st.session_state.current_question_index = prev_skipped
                st.rerun()
    
    with col2:
        unanswered_count = 0
        skipped = st.session_state.get("skipped_questions", set())
        answered = set(st.session_state.get("question_feedback", {}).keys())
        for q in st.session_state.quiz_questions:
            qid = q['question_id']
            if qid in skipped or qid not in answered:
                unanswered_count += 1
        if unanswered_count > 1:
            if st.button("⏭️ Skip to Next", use_container_width=True):
                # Use upsert to handle re-skipping
                save_question_attempt_upsert(
                    quiz_attempt_id=st.session_state.current_quiz_attempt,
                    question_id=q_id,
                    user_answer=None,
                    is_correct=False,
                    llm_explanation=None,
                    llm_references=None,
                    skipped=True
                )
                st.session_state.skipped_questions.add(q_id)
                next_idx = _find_next_unanswered_any_index(st.session_state.current_question_index)
                if next_idx is not None:
                    st.session_state.current_question_index = next_idx
                st.rerun()
    
    with col3:
        submit_disabled = False
        if question['response_type'] == 'multiple':
            if not user_answer or len(user_answer.split(',')) != question.get('expected_count', 2):
                submit_disabled = True
        elif not user_answer:
            submit_disabled = True
        
        if st.button("✅ Submit & Next", use_container_width=True, disabled=submit_disabled, type="primary"):
            # Process answer (NO LLM call)
            process_answer(question, user_answer)
    
    with col4:
        if st.session_state.current_question_index < len(st.session_state.quiz_questions) - 1:
            if st.button("🚪 Exit Quiz", use_container_width=True):
                if st.session_state.current_quiz_attempt:
                    quiz_service.abandon_quiz_attempt(st.session_state.current_quiz_attempt)
                st.session_state.current_question_index = len(st.session_state.quiz_questions)
                st.rerun()

def save_question_attempt_upsert(quiz_attempt_id, question_id, user_answer, is_correct, llm_explanation, llm_references, skipped):
    """Use UPSERT to handle cases where question was already attempted"""
    try:
        from database.db_manager import init_db_manager
        db = init_db_manager()
        
        db.execute_query(
            """
            INSERT INTO question_attempts (
                quiz_attempt_id, question_id, user_answer, is_correct,
                llm_explanation, llm_references, skipped
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (quiz_attempt_id, question_id) 
            DO UPDATE SET
                user_answer = EXCLUDED.user_answer,
                is_correct = EXCLUDED.is_correct,
                llm_explanation = EXCLUDED.llm_explanation,
                llm_references = EXCLUDED.llm_references,
                skipped = EXCLUDED.skipped,
                answered_at = CURRENT_TIMESTAMP
            """,
            (quiz_attempt_id, question_id, user_answer, is_correct, 
             llm_explanation, llm_references, skipped),
            fetch=False
        )
        return True
    except Exception as e:
        print(f"Error in save_question_attempt_upsert: {str(e)}")
        return False

def process_answer(question, user_answer):
    """Process user's answer WITHOUT LLM call (use stored validation_data)"""
    
    # Check correctness
    is_correct = check_answer_correctness(user_answer, question['correct_answer'])
    
    # Extract stored explanations from validation_data (NO LLM call)
    validation_data = question.get('validation_data')
    if isinstance(validation_data, str):
        validation_data = json.loads(validation_data)
    
    # Initialize LLM service to use helper method
    from services.llm_service import init_llm_service
    llm_service = init_llm_service()
    
    # Get stored explanations
    explanations = llm_service.get_stored_explanation(validation_data) if validation_data else {
        'has_claude': False,
        'has_gpt': False,
        'claude': None,
        'gpt': None
    }
    
    # Format references for storage
    all_references = []
    if explanations['has_claude'] and explanations['claude']['references']:
        all_references.extend(explanations['claude']['references'])
    if explanations['has_gpt'] and explanations['gpt']['references']:
        all_references.extend(explanations['gpt']['references'])
    
    references_text = '\n'.join(list(set(all_references))) if all_references else None
    
    # Use first available explanation for database storage
    primary_explanation = None
    if explanations['has_claude']:
        primary_explanation = explanations['claude']['explanation']
    elif explanations['has_gpt']:
        primary_explanation = explanations['gpt']['explanation']
    else:
        primary_explanation = "No explanation available."
    
    # Save to database
    save_question_attempt_upsert(
        quiz_attempt_id=st.session_state.current_quiz_attempt,
        question_id=question['question_id'],
        user_answer=user_answer,
        is_correct=is_correct,
        llm_explanation=primary_explanation,
        llm_references=references_text,
        skipped=False
    )
    
    # Store feedback in session (with BOTH explanations)
    st.session_state.question_feedback[question['question_id']] = {
        'is_correct': is_correct,
        'user_answer': user_answer,
        'explanations': explanations  # Contains both Claude and GPT
    }
    if question['question_id'] in st.session_state.skipped_questions:
        st.session_state.skipped_questions.remove(question['question_id'])
    
    st.rerun()

def render_question_feedback(question):
    """Render feedback after answer submission (shows BOTH LLM explanations)"""
    
    q_id = question['question_id']
    feedback = st.session_state.question_feedback[q_id]
    
    # Question text
    st.markdown(f"### {question['question_text']}")
    st.markdown("---")
    
    # Show options with highlighting
    options = parse_options(question['options_text'])
    correct_letters = set(question['correct_answer'].upper().replace(' ', '').split(','))
    user_letters = set(feedback['user_answer'].upper().replace(' ', '').split(','))
    
    st.markdown("**Options:**")
    for letter, text in options:
        if letter in correct_letters:
            st.success(f"✅ {letter}. {text} (Correct)")
        elif letter in user_letters:
            st.error(f"❌ {letter}. {text} (Your answer)")
        else:
            st.markdown(f"{letter}. {text}")
    
    st.markdown("---")
    
    # Result
    if feedback['is_correct']:
        st.success("🎉 **Correct!** Well done!")
    else:
        st.error("❌ **Incorrect**")
        st.info(f"**Correct answer:** {question['correct_answer']}")
    
    # BOTH LLM Explanations side-by-side
    explanations = feedback['explanations']
    
    st.markdown("### 📚 AI Explanations")
    
    if explanations['has_claude'] or explanations['has_gpt']:
        col1, col2 = st.columns(2)
        
        with col1:
            if explanations['has_claude']:
                claude = explanations['claude']
                st.markdown("#### 📘 Claude's Explanation")
                st.markdown(claude['explanation'])
                
                # Why wrong options
                if claude['why_wrong']:
                    with st.expander("Why other options are wrong"):
                        for opt, reason in claude['why_wrong'].items():
                            st.write(f"**{opt}:** {reason}")
                
                st.info(f"**💡 Key Concept:** {claude['key_concept']}")
                
                # References
                if claude['references']:
                    with st.expander("📖 References"):
                        for ref in claude['references']:
                            st.markdown(f"- {ref}")
            else:
                st.info("📘 Claude explanation not available")
        
        with col2:
            if explanations['has_gpt']:
                gpt = explanations['gpt']
                st.markdown("#### 📗 GPT's Explanation")
                st.markdown(gpt['explanation'])
                
                # Why wrong options
                if gpt['why_wrong']:
                    with st.expander("Why other options are wrong"):
                        for opt, reason in gpt['why_wrong'].items():
                            st.write(f"**{opt}:** {reason}")
                
                st.info(f"**💡 Key Concept:** {gpt['key_concept']}")
                
                # References
                if gpt['references']:
                    with st.expander("📖 References"):
                        for ref in gpt['references']:
                            st.markdown(f"- {ref}")
            else:
                st.info("📗 GPT explanation not available")
    else:
        st.warning("No AI explanations available for this question.")
    
    st.markdown("---")
    
    # Navigation
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        prev_skipped = _find_prev_skipped_index(st.session_state.current_question_index)
        if prev_skipped is not None:
            if st.button("⬅️ Previous Question", use_container_width=True):
                st.session_state.current_question_index = prev_skipped
                st.rerun()
    
    all_answered = _find_next_unanswered_any_index(st.session_state.current_question_index) is None and not st.session_state.get("skipped_questions")

    with col3:
        if not all_answered:
            next_unanswered = _find_next_unanswered_any_index(st.session_state.current_question_index)
            if st.button("➡️ Next Question", use_container_width=True, type="primary", disabled=next_unanswered is None):
                st.session_state.current_question_index = next_unanswered
                st.rerun()
    
    with col4:
        if not all_answered:
            if st.button("🚪 Exit Quiz", use_container_width=True):
                if st.session_state.current_quiz_attempt:
                    quiz_service.abandon_quiz_attempt(st.session_state.current_quiz_attempt)
                st.session_state.current_question_index = len(st.session_state.quiz_questions)
                st.rerun()
        else:
            if st.button("✅ Final Submission", use_container_width=True, type="primary"):
                quiz_service.complete_quiz_attempt(st.session_state.current_quiz_attempt)
                st.session_state.current_question_index = len(st.session_state.quiz_questions)
                st.rerun()

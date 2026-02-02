"""
AI Quiz Platform - Question Form Component
Version: 1.5.0
Changelog: 
- ENHANCEMENT: Added optional AI validation (skip GenAI calls to save costs)
- Added checkbox to skip AI validation and save directly
- Questions saved without AI validation are flagged for manual review
- FIXED: Form fields properly reset to empty/default values after save
"""

import streamlit as st
from utils.helpers import parse_options, validate_options_format, validate_correct_answer
from utils.validators import validate_question_text, validate_expected_count
from services.question_service import question_service
from config.settings import settings

def reset_validation_state():
    """Clear validation-related session state when form fields change"""
    st.session_state.validation_expired = True
    keys_to_clear = [
        'validation_result',
        'question_data_validated',
        'form_submitted',
        'save_action',
        'final_answer',
        'final_action',
        'skip_ai_validation'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def render_question_form():
    """Render add/edit question form with integrated validation"""
    
    st.subheader("➕ Add New Question")
    
    # Initialize session state for validation workflow
    if 'validation_result' not in st.session_state:
        st.session_state.validation_result = None
    if 'question_data_validated' not in st.session_state:
        st.session_state.question_data_validated = None
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    if 'skip_ai_validation' not in st.session_state:
        st.session_state.skip_ai_validation = False
    if 'validation_expired' not in st.session_state:
        st.session_state.validation_expired = False
    if 'reset_form' not in st.session_state:
        st.session_state.reset_form = False

    # Reset widget keys before widgets are created
    if st.session_state.reset_form:
        st.session_state.form_question_text = ''
        st.session_state.form_options_text = ''
        st.session_state.form_response_type = 'single'
        st.session_state.form_expected_count = 2
        st.session_state.form_correct_answer = ''
        st.session_state.form_difficulty = 'Medium'
        st.session_state.form_skip_ai = False
        st.session_state.skip_ai_checkbox = False
        st.session_state.validation_expired = False
        st.session_state.reset_form = False
    else:
        st.session_state.setdefault('form_response_type', 'single')
        st.session_state.setdefault('form_expected_count', 2)
        st.session_state.setdefault('form_difficulty', 'Medium')
        st.session_state.setdefault('form_skip_ai', False)

    # Render the single integrated form
    render_integrated_form()

def render_integrated_form():
    """Render the complete form with validation and save in single workflow"""
    
    # Check if we have validation results
    has_validation = st.session_state.validation_result is not None
    validation_expired = st.session_state.get('validation_expired', False)
    has_active_validation = has_validation and not validation_expired
    
    # Get current values or use empty defaults
    response_type_value = st.session_state.get('form_response_type', 'single')
    skip_ai_value = st.session_state.get('form_skip_ai', False)
    
    # Fields layout (left: question/options, right: response details)
    left, right = st.columns([2, 1])
    with left:
        question_text = st.text_area(
            "Question *",
            key="form_question_text",
            height=140,
            placeholder="Enter your question here...",
            help="The main question text"
        )
        options_text = st.text_area(
            "Options *",
            key="form_options_text",
            height=190,
            placeholder="A. First option\\nB. Second option\\nC. Third option\\nD. Fourth option",
            help="Enter options in format: A. Option text (one per line). Can have 2-6 options."
        )
    with right:
        response_type = st.selectbox(
            "Response Type *",
            ["single", "multiple"],
            key="form_response_type",
            format_func=lambda x: "Single Choice (Radio Button)" if x == "single" else "Multiple Choice (Checkboxes)"
        )
        expected_count = None
        if response_type == "multiple":
            expected_count = st.number_input(
                "Expected Selections *",
                min_value=2,
                max_value=6,
                value=st.session_state.get('form_expected_count', 2),
                key="form_expected_count",
                help="How many options should the user select?"
            )
        correct_answer = st.text_input(
            "Correct Answer" + (" *" if skip_ai_value else " (Optional)"),
            key="form_correct_answer",
            placeholder="A (for single) or A,C,D (for multiple)" + ("" if skip_ai_value else " - Leave empty to let AI determine"),
            help="REQUIRED if skipping AI validation. Otherwise, leave empty to let AI determine the correct answer."
        )
        difficulty = st.selectbox(
            "Difficulty *",
            settings.DIFFICULTY_LEVELS,
            key="form_difficulty"
        )

    # Skip AI Validation checkbox (between form and panel)
    skip_ai = st.checkbox(
        "⚡ Skip AI Validation (Save directly without LLM check)",
        value=skip_ai_value,
        help="Enable this to save questions immediately without AI validation. Use when you're confident about your answer or want to save GenAI costs.",
        key="skip_ai_checkbox"
    )
    if skip_ai != skip_ai_value:
        st.session_state.form_skip_ai = skip_ai
        reset_validation_state()
        st.rerun()
    if skip_ai:
        st.markdown("AI validation skipped. Correct Answer required (will save & flag for review).")

    # Show Validation & Actions only after user starts entering data or checks skip_ai
    has_any_input = any([
        bool(question_text.strip()),
        bool(options_text.strip()),
        bool(correct_answer.strip()),
        response_type == "multiple" and bool(expected_count),
        skip_ai
    ])


    col1, col2 = st.columns(2)
    with col1:
        validate_enabled = (not skip_ai) and (not has_validation or validation_expired)
        validate_clicked = st.button(
            "🤖 Validate with AI",
            use_container_width=True,
            type="primary",
            disabled=not validate_enabled
        )
    with col2:
        save_clicked = st.button(
            "💾 Save Question (No AI Check)",
            use_container_width=True,
            type="primary" if skip_ai else "secondary",
            disabled=not skip_ai
        )

    if validate_clicked:
        st.session_state.revalidating = False
        handle_validation(
            question_text,
            options_text,
            response_type,
            correct_answer,
            expected_count,
            difficulty,
            False
        )
    elif save_clicked and skip_ai:
        handle_validation(
            question_text,
            options_text,
            response_type,
            correct_answer,
            expected_count,
            difficulty,
            True
        )
    
    # Detect changes after submit and expire validation if inputs differ
    if has_validation and not st.session_state.get("revalidating"):
        snapshot = st.session_state.get('validation_snapshot', {}) or {}
        current_response_type = st.session_state.get('form_response_type', 'single')
        current = {
            'question_text': st.session_state.get('form_question_text', ''),
            'options_text': st.session_state.get('form_options_text', ''),
            'response_type': current_response_type,
            'correct_answer': st.session_state.get('form_correct_answer', '').upper().replace(' ', ''),
            'expected_count': st.session_state.get('form_expected_count') if current_response_type == 'multiple' else None,
            'difficulty': st.session_state.get('form_difficulty', 'Medium')
        }
        if snapshot and any(snapshot.get(k) != current.get(k) for k in current.keys()):
            st.session_state.validation_expired = True

    # Show validation results if available (outside form)
    if has_validation:
        render_validation_results()

    # After a save, clear inputs and reset skip AI checkbox
    if st.session_state.get("reset_form"):
        st.rerun()

def create_manual_validation_result(question_data):
    """
    Create a mock validation result when AI validation is skipped
    This allows the question to be saved with the manual answer
    """
    return {
        'all_agree': False,  # Not AI validated
        'claude': {
            'success': False,
            'model': 'claude',
            'data': {},
            'error': 'AI validation skipped by user'
        },
        'gpt': {
            'success': False,
            'model': 'gpt',
            'data': {},
            'error': 'AI validation skipped by user'
        },
        'agreement_count': 0,
        'consensus_answer': question_data.get('correct_answer', ''),
        'manual_entry': True,  # Flag to indicate this was manually entered
        'skipped_ai': True
    }

def handle_validation(question_text, options_text, response_type, correct_answer, expected_count, difficulty, skip_ai=False):
    """Handle validation logic when user clicks Validate button"""
    
    # Validation
    errors = []
    
    # Validate question text
    is_valid, error_msg = validate_question_text(question_text)
    if not is_valid:
        errors.append(f"Question: {error_msg}")
    
    # Validate options
    is_valid, error_msg = validate_options_format(options_text)
    if not is_valid:
        errors.append(f"Options: {error_msg}")
    else:
        options = parse_options(options_text)
        
        # Validate correct answer - REQUIRED if skipping AI
        if skip_ai:
            if not correct_answer or not correct_answer.strip():
                errors.append("Correct Answer: REQUIRED when skipping AI validation")
            elif correct_answer and correct_answer.strip():
                if response_type == 'multiple':
                    # Enforce expected count match for manual entries (single error message)
                    if expected_count is None:
                        errors.append("Correct Answer: Must select exactly the expected number of option(s)")
                    else:
                        answers = [a.strip().upper() for a in correct_answer.split(',') if a.strip()]
                        if len(set(answers)) != len(answers):
                            errors.append(f"Correct Answer: Must select exactly {expected_count} option(s)")
                        elif len(answers) != expected_count:
                            errors.append(f"Correct Answer: Must select exactly {expected_count} option(s)")
                        else:
                            is_valid, error_msg = validate_correct_answer(correct_answer, options, response_type)
                            if not is_valid:
                                errors.append(f"Correct Answer: {error_msg}")
                else:
                    is_valid, error_msg = validate_correct_answer(correct_answer, options, response_type)
                    if not is_valid:
                        errors.append(f"Correct Answer: {error_msg}")
        else:
            # Optional if using AI
            if correct_answer and correct_answer.strip():
                is_valid, error_msg = validate_correct_answer(correct_answer, options, response_type)
                if not is_valid:
                    errors.append(f"Correct Answer: {error_msg}")
        
        # Validate expected count for multiple choice
        if response_type == 'multiple' and expected_count:
            is_valid, error_msg = validate_expected_count(expected_count, len(options))
            if not is_valid and "trivial" not in error_msg:
                errors.append(f"Expected Count: {error_msg}")
    
    # Show validation errors
    if errors:
        for error in errors:
            st.error(error)
        return
    
    # Prepare question data
    question_data = {
        'question_text': question_text,
        'options_text': options_text,
        'response_type': response_type,
        'correct_answer': correct_answer.upper().replace(' ', '') if correct_answer else '',
        'expected_count': expected_count,
        'difficulty': difficulty
    }
    
    # ENHANCEMENT: Skip AI validation if checkbox is checked
    if skip_ai:
        # Create manual validation result
        validation_result = create_manual_validation_result(question_data)
        
        # Store validation result in session state
        st.session_state.validation_result = validation_result
        st.session_state.question_data_validated = question_data
        st.session_state.validation_snapshot = {
            'question_text': question_data['question_text'],
            'options_text': question_data['options_text'],
            'response_type': question_data['response_type'],
            'correct_answer': question_data['correct_answer'],
            'expected_count': question_data.get('expected_count'),
            'difficulty': question_data['difficulty']
        }
        st.session_state.form_submitted = True
        st.session_state.skip_ai_validation = True
        st.session_state.validation_expired = False
        st.session_state.validation_token = st.session_state.get('validation_token', 0) + 1
        st.session_state.revalidating = False
        st.session_state.final_answer = question_data['correct_answer']
        st.session_state.final_action = "flag"  # Always flag manual entries
        handle_save()
        return
        
    # LLM Validation (PARALLEL execution)
    st.info("🤖 Validating with AI models (Claude & GPT via Bedrock) in parallel...")
    
    try:
        # Initialize LLM service
        from services.llm_service import init_llm_service
        llm_service = init_llm_service()
        
        with st.spinner("Consulting both AI models simultaneously..."):
            validation_result = llm_service.validate_question(question_data)
        
        # Store validation result in session state
        st.session_state.validation_result = validation_result
        st.session_state.question_data_validated = question_data
        st.session_state.validation_snapshot = {
            'question_text': question_data['question_text'],
            'options_text': question_data['options_text'],
            'response_type': question_data['response_type'],
            'correct_answer': question_data['correct_answer'],
            'expected_count': question_data.get('expected_count'),
            'difficulty': question_data['difficulty']
        }
        st.session_state.form_submitted = True
        st.session_state.skip_ai_validation = False
        st.session_state.validation_expired = False
        st.session_state.validation_token = st.session_state.get('validation_token', 0) + 1
        st.session_state.revalidating = False
        
        st.success("✅ Validation complete! Review results below.")
        st.rerun()
        
    except Exception as e:
        st.error(f"Error during validation: {str(e)}")
        if settings.DEBUG_MODE:
            st.exception(e)

def render_validation_results():
    """Render validation results and action selection"""
    
    validation_result = st.session_state.get('validation_result')
    question_data = st.session_state.get('question_data_validated')
    skip_ai = st.session_state.get('skip_ai_validation', False)
    if not validation_result or not question_data:
        return
    
    # If AI was skipped, no extra UI needed
    if skip_ai or validation_result.get('manual_entry', False):
        return
    
    # Regular AI validation results display
    st.subheader("🤖 AI Validation Results")
    
    claude_data = validation_result.get('claude', {}).get('data', {}) if validation_result.get('claude', {}).get('success') else {}
    gpt_data = validation_result.get('gpt', {}).get('data', {}) if validation_result.get('gpt', {}).get('success') else {}
    claude_ans = claude_data.get('your_answer', 'N/A')
    gpt_ans = gpt_data.get('your_answer', 'N/A')
    agreement_count = validation_result['agreement_count']
    consensus_answer = validation_result['consensus_answer']
    stored_answer = question_data.get('correct_answer', '')
    
    # Display LLM results side by side (always)
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📘 Claude 3 Sonnet**")
        if validation_result['claude']['success']:
            st.write(f"**Answer:** {claude_ans}")
            st.write(f"**Confidence:** {claude_data.get('confidence', 'N/A')}")
            with st.expander("Claude Explanation", expanded=False):
                st.write(f"**Why Correct:** {claude_data.get('explanation', 'No explanation')}")
                if claude_data.get('why_wrong'):
                    st.write("**Why Wrong Options:**")
                    for opt, reason in claude_data.get('why_wrong', {}).items():
                        st.write(f"• {opt}: {reason}")
                st.write(f"**Key Concept:** {claude_data.get('key_concept', 'N/A')}")
                if claude_data.get('references'):
                    st.write("**References:**")
                    for ref in claude_data.get('references', []):
                        st.write(f"• {ref}")
        else:
            st.error(f"Claude Error: {validation_result['claude'].get('error', 'Unknown error')}")
    
    with col2:
        st.markdown("**📗 GPT (Bedrock)**")
        if validation_result['gpt']['success']:
            st.write(f"**Answer:** {gpt_ans}")
            st.write(f"**Confidence:** {gpt_data.get('confidence', 'N/A')}")
            with st.expander("GPT Explanation", expanded=False):
                st.write(f"**Why Correct:** {gpt_data.get('explanation', 'No explanation')}")
                if gpt_data.get('why_wrong'):
                    st.write("**Why Wrong Options:**")
                    for opt, reason in gpt_data.get('why_wrong', {}).items():
                        st.write(f"• {opt}: {reason}")
                st.write(f"**Key Concept:** {gpt_data.get('key_concept', 'N/A')}")
                if gpt_data.get('references'):
                    st.write("**References:**")
                    for ref in gpt_data.get('references', []):
                        st.write(f"• {ref}")
        else:
            st.error(f"GPT Error: {validation_result['gpt'].get('error', 'Unknown error')}")
    
    st.markdown("---")
    
    # Mismatch flow
    if agreement_count < 2:
        st.markdown("⚠️ Models disagree.")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if claude_ans and claude_ans != 'N/A' and st.button(f"Save Claude Answer ({claude_ans})", type="secondary", use_container_width=True):
                st.session_state.final_answer = claude_ans
                st.session_state.final_action = "accept"
                handle_save()
        with col2:
            if gpt_ans and gpt_ans != 'N/A' and st.button(f"Save GPT Answer ({gpt_ans})", type="secondary", use_container_width=True):
                st.session_state.final_answer = gpt_ans
                st.session_state.final_action = "accept"
                handle_save()
        with col3:
            if st.button("Save & Flag for Review", type="secondary", use_container_width=True):
                st.session_state.final_answer = stored_answer if stored_answer else consensus_answer
                st.session_state.final_action = "flag"
                handle_save()
        return
    
    # Agreement flow
    st.success(f"✅ Models agree. Answer: {consensus_answer}")
    if st.button("💾 Save Question", type="primary"):
        st.session_state.final_answer = consensus_answer
        st.session_state.final_action = "accept"
        handle_save()

def handle_save():
    """Handle save logic when user clicks Save button"""
    
    validation_result = st.session_state.validation_result
    question_data = st.session_state.question_data_validated
    action = st.session_state.get('final_action', 'flag')
    final_answer = st.session_state.get('final_answer', '')
    skip_ai = st.session_state.get('skip_ai_validation', False)
    
    # Prepare final question data
    final_question_data = question_data.copy()
    final_question_data['correct_answer'] = final_answer
    
    # Set flags based on action and whether AI was skipped
    if skip_ai or validation_result.get('manual_entry', False):
        # Manual entry - always flag for review
        llm_validated = False
        llm_conflict = True
    elif action == "accept":
        llm_validated = True
        llm_conflict = False
    else:  # flag
        llm_validated = False
        llm_conflict = True
    
    # Override validation result flags
    validation_result_copy = validation_result.copy()
    validation_result_copy['all_agree'] = llm_validated
    
    try:
        question_id = question_service.create_question(final_question_data, validation_result_copy)
        
        if question_id:
            # Show success message
            if skip_ai or validation_result.get('manual_entry', False):
                st.success(f"✅ **Question saved successfully!** (ID: {question_id})")
                st.info("ℹ️ Question saved but flagged for review (manual entry without AI validation). Check 'Review Queue' to review and unflag.")
            elif action == "accept":
                st.success(f"✅ **Question saved successfully!** (ID: {question_id})")
                st.success("✅ Question is now available for quizzes!")
            else:
                st.success(f"✅ **Question saved with flag!** (ID: {question_id})")
                st.info("ℹ️ Question saved but flagged for review. Check 'Review Queue' to review and unflag.")
            
            # FIXED: Clear form state completely
            clear_form_state()
            st.session_state.validation_expired = False
            
            # Wait briefly to show success message, then rerun
            import time
            time.sleep(2)
            st.rerun()
        else:
            st.error("❌ Failed to save question. Please try again.")
    
    except Exception as e:
        st.error(f"❌ Error saving question: {str(e)}")
        if settings.DEBUG_MODE:
            st.exception(e)

def clear_form_state():
    """FIXED: Clear all form-related session state and reset to defaults"""
    keys_to_clear = [
        'validation_result',
        'question_data_validated',
        'form_submitted',
        'save_action',
        'final_answer',
        'final_action',
        'skip_ai_validation'
    ]
    
    # Delete all keys
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    # Reset form fields on next render (cannot mutate widget keys after instantiation)
    st.session_state.reset_form = True

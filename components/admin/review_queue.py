"""
AI Quiz Platform - Review Queue Component
Version: 1.2.2
Changelog: 
- FIXED: Question text now uses normal font (not H3 header)
- FIXED: Options display with proper line breaks (one per line)
- Consistent formatting with Manage Quizzes page
"""

import streamlit as st
import json
from services.question_service import question_service

def render_review_queue():
    """Render flagged questions review interface"""
    
    st.subheader("⚠️ Review Queue - Flagged Questions")
    st.markdown("Questions where AI models disagreed during validation or were manually flagged")
    
    # Get flagged questions (server-side filtered)
    flagged_questions = []
    total_filtered = 0
    
    # Filters (single horizontal line; search below if crowded)
    st.markdown("---")
    st.markdown("#### Filters")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        difficulty_filter = st.selectbox("Difficulty", ["All", "Easy", "Medium", "Hard"])
    with col2:
        response_filter = st.selectbox("Response Type", ["All", "single", "multiple"])
    with col3:
        manual_filter = st.selectbox("Validation Type", ["All", "Manual (Skipped AI)", "AI Disagreement/Error"])
    with col4:
        sort_by = st.selectbox(
            "Sort",
            ["newest", "oldest", "id_desc", "id_asc"],
            format_func=lambda x: {
                "newest": "Newest",
                "oldest": "Oldest",
                "id_desc": "ID (High → Low)",
                "id_asc": "ID (Low → High)"
            }[x]
        )
    with col5:
        page_size = st.selectbox("Page size", [5, 10, 20, 50], index=1)
    with col6:
        page_number = st.number_input("Page", min_value=1, value=st.session_state.get("review_page", 1), key="review_page")
    
    search_term = st.text_input("Search", placeholder="Search question text or options...")

    def detect_manual_entry(validation_data):
        has_skip_flag = validation_data.get('skipped_ai') or validation_data.get('manual_entry')
        has_skip_error = (
            validation_data.get('claude', {}).get('error') == 'AI validation skipped by user' or
            validation_data.get('gpt', {}).get('error') == 'AI validation skipped by user'
        )
        return bool(has_skip_flag or has_skip_error)

    result = question_service.get_flagged_questions_filtered(
        difficulty=difficulty_filter,
        response_type=response_filter,
        manual_filter=manual_filter,
        search_term=search_term,
        page=page_number,
        page_size=page_size,
        sort_by=sort_by
    )
    flagged_questions = result.get("items", [])
    total_filtered = result.get("total", 0)

    if total_filtered == 0:
        st.success("✅ No flagged questions! All questions have been reviewed or have AI agreement.")
        return

    total_pages = max((total_filtered + page_size - 1) // page_size, 1)
    if page_number > total_pages:
        page_number = total_pages
    
    start = (page_number - 1) * page_size
    end = start + page_size
    st.warning(f"Found {total_filtered} question(s) needing review")
    st.info("💡 **Note:** Flagged questions are saved in the database but **NOT available** in quizzes until you review and unflag them.")
    st.caption(f"Showing {start + 1}-{min(end, total_filtered)} of {total_filtered} flagged questions")
    
    for q in flagged_questions:
        with st.expander(f"Question ID: {q['question_id']} - {q['question_text'][:80]}..."):
            # FIXED: Remove large header formatting, use normal text with bold label
            st.markdown(f"**Question ID:** {q['question_id']}")
            st.markdown(f"**Question:** {q['question_text']}")
            
            # FIXED: Display options with proper line breaks
            st.markdown("**Options:**")
            # Ensure each option is on a new line
            options_lines = q['options_text'].strip().split('\n')
            for line in options_lines:
                if line.strip():  # Skip empty lines
                    st.markdown(line)
            
            stored_answer = (q.get('correct_answer') or "").strip().upper()
            st.markdown(f"**Difficulty:** {q['difficulty']}")
            st.markdown(f"**Response Type:** {q['response_type']}")
            
            # Show validation data
            validation_data = {}
            is_manual = False
            
            if q['validation_data']:
                try:
                    validation_data = json.loads(q['validation_data']) if isinstance(q['validation_data'], str) else q['validation_data']
                    
                    # Robust detection of manual entry
                    is_manual = detect_manual_entry(validation_data)
                except Exception as e:
                    st.error(f"Error parsing validation data: {str(e)}")
                    validation_data = {}
                    is_manual = False
                
            # Correct Answer editor + actions
            st.markdown("---")
            options_lines = q['options_text'].strip().split('\n')
            option_letters = []
            for line in options_lines:
                line = line.strip()
                if not line:
                    continue
                letter = line[0].upper()
                if letter.isalpha() and letter not in option_letters:
                    option_letters.append(letter)
            if not option_letters:
                option_letters = ["A", "B", "C", "D", "E", "F"]

            row_col1, row_col2, row_col3 = st.columns([6, 2, 2])
            with row_col1:
                if q['response_type'] == "multiple":
                    selected_defaults = [s.strip().upper() for s in stored_answer.split(",") if s.strip()]
                    selected_defaults = [s for s in selected_defaults if s in option_letters]
                    chosen_answers = st.multiselect(
                        "Correct Answer",
                        options=option_letters,
                        default=selected_defaults,
                        key=f"correct_multi_{q['question_id']}"
                    )
                    updated_answer = ",".join(chosen_answers)
                else:
                    selected_default = stored_answer if stored_answer in option_letters else option_letters[0]
                    updated_answer = st.selectbox(
                        "Correct Answer",
                        options=option_letters,
                        index=option_letters.index(selected_default),
                        key=f"correct_single_{q['question_id']}"
                    )

            with row_col2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("✅ Unflag", key=f"unflag_{q['question_id']}", use_container_width=True, type="primary"):
                    if question_service.unflag_question(q['question_id'], updated_answer):
                        st.success("✅ Question unflagged and updated.")
                        st.rerun()
                    else:
                        st.error("❌ Failed to unflag question")

            with row_col3:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️ Delete", key=f"delete_{q['question_id']}", use_container_width=True):
                    if question_service.delete_question(q['question_id']):
                        st.success("Question deleted!")
                        st.rerun()

            # AI Model Responses (only for AI disagreement/errors)
            if validation_data and not is_manual:
                st.markdown("---")
                st.markdown("#### 🤖 AI Model Responses")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**📘 Claude 3 Sonnet**")
                    if validation_data.get('claude', {}).get('success'):
                        data = validation_data['claude']['data']
                        claude_answer = data.get('your_answer', 'N/A')
                        st.write(f"**Answer:** {claude_answer}")
                        st.write(f"**Confidence:** {data.get('confidence', 'N/A')}")
                        with st.expander("View Full Explanation"):
                            st.write(f"**Why Correct:** {data.get('explanation', 'No explanation')}")
                            if data.get('key_concept'):
                                st.info(f"**Key Concept:** {data['key_concept']}")
                    else:
                        st.error(f"Error: {validation_data.get('claude', {}).get('error', 'Unknown error')}")
                with col2:
                    st.markdown("**📗 GPT (Bedrock)**")
                    if validation_data.get('gpt', {}).get('success'):
                        data = validation_data['gpt']['data']
                        gpt_answer = data.get('your_answer', 'N/A')
                        st.write(f"**Answer:** {gpt_answer}")
                        st.write(f"**Confidence:** {data.get('confidence', 'N/A')}")
                        with st.expander("View Full Explanation"):
                            st.write(f"**Why Correct:** {data.get('explanation', 'No explanation')}")
                            if data.get('key_concept'):
                                st.info(f"**Key Concept:** {data['key_concept']}")
                    else:
                        st.error(f"Error: {validation_data.get('gpt', {}).get('error', 'Unknown error')}")

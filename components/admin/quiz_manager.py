"""
AI Quiz Platform - Quiz Manager Component
Version: 1.2.0
Changelog: 
- FIXED: Changed checkboxes to radio buttons for Add/Delete actions
- Better UX: Only one action selectable per question
- Clearer UI with single action button based on selection
"""

import uuid
import streamlit as st
from services.quiz_service import quiz_service
from services.question_service import question_service
from utils.validators import validate_quiz_name
from utils.helpers import parse_options
from config.settings import settings

def render_quiz_manager():
    """Render quiz creation and management interface"""
    
    st.subheader("📚 Quiz Manager")
    
    tab1, tab2, tab3 = st.tabs(["Create New Quiz", "Manage Existing Quizzes", "Delete Quiz"])
    
    with tab1:
        render_create_quiz_form()
    
    with tab2:
        render_manage_quizzes()
    
    with tab3:
        render_delete_quiz()

def render_create_quiz_form():
    """Render create quiz form"""
    
    st.markdown("### Create New Quiz")

    if "create_quiz_form_nonce" not in st.session_state:
        st.session_state.create_quiz_form_nonce = uuid.uuid4().hex

    form_nonce = st.session_state.create_quiz_form_nonce

    if st.session_state.get("create_quiz_success"):
        quiz_id = st.session_state.get("create_quiz_success_id")
        st.success(f"✅ Quiz created successfully! (ID: {quiz_id})")
        st.session_state.pop("create_quiz_success", None)
        st.session_state.pop("create_quiz_success_id", None)

    with st.form(f"create_quiz_form_{form_nonce}"):
        quiz_name = st.text_input(
            "Quiz Name *",
            key=f"create_quiz_name_{form_nonce}",
            value="",
            placeholder="e.g., AWS Solutions Architect Practice",
            help="Unique name for the quiz"
        )
        
        topic_domain = st.text_input(
            "Topic/Domain *",
            key=f"create_quiz_topic_{form_nonce}",
            value="",
            placeholder="e.g., AWS Solutions Architect",
            help="Subject area for LLM context"
        )
        
        target_level = st.selectbox(
            "Target Level *",
            settings.TARGET_LEVELS,
            key=f"create_quiz_target_{form_nonce}",
            index=0,
            help="Skill level for this quiz"
        )
        
        cert_reference = st.text_input(
            "Certification Reference (Optional)",
            key=f"create_quiz_cert_{form_nonce}",
            value="",
            placeholder="e.g., AWS SAA-C03",
            help="Certification or exam reference for LLM context"
        )
        
        submitted = st.form_submit_button("Create Quiz", use_container_width=True)
        
        if submitted:
            # Validate
            is_valid, error_msg = validate_quiz_name(quiz_name)
            if not is_valid:
                st.error(error_msg)
                return
            
            if not topic_domain or len(topic_domain.strip()) < 3:
                st.error("Topic/Domain must be at least 3 characters")
                return
            
            # Create quiz
            quiz_data = {
                'quiz_name': quiz_name.strip(),
                'topic_domain': topic_domain.strip(),
                'target_level': target_level,
                'cert_reference': cert_reference.strip() if cert_reference else None
            }
            
            quiz_id = quiz_service.create_quiz(quiz_data)
            
            if quiz_id:
                st.session_state.create_quiz_success = True
                st.session_state.create_quiz_success_id = quiz_id
                st.session_state.create_quiz_form_nonce = uuid.uuid4().hex
                st.rerun()
            else:
                st.error("Failed to create quiz. Quiz name might already exist.")

def render_manage_quizzes():
    """Render quiz management interface"""
    
    st.markdown("### Manage Existing Quizzes")
    
    # Get all quizzes
    quizzes = quiz_service.get_all_quizzes()
    
    if not quizzes:
        st.info("No quizzes created yet. Create one in the 'Create New Quiz' tab.")
        return
    
    # Quiz selector + summary in two columns
    quiz_options = {q['quiz_name']: q['quiz_id'] for q in quizzes}
    top_left, top_right = st.columns([2, 3])
    with top_left:
        selected_quiz_name = st.selectbox("Select Quiz", list(quiz_options.keys()))
    selected_quiz_id = quiz_options[selected_quiz_name]
    
    # Get quiz details
    quiz = quiz_service.get_quiz_by_id(selected_quiz_id)
    stats = quiz_service.get_quiz_stats(selected_quiz_id)
    
    # Display quiz info (right column)
    with top_right:
        st.markdown("#### Quiz Information")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total", stats['total'])
        col2.metric("Easy", stats['Easy'])
        col3.metric("Medium", stats['Medium'])
        col4.metric("Hard", stats['Hard'])
        
        meta = f"Topic: {quiz['topic_domain']} • Level: {quiz['target_level']}"
        if quiz['cert_reference']:
            meta += f" • Certification: {quiz['cert_reference']}"
        st.markdown(meta)
    
    st.markdown("---")
    
    # Tag questions section
    st.markdown("#### Tag Questions to Quiz")
    
    # Get all questions (non-flagged only)
    all_questions = [q for q in question_service.get_all_questions() if not q.get('llm_conflict')]
    quiz_questions = quiz_service.get_quiz_questions(selected_quiz_id)
    quiz_question_ids = {q['question_id'] for q in quiz_questions}
    
    # Filter options
    # Filters like Review Queue
    st.markdown("#### Filters")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        filter_difficulty = st.selectbox("Difficulty", ["All"] + settings.DIFFICULTY_LEVELS)
    with col2:
        filter_response = st.selectbox("Response Type", ["All", "single", "multiple"])
    with col3:
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
    with col4:
        page_size = st.selectbox("Page size", [5, 10, 20, 50], index=1)
    with col5:
        page_number = st.number_input("Page", min_value=1, value=st.session_state.get("quiz_manage_page", 1), key="quiz_manage_page")
    with col6:
        st.markdown("")
    
    search_term = st.text_input("Search", placeholder="Search question text or options...")
    
    # Filter questions
    questions_list = list(all_questions)
    
    if filter_difficulty != "All":
        questions_list = [q for q in questions_list if q['difficulty'] == filter_difficulty]
    if filter_response != "All":
        questions_list = [q for q in questions_list if q['response_type'] == filter_response]
    
    if search_term:
        search_lower = search_term.lower()
        questions_list = [
            q for q in questions_list 
            if search_lower in q['question_text'].lower() or search_lower in q['options_text'].lower()
        ]

    # Sort
    if sort_by == "newest":
        questions_list = sorted(questions_list, key=lambda x: x.get("created_at") or 0, reverse=True)
    elif sort_by == "oldest":
        questions_list = sorted(questions_list, key=lambda x: x.get("created_at") or 0)
    elif sort_by == "id_desc":
        questions_list = sorted(questions_list, key=lambda x: x.get("question_id", 0), reverse=True)
    elif sort_by == "id_asc":
        questions_list = sorted(questions_list, key=lambda x: x.get("question_id", 0))
    
    # Map question_id -> list of quiz names (bulk)
    tagged_by_question = {}
    for row in quiz_service.get_question_tags():
        tagged_by_question.setdefault(row["question_id"], set()).add(row["quiz_name"])

    # Unified questions list
    if questions_list:
        total = len(questions_list)
        total_pages = max((total + page_size - 1) // page_size, 1)
        if page_number > total_pages:
            page_number = total_pages

        start = (page_number - 1) * page_size
        end = start + page_size
        page_questions = questions_list[start:end]
        st.caption(f"Showing {start + 1}-{min(end, total)} of {total} questions")

        for q in page_questions:
            tagged = sorted(tagged_by_question.get(q['question_id'], []))
            tag_inline = ""
            if tagged:
                tag_text = ", ".join(tagged)
                if len(tag_text) > 40:
                    tag_text = tag_text[:37].rstrip() + "..."
                tag_inline = f" ({tag_text})"
            header_text = f"[{q['difficulty']}] {q['question_text'][:100]}...{tag_inline}"
            with st.expander(header_text):
                st.markdown(f"**Question ID:** {q['question_id']} | **Difficulty:** {q['difficulty']} | **Type:** {q['response_type']}")
                
                st.markdown(f"**Question:** {q['question_text']}")
                correct_letters = set([c.strip() for c in q['correct_answer'].upper().replace(' ', '').split(',') if c.strip()])
                options_inline = []
                for letter, text in parse_options(q['options_text']):
                    label = f"{letter}. {text}"
                    if letter in correct_letters:
                        options_inline.append(f"✅ {label}")
                    else:
                        options_inline.append(label)
                st.markdown("**Options:** " + ", ".join(options_inline))

                if tagged:
                    st.markdown("**Tagged:** " + ", ".join(tagged))
                else:
                    st.markdown("**Tagged:** (none)")
                
                current_tags = tagged_by_question.get(q['question_id'], set())
                tag_key = f"tag_quiz_{q['question_id']}"
                if tag_key in st.session_state:
                    selected_tags = st.multiselect(
                        "Tag to Quiz",
                        list(quiz_options.keys()),
                        key=tag_key
                    )
                else:
                    selected_tags = st.multiselect(
                        "Tag to Quiz",
                        list(quiz_options.keys()),
                        default=sorted(current_tags),
                        key=tag_key
                    )
                new_tags = set(selected_tags)
                if new_tags != set(current_tags):
                    to_add = new_tags - current_tags
                    to_remove = current_tags - new_tags
                    success = True
                    for name in to_add:
                        if not quiz_service.add_questions_to_quiz(quiz_options[name], [q['question_id']]):
                            success = False
                    for name in to_remove:
                        if not quiz_service.remove_question_from_quiz(quiz_options[name], q['question_id']):
                            success = False
                    if success:
                        st.success("✅ Tags updated")
                        st.rerun()
                    else:
                        st.error("Failed to update tags")

                delete_col = st.columns([1, 7])[0]
                with delete_col:
                    if st.button("🗑️", key=f"delete_q_{q['question_id']}"):
                        if question_service.delete_question(q['question_id']):
                            st.success("Question deleted")
                            st.rerun()
    else:
        st.info("No questions matching the filters.")

def render_delete_quiz():
    """Render delete quiz interface (delete quizzes only, keep questions)"""
    
    st.markdown("### Delete Quiz")
    
    quizzes = quiz_service.get_all_quizzes()
    if not quizzes:
        st.info("No quizzes available to delete.")
        return
    
    st.markdown("Select quizzes to delete:")
    selected_ids = []
    for quiz in quizzes:
        label = f"{quiz['quiz_name']} (ID: {quiz['quiz_id']})"
        if st.checkbox(label, key=f"delete_quiz_{quiz['quiz_id']}"):
            selected_ids.append(quiz['quiz_id'])
    
    if st.button("Delete Selected", type="primary"):
        if not selected_ids:
            st.warning("Select at least one quiz to delete.")
            return
        
        deleted = 0
        for qid in selected_ids:
            try:
                quiz_service.db.execute_query(
                    "DELETE FROM quizzes WHERE quiz_id = %s",
                    (qid,),
                    fetch=False
                )
                deleted += 1
            except Exception:
                pass
        
        if deleted:
            st.success(f"✅ Deleted {deleted} quiz(es). Questions remain intact.")
            st.rerun()
        else:
            st.error("Failed to delete selected quizzes.")

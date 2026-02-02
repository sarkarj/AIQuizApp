"""
AI Quiz Platform - Question Service
Version: 1.2.0
Changelog: 
- Enhanced to store complete validation_data with both LLM explanations
- Added method to update correct_answer when unflagging from review queue
"""

import json
from typing import Optional, List, Dict

class QuestionService:
    """Service for question management"""
    
    def __init__(self):
        self._db = None
    
    @property
    def db(self):
        """Lazy load database manager"""
        if self._db is None:
            from database.db_manager import init_db_manager
            self._db = init_db_manager()
        return self._db
    
    def create_question(self, question_data: Dict, validation_result: Dict) -> Optional[int]:
        """
        Create new question with complete validation data
        
        Args:
            question_data: Question details
            validation_result: LLM validation results with both Claude and GPT responses
        
        Returns:
            question_id or None
        """
        try:
            result = self.db.execute_one(
                """
                INSERT INTO questions (
                    question_text, options_text, response_type, correct_answer,
                    expected_count, difficulty, llm_validated, llm_conflict, validation_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING question_id
                """,
                (
                    question_data['question_text'],
                    question_data['options_text'],
                    question_data['response_type'],
                    question_data['correct_answer'],
                    question_data.get('expected_count'),
                    question_data['difficulty'],
                    validation_result['all_agree'],
                    not validation_result['all_agree'],
                    json.dumps(validation_result)
                )
            )
            return result['question_id'] if result else None
        except Exception as e:
            print(f"Error in create_question: {str(e)}")
            return None
    
    def update_question(self, question_id: int, question_data: Dict, validation_result: Dict) -> bool:
        """Update existing question"""
        try:
            self.db.execute_query(
                """
                UPDATE questions SET
                    question_text = %s,
                    options_text = %s,
                    response_type = %s,
                    correct_answer = %s,
                    expected_count = %s,
                    difficulty = %s,
                    llm_validated = %s,
                    llm_conflict = %s,
                    validation_data = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE question_id = %s
                """,
                (
                    question_data['question_text'],
                    question_data['options_text'],
                    question_data['response_type'],
                    question_data['correct_answer'],
                    question_data.get('expected_count'),
                    question_data['difficulty'],
                    validation_result['all_agree'],
                    not validation_result['all_agree'],
                    json.dumps(validation_result),
                    question_id
                ),
                fetch=False
            )
            return True
        except Exception as e:
            print(f"Error in update_question: {str(e)}")
            return False
    
    def unflag_question(self, question_id: int, chosen_answer: Optional[str] = None) -> bool:
        """
        Unflag a question after manual review
        Sets llm_conflict = FALSE and llm_validated = TRUE
        Optionally updates correct_answer based on admin's choice
        
        Args:
            question_id: Question ID
            chosen_answer: New correct answer if admin chose specific LLM's answer
        
        Returns:
            True if successful
        """
        try:
            if chosen_answer:
                # Update with new correct answer
                self.db.execute_query(
                    """
                    UPDATE questions 
                    SET llm_conflict = FALSE,
                        llm_validated = TRUE,
                        correct_answer = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE question_id = %s
                    """,
                    (chosen_answer, question_id),
                    fetch=False
                )
            else:
                # Just unflag, keep existing answer
                self.db.execute_query(
                    """
                    UPDATE questions 
                    SET llm_conflict = FALSE,
                        llm_validated = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE question_id = %s
                    """,
                    (question_id,),
                    fetch=False
                )
            return True
        except Exception as e:
            print(f"Error in unflag_question: {str(e)}")
            return False
    
    def delete_question(self, question_id: int) -> bool:
        """Delete question"""
        try:
            self.db.execute_query(
                "DELETE FROM questions WHERE question_id = %s",
                (question_id,),
                fetch=False
            )
            return True
        except Exception as e:
            print(f"Error in delete_question: {str(e)}")
            return False
    
    def get_question_by_id(self, question_id: int) -> Optional[Dict]:
        """Get question by ID"""
        try:
            return self.db.execute_one(
                "SELECT * FROM questions WHERE question_id = %s",
                (question_id,)
            )
        except Exception as e:
            print(f"Error in get_question_by_id: {str(e)}")
            return None
    
    def get_all_questions(self, filter_conflict: bool = False) -> List[Dict]:
        """Get all questions, optionally filter by conflict status"""
        try:
            query = "SELECT * FROM questions"
            params = ()
            
            if filter_conflict:
                query += " WHERE llm_conflict = TRUE"
            
            query += " ORDER BY created_at DESC"
            
            return self.db.execute_query(query, params)
        except Exception as e:
            print(f"Error in get_all_questions: {str(e)}")
            return []
    
    def get_flagged_questions(self) -> List[Dict]:
        """Get questions flagged for review"""
        return self.get_all_questions(filter_conflict=True)

    def get_flagged_questions_filtered(
        self,
        difficulty: str = "All",
        response_type: str = "All",
        manual_filter: str = "All",
        search_term: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "newest"
    ) -> Dict:
        """
        Get flagged questions with server-side filtering and pagination.
        Returns dict with items + total count.
        """
        try:
            where_clauses = ["llm_conflict = TRUE"]
            params: List = []

            if difficulty != "All":
                where_clauses.append("difficulty = %s")
                params.append(difficulty)

            if response_type != "All":
                where_clauses.append("response_type = %s")
                params.append(response_type)

            if search_term:
                where_clauses.append("(question_text ILIKE %s OR options_text ILIKE %s)")
                search_pattern = f"%{search_term}%"
                params.extend([search_pattern, search_pattern])

            if manual_filter != "All":
                if manual_filter == "Manual (Skipped AI)":
                    where_clauses.append(
                        "("
                        "validation_data->>'skipped_ai' = 'true' "
                        "OR validation_data->>'manual_entry' = 'true' "
                        "OR validation_data->'claude'->>'error' = 'AI validation skipped by user' "
                        "OR validation_data->'gpt'->>'error' = 'AI validation skipped by user'"
                        ")"
                    )
                elif manual_filter == "AI Disagreement/Error":
                    where_clauses.append(
                        "NOT ("
                        "validation_data->>'skipped_ai' = 'true' "
                        "OR validation_data->>'manual_entry' = 'true' "
                        "OR validation_data->'claude'->>'error' = 'AI validation skipped by user' "
                        "OR validation_data->'gpt'->>'error' = 'AI validation skipped by user'"
                        ")"
                    )

            where_sql = " AND ".join(where_clauses)

            # Sorting
            sort_sql = "created_at DESC"
            if sort_by == "oldest":
                sort_sql = "created_at ASC"
            elif sort_by == "id_desc":
                sort_sql = "question_id DESC"
            elif sort_by == "id_asc":
                sort_sql = "question_id ASC"

            # Total count
            count_result = self.db.execute_one(
                f"SELECT COUNT(*) as total FROM questions WHERE {where_sql}",
                tuple(params)
            )
            total = count_result['total'] if count_result else 0

            # Page of items
            offset = max(page - 1, 0) * page_size
            items = self.db.execute_query(
                f"""
                SELECT * FROM questions
                WHERE {where_sql}
                ORDER BY {sort_sql}
                LIMIT %s OFFSET %s
                """,
                tuple(params + [page_size, offset])
            )

            return {"items": items, "total": total}
        except Exception as e:
            print(f"Error in get_flagged_questions_filtered: {str(e)}")
            return {"items": [], "total": 0}
    
    def search_questions(self, search_term: str = None, difficulty: str = None) -> List[Dict]:
        """Search questions by text or difficulty"""
        try:
            query = "SELECT * FROM questions WHERE 1=1"
            params = []
            
            if search_term:
                query += " AND (question_text ILIKE %s OR options_text ILIKE %s)"
                search_pattern = f"%{search_term}%"
                params.extend([search_pattern, search_pattern])
            
            if difficulty:
                query += " AND difficulty = %s"
                params.append(difficulty)
            
            query += " ORDER BY created_at DESC"
            
            return self.db.execute_query(query, tuple(params))
        except Exception as e:
            print(f"Error in search_questions: {str(e)}")
            return []

question_service = QuestionService()

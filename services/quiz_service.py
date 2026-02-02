"""
AI Quiz Platform - Quiz Service
Version: 1.1.2
Changelog: Fixed SQL query bug - replaced SELECT DISTINCT with GROUP BY to avoid PostgreSQL ordering error
"""

import random
from typing import Optional, List, Dict
from config.settings import settings

class QuizService:
    """Service for quiz management and attempts"""
    
    def __init__(self):
        self._db = None
    
    @property
    def db(self):
        """Lazy load database manager"""
        if self._db is None:
            from database.db_manager import init_db_manager
            self._db = init_db_manager()
        return self._db
    
    def create_quiz(self, quiz_data: Dict) -> Optional[int]:
        """Create new quiz"""
        try:
            result = self.db.execute_one(
                """
                INSERT INTO quizzes (quiz_name, topic_domain, target_level, cert_reference)
                VALUES (%s, %s, %s, %s)
                RETURNING quiz_id
                """,
                (
                    quiz_data['quiz_name'],
                    quiz_data['topic_domain'],
                    quiz_data['target_level'],
                    quiz_data.get('cert_reference')
                )
            )
            return result['quiz_id'] if result else None
        except Exception as e:
            print(f"Error in create_quiz: {str(e)}")
            return None
    
    def get_all_quizzes(self) -> List[Dict]:
        """Get all quizzes"""
        try:
            return self.db.execute_query(
                "SELECT * FROM quizzes ORDER BY quiz_name"
            )
        except Exception as e:
            print(f"Error in get_all_quizzes: {str(e)}")
            return []
    
    def get_quiz_by_id(self, quiz_id: int) -> Optional[Dict]:
        """Get quiz by ID"""
        try:
            return self.db.execute_one(
                "SELECT * FROM quizzes WHERE quiz_id = %s",
                (quiz_id,)
            )
        except Exception as e:
            print(f"Error in get_quiz_by_id: {str(e)}")
            return None
    
    def add_questions_to_quiz(self, quiz_id: int, question_ids: List[int]) -> bool:
        """Add questions to quiz"""
        try:
            # Prepare batch insert
            params_list = [(quiz_id, qid) for qid in question_ids]
            
            # Use INSERT ... ON CONFLICT to avoid duplicates
            for quiz_id, question_id in params_list:
                self.db.execute_query(
                    """
                    INSERT INTO quiz_questions (quiz_id, question_id)
                    VALUES (%s, %s)
                    ON CONFLICT (quiz_id, question_id) DO NOTHING
                    """,
                    (quiz_id, question_id),
                    fetch=False
                )
            return True
        except Exception as e:
            print(f"Error in add_questions_to_quiz: {str(e)}")
            return False
    
    def remove_question_from_quiz(self, quiz_id: int, question_id: int) -> bool:
        """Remove question from quiz"""
        try:
            self.db.execute_query(
                "DELETE FROM quiz_questions WHERE quiz_id = %s AND question_id = %s",
                (quiz_id, question_id),
                fetch=False
            )
            return True
        except Exception as e:
            print(f"Error in remove_question_from_quiz: {str(e)}")
            return False
    
    def get_quiz_questions(self, quiz_id: int) -> List[Dict]:
        """Get all questions for a quiz"""
        try:
            return self.db.execute_query(
                """
                SELECT q.*
                FROM questions q
                JOIN quiz_questions qq ON q.question_id = qq.question_id
                WHERE qq.quiz_id = %s
                ORDER BY qq.added_at DESC
                """,
                (quiz_id,)
            )
        except Exception as e:
            print(f"Error in get_quiz_questions: {str(e)}")
            return []
    
    def get_quiz_stats(self, quiz_id: int) -> Dict:
        """Get quiz statistics (only non-flagged questions)"""
        try:
            # Count questions by difficulty (exclude flagged questions)
            stats = self.db.execute_query(
                """
                SELECT 
                    q.difficulty,
                    COUNT(*) as count
                FROM questions q
                JOIN quiz_questions qq ON q.question_id = qq.question_id
                WHERE qq.quiz_id = %s AND q.llm_conflict = FALSE
                GROUP BY q.difficulty
                """,
                (quiz_id,)
            )
            
            result = {'Easy': 0, 'Medium': 0, 'Hard': 0, 'total': 0}
            
            if stats:
                for stat in stats:
                    result[stat['difficulty']] = stat['count']
                    result['total'] += stat['count']
            
            return result
        except Exception as e:
            print(f"Error in get_quiz_stats: {str(e)}")
            return {'Easy': 0, 'Medium': 0, 'Hard': 0, 'total': 0}
    
    def select_questions_for_attempt(
        self, 
        quiz_id: int, 
        num_questions: int, 
        difficulty: str,
        user_id: int
    ) -> List[int]:
        """
        Select questions for quiz attempt with smart selection logic
        IMPORTANT: Excludes flagged questions (llm_conflict = TRUE)
        
        Returns:
            List of question_ids
        """
        try:
            # Get all NON-FLAGGED questions for this quiz
            all_questions = self.db.execute_query(
                """
                SELECT q.question_id, q.difficulty
                FROM questions q
                JOIN quiz_questions qq ON q.question_id = qq.question_id
                WHERE qq.quiz_id = %s AND q.llm_conflict = FALSE
                """,
                (quiz_id,)
            )
            
            if not all_questions:
                return []
            
            # Get recently seen questions (last 3 attempts)
            # FIXED: Changed from SELECT DISTINCT with ORDER BY to GROUP BY
            recent_questions = self.db.execute_query(
                """
                SELECT qa.question_id
                FROM question_attempts qa
                JOIN quiz_attempts qza ON qa.quiz_attempt_id = qza.quiz_attempt_id
                WHERE qza.user_id = %s AND qza.quiz_id = %s
                GROUP BY qa.question_id
                ORDER BY MAX(qa.answered_at) DESC
                LIMIT %s
                """,
                (user_id, quiz_id, settings.RECENT_ATTEMPTS_TO_AVOID * num_questions)
            )
            
            recent_ids = {q['question_id'] for q in recent_questions}
            
            # Filter available questions
            available = [q for q in all_questions if q['question_id'] not in recent_ids]
            
            # If not enough available, use all questions
            if len(available) < num_questions:
                available = all_questions
            
            # Separate by difficulty
            easy = [q for q in available if q['difficulty'] == 'Easy']
            medium = [q for q in available if q['difficulty'] == 'Medium']
            hard = [q for q in available if q['difficulty'] == 'Hard']
            
            # Get difficulty mix ratios
            mix = settings.DIFFICULTY_MIX.get(difficulty, settings.DIFFICULTY_MIX['Medium'])
            
            # Calculate counts
            easy_count = int(num_questions * mix['Easy'])
            medium_count = int(num_questions * mix['Medium'])
            hard_count = num_questions - easy_count - medium_count
            
            # Random selection with fallback
            selected = []
            
            # Select from each difficulty
            selected.extend(random.sample(easy, min(easy_count, len(easy))))
            selected.extend(random.sample(medium, min(medium_count, len(medium))))
            selected.extend(random.sample(hard, min(hard_count, len(hard))))
            
            # If not enough, fill from any difficulty
            if len(selected) < num_questions:
                remaining_pool = [q for q in available if q not in selected]
                if remaining_pool:
                    additional_needed = num_questions - len(selected)
                    additional = random.sample(remaining_pool, min(additional_needed, len(remaining_pool)))
                    selected.extend(additional)
            
            # Shuffle final selection
            random.shuffle(selected)
            
            return [q['question_id'] for q in selected]
            
        except Exception as e:
            print(f"Error in select_questions_for_attempt: {str(e)}")
            return []
    
    def create_quiz_attempt(self, user_id: int, quiz_id: int, question_ids: List[int], difficulty: str, session_id: str) -> Optional[int]:
        """Create new quiz attempt"""
        try:
            result = self.db.execute_one(
                """
                INSERT INTO quiz_attempts (
                    user_id, quiz_id, total_questions, difficulty_selected, session_id
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING quiz_attempt_id
                """,
                (user_id, quiz_id, len(question_ids), difficulty, session_id)
            )
            return result['quiz_attempt_id'] if result else None
        except Exception as e:
            print(f"Error in create_quiz_attempt: {str(e)}")
            return None
    
    def save_question_attempt(self, attempt_data: Dict) -> bool:
        """Save user's answer to a question"""
        try:
            self.db.execute_query(
                """
                INSERT INTO question_attempts (
                    quiz_attempt_id, question_id, user_answer, is_correct,
                    llm_explanation, llm_references, skipped
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    attempt_data['quiz_attempt_id'],
                    attempt_data['question_id'],
                    attempt_data.get('user_answer'),
                    attempt_data.get('is_correct'),
                    attempt_data.get('llm_explanation'),
                    attempt_data.get('llm_references'),
                    attempt_data.get('skipped', False)
                ),
                fetch=False
            )
            return True
        except Exception as e:
            print(f"Error in save_question_attempt: {str(e)}")
            return False
    
    def complete_quiz_attempt(self, quiz_attempt_id: int) -> bool:
        """Mark quiz attempt as completed and calculate score"""
        try:
            # Calculate correct count
            result = self.db.execute_one(
                """
                SELECT COUNT(*) as correct_count
                FROM question_attempts
                WHERE quiz_attempt_id = %s AND is_correct = TRUE
                """,
                (quiz_attempt_id,)
            )
            
            correct_count = result['correct_count'] if result else 0
            
            # Update quiz attempt
            self.db.execute_query(
                """
                UPDATE quiz_attempts
                SET completed_at = CURRENT_TIMESTAMP,
                    status = 'completed',
                    correct_count = %s
                WHERE quiz_attempt_id = %s
                """,
                (correct_count, quiz_attempt_id),
                fetch=False
            )
            return True
        except Exception as e:
            print(f"Error in complete_quiz_attempt: {str(e)}")
            return False

    def abandon_quiz_attempt(self, quiz_attempt_id: int) -> bool:
        """Mark quiz attempt as abandoned (exit early) without recalculating score"""
        try:
            self.db.execute_query(
                """
                UPDATE quiz_attempts
                SET completed_at = CURRENT_TIMESTAMP,
                    status = 'abandoned'
                WHERE quiz_attempt_id = %s
                """,
                (quiz_attempt_id,),
                fetch=False
            )
            return True
        except Exception as e:
            print(f"Error in abandon_quiz_attempt: {str(e)}")
            return False

    def get_attempt_state(self, quiz_attempt_id: int) -> Dict:
        """Get answered/skipped sets for a quiz attempt"""
        try:
            rows = self.db.execute_query(
                """
                SELECT question_id, skipped
                FROM question_attempts
                WHERE quiz_attempt_id = %s
                """,
                (quiz_attempt_id,)
            )
            answered = set()
            skipped = set()
            for r in rows:
                if r['skipped']:
                    skipped.add(r['question_id'])
                else:
                    answered.add(r['question_id'])
            return {"answered": answered, "skipped": skipped}
        except Exception as e:
            print(f"Error in get_attempt_state: {str(e)}")
            return {"answered": set(), "skipped": set()}

    def get_question_tags(self) -> List[Dict]:
        """Get question_id -> quiz_name mappings"""
        try:
            return self.db.execute_query(
                """
                SELECT qq.question_id, q.quiz_name
                FROM quiz_questions qq
                JOIN quizzes q ON qq.quiz_id = q.quiz_id
                """
            )
        except Exception as e:
            print(f"Error in get_question_tags: {str(e)}")
            return []
    
    def get_quiz_attempt_details(self, quiz_attempt_id: int) -> Optional[Dict]:
        """Get details of a quiz attempt"""
        try:
            return self.db.execute_one(
                """
                SELECT 
                    qa.*,
                    q.quiz_name,
                    q.topic_domain
                FROM quiz_attempts qa
                LEFT JOIN quizzes q ON qa.quiz_id = q.quiz_id
                WHERE qa.quiz_attempt_id = %s
                """,
                (quiz_attempt_id,)
            )
        except Exception as e:
            print(f"Error in get_quiz_attempt_details: {str(e)}")
            return None
    
    def get_attempt_question_details(self, quiz_attempt_id: int) -> List[Dict]:
        """Get all question attempts for a quiz attempt"""
        try:
            return self.db.execute_query(
                """
                SELECT 
                    qa.*,
                    q.question_text,
                    q.options_text,
                    q.correct_answer,
                    q.response_type
                FROM question_attempts qa
                JOIN questions q ON qa.question_id = q.question_id
                WHERE qa.quiz_attempt_id = %s
                ORDER BY qa.answered_at
                """,
                (quiz_attempt_id,)
            )
        except Exception as e:
            print(f"Error in get_attempt_question_details: {str(e)}")
            return []

quiz_service = QuizService()

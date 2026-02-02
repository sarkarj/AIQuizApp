"""
AI Quiz Platform - User Service
Version: 1.0.1
"""

from typing import Optional, Dict

class UserService:
    """Service for user management"""
    
    def __init__(self):
        self._db = None
    
    @property
    def db(self):
        """Lazy load database manager"""
        if self._db is None:
            from database.db_manager import init_db_manager
            self._db = init_db_manager()
        return self._db
    
    def get_or_create_user(self, username: str) -> Optional[int]:
        """
        Get existing user or create new one
        
        Returns:
            user_id
        """
        try:
            # Check if user exists
            user = self.db.execute_one(
                "SELECT user_id FROM users WHERE username = %s",
                (username,)
            )
            
            if user:
                # Update last_seen
                self.db.execute_query(
                    "UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE user_id = %s",
                    (user['user_id'],),
                    fetch=False
                )
                return user['user_id']
            else:
                # Create new user
                result = self.db.execute_one(
                    "INSERT INTO users (username) VALUES (%s) RETURNING user_id",
                    (username,)
                )
                return result['user_id'] if result else None
                
        except Exception as e:
            print(f"Error in get_or_create_user: {str(e)}")
            return None
    
    def get_user_stats(self, user_id: int) -> Dict:
        """
        Get user statistics
        
        Returns:
            {
                'total_attempts': int,
                'average_score': float,
                'best_score': float,
                'recent_trend': str
            }
        """
        try:
            # Get total attempts
            result = self.db.execute_one(
                """
                SELECT 
                    COUNT(*) as total_attempts,
                    AVG(CAST(correct_count AS FLOAT) / NULLIF(total_questions, 0) * 100) as avg_score,
                    MAX(CAST(correct_count AS FLOAT) / NULLIF(total_questions, 0) * 100) as best_score
                FROM quiz_attempts
                WHERE user_id = %s AND status = 'completed'
                """,
                (user_id,)
            )
            
            if not result:
                return {
                    'total_attempts': 0,
                    'average_score': 0.0,
                    'best_score': 0.0,
                    'recent_trend': 'No data'
                }
            
            # Calculate recent trend (last 3 vs previous 3)
            recent = self.db.execute_query(
                """
                SELECT 
                    CAST(correct_count AS FLOAT) / NULLIF(total_questions, 0) * 100 as score
                FROM quiz_attempts
                WHERE user_id = %s AND status = 'completed'
                ORDER BY completed_at DESC
                LIMIT 6
                """,
                (user_id,)
            )
            
            trend = "Stable"
            if len(recent) >= 6:
                recent_3 = sum([r['score'] for r in recent[:3]]) / 3
                previous_3 = sum([r['score'] for r in recent[3:6]]) / 3
                diff = recent_3 - previous_3
                
                if diff > 5:
                    trend = f"Improving (+{diff:.1f}%)"
                elif diff < -5:
                    trend = f"Declining ({diff:.1f}%)"
            
            return {
                'total_attempts': result['total_attempts'] or 0,
                'average_score': round(result['avg_score'] or 0, 1),
                'best_score': round(result['best_score'] or 0, 1),
                'recent_trend': trend
            }
            
        except Exception as e:
            print(f"Error in get_user_stats: {str(e)}")
            return {
                'total_attempts': 0,
                'average_score': 0.0,
                'best_score': 0.0,
                'recent_trend': 'Error'
            }
    
    def get_attempt_history(self, user_id: int, limit: int = 10) -> list:
        """
        Get user's quiz attempt history
        
        Returns:
            List of attempt records
        """
        try:
            return self.db.execute_query(
                """
                SELECT 
                    qa.quiz_attempt_id,
                    qa.started_at,
                    qa.completed_at,
                    qa.total_questions,
                    qa.correct_count,
                    qa.difficulty_selected,
                    q.quiz_name,
                    CAST(qa.correct_count AS FLOAT) / NULLIF(qa.total_questions, 0) * 100 as score_percentage
                FROM quiz_attempts qa
                LEFT JOIN quizzes q ON qa.quiz_id = q.quiz_id
                WHERE qa.user_id = %s AND qa.status = 'completed'
                ORDER BY qa.completed_at DESC
                LIMIT %s
                """,
                (user_id, limit)
            )
        except Exception as e:
            print(f"Error in get_attempt_history: {str(e)}")
            return []
    
    def get_performance_trend(self, user_id: int, limit: int = 10) -> list:
        """
        Get performance trend data for charts
        
        Returns:
            List of {attempt_number, score, date}
        """
        try:
            results = self.db.execute_query(
                """
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY completed_at) as attempt_number,
                    CAST(correct_count AS FLOAT) / NULLIF(total_questions, 0) * 100 as score,
                    completed_at
                FROM quiz_attempts
                WHERE user_id = %s AND status = 'completed'
                ORDER BY completed_at
                LIMIT %s
                """,
                (user_id, limit)
            )
            return results
        except Exception as e:
            print(f"Error in get_performance_trend: {str(e)}")
            return []

user_service = UserService()
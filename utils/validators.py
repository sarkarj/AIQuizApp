"""
AI Quiz Platform - Input Validators
Version: 1.0.0
"""

from typing import Tuple

def validate_username(username: str) -> Tuple[bool, str]:
    """Validate username format"""
    if not username or not username.strip():
        return False, "Username cannot be empty"
    
    username = username.strip()
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(username) > 50:
        return False, "Username must be less than 50 characters"
    
    if not username.replace('_', '').replace('-', '').isalnum():
        return False, "Username can only contain letters, numbers, underscore, and hyphen"
    
    return True, ""

def validate_quiz_name(quiz_name: str) -> Tuple[bool, str]:
    """Validate quiz name"""
    if not quiz_name or not quiz_name.strip():
        return False, "Quiz name cannot be empty"
    
    quiz_name = quiz_name.strip()
    
    if len(quiz_name) < 3:
        return False, "Quiz name must be at least 3 characters"
    
    if len(quiz_name) > 200:
        return False, "Quiz name must be less than 200 characters"
    
    return True, ""

def validate_question_text(question_text: str) -> Tuple[bool, str]:
    """Validate question text"""
    if not question_text or not question_text.strip():
        return False, "Question text cannot be empty"
    
    if len(question_text.strip()) < 10:
        return False, "Question must be at least 10 characters"
    
    return True, ""

def validate_expected_count(expected_count: int, num_options: int) -> Tuple[bool, str]:
    """Validate expected count for multiple selection"""
    if expected_count < 2:
        return False, "Expected count must be at least 2"
    
    if expected_count > num_options:
        return False, f"Expected count cannot exceed number of options ({num_options})"
    
    if expected_count == num_options:
        return False, "Expected count cannot equal total options (would make question trivial)"
    
    return True, ""

def validate_admin_credentials(username: str, password: str, correct_username: str, correct_password: str) -> bool:
    """Validate admin credentials"""
    return username == correct_username and password == correct_password

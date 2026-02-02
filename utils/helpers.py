"""
AI Quiz Platform - Helper Utilities
Version: 1.0.0
"""

import re
from typing import List, Tuple, Optional

def parse_options(options_text: str) -> List[Tuple[str, str]]:
    """
    Parse options text into structured format
    
    Args:
        options_text: Raw options like "A. Option 1\nB. Option 2"
    
    Returns:
        List of tuples [(letter, text), ...]
    """
    lines = options_text.strip().split('\n')
    options = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Match pattern: "A. Text" or "A) Text"
        match = re.match(r'^([A-E])[.)]\s*(.+)$', line, re.IGNORECASE)
        if match:
            letter, text = match.groups()
            options.append((letter.upper(), text.strip()))
    
    return options

def format_options_for_storage(options: List[Tuple[str, str]]) -> str:
    """
    Format options for database storage
    
    Args:
        options: List of tuples [(letter, text), ...]
    
    Returns:
        Formatted string "A. Option 1\nB. Option 2"
    """
    return '\n'.join([f"{letter}. {text}" for letter, text in options])

def validate_options_format(options_text: str) -> Tuple[bool, str]:
    """
    Validate options format
    
    Returns:
        (is_valid, error_message)
    """
    if not options_text or not options_text.strip():
        return False, "Options cannot be empty"
    
    options = parse_options(options_text)
    
    if len(options) < 2:
        return False, "Must have at least 2 options"
    
    if len(options) > 5:
        return False, "Cannot have more than 5 options"
    
    # Check sequential letters
    expected_letters = ['A', 'B', 'C', 'D', 'E'][:len(options)]
    actual_letters = [opt[0] for opt in options]
    
    if actual_letters != expected_letters:
        return False, f"Options must be sequential starting from A (expected: {', '.join(expected_letters)})"
    
    return True, ""

def validate_correct_answer(correct_answer: str, options: List[Tuple[str, str]], response_type: str) -> Tuple[bool, str]:
    """
    Validate correct answer format
    
    Returns:
        (is_valid, error_message)
    """
    if not correct_answer or not correct_answer.strip():
        return False, "Correct answer cannot be empty"
    
    correct_answer = correct_answer.strip().upper()
    available_letters = [opt[0] for opt in options]
    
    if response_type == 'single':
        if len(correct_answer) != 1:
            return False, "Single response must have exactly one answer (e.g., 'A')"
        if correct_answer not in available_letters:
            return False, f"Answer must be one of: {', '.join(available_letters)}"
    else:  # multiple
        answers = [a.strip() for a in correct_answer.split(',')]
        if len(answers) < 2:
            return False, "Multiple selection must have at least 2 correct answers"
        for ans in answers:
            if ans not in available_letters:
                return False, f"Invalid answer '{ans}'. Must be one of: {', '.join(available_letters)}"
    
    return True, ""

def format_answer_for_display(answer: str) -> str:
    """Format answer for user-friendly display"""
    if ',' in answer:
        return ', '.join(answer.split(','))
    return answer

def parse_user_answer(selected_options: List[str]) -> str:
    """
    Parse user's selected options into storage format
    
    Args:
        selected_options: List like ["A. Option 1", "C. Option 3"]
    
    Returns:
        Comma-separated letters "A,C"
    """
    letters = []
    for option in selected_options:
        match = re.match(r'^([A-E])[.)]\s*', option)
        if match:
            letters.append(match.group(1))
    
    return ','.join(sorted(letters))

def check_answer_correctness(user_answer: str, correct_answer: str) -> bool:
    """
    Check if user answer matches correct answer
    
    Args:
        user_answer: "A" or "A,C"
        correct_answer: "A" or "A,C"
    
    Returns:
        True if answers match
    """
    # Normalize both answers
    user_set = set(user_answer.upper().replace(' ', '').split(','))
    correct_set = set(correct_answer.upper().replace(' ', '').split(','))
    
    return user_set == correct_set

def calculate_percentage(correct: int, total: int) -> float:
    """Calculate percentage score"""
    if total == 0:
        return 0.0
    return round((correct / total) * 100, 1)

def get_performance_emoji(percentage: float) -> str:
    """Get emoji based on performance"""
    if percentage >= 90:
        return "🏆"
    elif percentage >= 80:
        return "🌟"
    elif percentage >= 70:
        return "👍"
    elif percentage >= 60:
        return "📚"
    else:
        return "💪"

def get_motivational_message(percentage: float, attempt_count: int) -> str:
    """Generate motivational message"""
    if percentage >= 90:
        messages = [
            "Outstanding! You're mastering this topic! 🎉",
            "Excellent work! Keep up the momentum! 🚀",
            "You're crushing it! Amazing performance! ⭐"
        ]
    elif percentage >= 70:
        messages = [
            "Great job! You're on the right track! 💪",
            "Well done! Keep practicing to reach mastery! 📈",
            "Good progress! You're getting better! 👏"
        ]
    else:
        messages = [
            "Keep going! Every attempt makes you stronger! 💪",
            "Don't give up! You're building your knowledge! 📚",
            "Practice makes perfect! You've got this! 🎯"
        ]
    
    import random
    return random.choice(messages)

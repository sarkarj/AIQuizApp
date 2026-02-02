-- AI Quiz Platform - Database Schema
-- Version: 1.0.1
-- PostgreSQL 15+
-- Changelog: Added UNIQUE constraint on question_attempts to prevent duplicate answers

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_username ON users(username);

-- Quizzes table
CREATE TABLE IF NOT EXISTS quizzes (
    quiz_id SERIAL PRIMARY KEY,
    quiz_name VARCHAR(200) UNIQUE NOT NULL,
    topic_domain VARCHAR(200) NOT NULL,
    target_level VARCHAR(50) CHECK (target_level IN ('Beginner', 'Intermediate', 'Advanced')),
    cert_reference VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_quiz_name ON quizzes(quiz_name);

-- Questions table
CREATE TABLE IF NOT EXISTS questions (
    question_id SERIAL PRIMARY KEY,
    question_text TEXT NOT NULL,
    options_text TEXT NOT NULL,
    response_type VARCHAR(20) CHECK (response_type IN ('single', 'multiple')) NOT NULL,
    correct_answer VARCHAR(50) NOT NULL,
    expected_count INTEGER,
    difficulty VARCHAR(20) CHECK (difficulty IN ('Easy', 'Medium', 'Hard')) NOT NULL,
    llm_validated BOOLEAN DEFAULT FALSE,
    llm_conflict BOOLEAN DEFAULT FALSE,
    validation_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_difficulty ON questions(difficulty);
CREATE INDEX IF NOT EXISTS idx_llm_conflict ON questions(llm_conflict);
-- Speed up manual vs AI filtering on review queue
CREATE INDEX IF NOT EXISTS idx_questions_manual_entry ON questions ((validation_data->>'manual_entry'));
CREATE INDEX IF NOT EXISTS idx_questions_skipped_ai ON questions ((validation_data->>'skipped_ai'));

-- Quiz-Questions mapping (Many-to-Many)
CREATE TABLE IF NOT EXISTS quiz_questions (
    id SERIAL PRIMARY KEY,
    quiz_id INTEGER REFERENCES quizzes(quiz_id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(question_id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(quiz_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_questions_quiz ON quiz_questions(quiz_id);
CREATE INDEX IF NOT EXISTS idx_quiz_questions_question ON quiz_questions(question_id);

-- Quiz attempts table
CREATE TABLE IF NOT EXISTS quiz_attempts (
    quiz_attempt_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    quiz_id INTEGER REFERENCES quizzes(quiz_id) ON DELETE SET NULL,
    total_questions INTEGER NOT NULL,
    correct_count INTEGER DEFAULT 0,
    difficulty_selected VARCHAR(20),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    session_id VARCHAR(100),
    status VARCHAR(20) CHECK (status IN ('in_progress', 'completed', 'abandoned')) DEFAULT 'in_progress'
);

CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user ON quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_session ON quiz_attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_started ON quiz_attempts(started_at);

-- Question attempts table
CREATE TABLE IF NOT EXISTS question_attempts (
    attempt_id SERIAL PRIMARY KEY,
    quiz_attempt_id INTEGER REFERENCES quiz_attempts(quiz_attempt_id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(question_id) ON DELETE CASCADE,
    user_answer VARCHAR(50),
    is_correct BOOLEAN,
    llm_explanation TEXT,
    llm_references TEXT,
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    skipped BOOLEAN DEFAULT FALSE,
    -- ADDED v1.0.1: Prevent duplicate attempts for same question in same quiz attempt
    -- This allows UPSERT functionality when answering previously skipped questions
    CONSTRAINT question_attempts_unique_attempt_question UNIQUE (quiz_attempt_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_question_attempts_quiz ON question_attempts(quiz_attempt_id);
CREATE INDEX IF NOT EXISTS idx_question_attempts_question ON question_attempts(question_id);

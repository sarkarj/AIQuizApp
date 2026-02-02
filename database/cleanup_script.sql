-- AI Quiz Platform - Database Cleanup Script
-- Version: 1.0.0
-- Purpose: Clean all tables for fresh start (use with caution!)
-- 
-- USAGE:
-- From container: psql -U quiz_user -d quiz_db -f cleanup_script.sql
-- 
-- WARNING: This will DELETE ALL DATA from all tables!

-- Disable foreign key checks temporarily
SET session_replication_role = 'replica';

-- Clean all data from tables (in correct order due to foreign keys)
TRUNCATE TABLE question_attempts CASCADE;
TRUNCATE TABLE quiz_attempts CASCADE;
TRUNCATE TABLE quiz_questions CASCADE;
TRUNCATE TABLE questions CASCADE;
TRUNCATE TABLE quizzes CASCADE;
TRUNCATE TABLE users CASCADE;

-- Re-enable foreign key checks
SET session_replication_role = 'origin';

-- Reset sequences to start from 1
ALTER SEQUENCE users_user_id_seq RESTART WITH 1;
ALTER SEQUENCE quizzes_quiz_id_seq RESTART WITH 1;
ALTER SEQUENCE questions_question_id_seq RESTART WITH 1;
ALTER SEQUENCE quiz_questions_id_seq RESTART WITH 1;
ALTER SEQUENCE quiz_attempts_quiz_attempt_id_seq RESTART WITH 1;
ALTER SEQUENCE question_attempts_attempt_id_seq RESTART WITH 1;

-- Verify cleanup (should return 0 for all)
SELECT 'users' as table_name, COUNT(*) as record_count FROM users
UNION ALL
SELECT 'quizzes', COUNT(*) FROM quizzes
UNION ALL
SELECT 'questions', COUNT(*) FROM questions
UNION ALL
SELECT 'quiz_questions', COUNT(*) FROM quiz_questions
UNION ALL
SELECT 'quiz_attempts', COUNT(*) FROM quiz_attempts
UNION ALL
SELECT 'question_attempts', COUNT(*) FROM question_attempts;

-- Success message
\echo '✅ Database cleanup completed successfully!'
\echo 'All tables are now empty and sequences reset.'

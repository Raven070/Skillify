-- This schema defines the complete database structure for the AI Explorers website.
-- It is compatible with the final SQLAlchemy version of the application.

-- Drop tables in reverse order of dependency to prevent foreign key errors.

DROP TABLE IF EXISTS password_reset_tokens;
DROP TABLE IF EXISTS student_quiz_attempts;
DROP TABLE IF EXISTS video_completions;
DROP TABLE IF EXISTS student_course_access;
DROP TABLE IF EXISTS quizzes;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS users;


-- Table for user accounts
CREATE TABLE users (
    id INTEGER NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    email VARCHAR(100) NOT NULL, 
    password VARCHAR(200) NOT NULL, 
    account_code VARCHAR(50) NOT NULL, 
    is_admin BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (email), 
    UNIQUE (account_code)
);

-- Table for courses
CREATE TABLE courses (
    id INTEGER NOT NULL, 
    title VARCHAR(150) NOT NULL, 
    description TEXT NOT NULL, 
    thumbnail_url VARCHAR(200), 
    status VARCHAR(20) NOT NULL, 
    duration_weeks INTEGER, 
    student_count INTEGER, 
    PRIMARY KEY (id)
);

-- Table for individual sessions within a course
CREATE TABLE sessions (
    id INTEGER NOT NULL, 
    course_id INTEGER NOT NULL, 
    title VARCHAR(150) NOT NULL, 
    thumbnail_url VARCHAR(200), 
    is_free BOOLEAN NOT NULL, 
    video1_url VARCHAR(300), 
    video2_url VARCHAR(300), 
    video3_url VARCHAR(300), 
    video4_url VARCHAR(300), 
    PRIMARY KEY (id), 
    FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);

-- Table for quiz questions
CREATE TABLE quizzes (
    id INTEGER NOT NULL, 
    session_id INTEGER NOT NULL, 
    question TEXT NOT NULL, 
    option1 VARCHAR(200) NOT NULL, 
    option2 VARCHAR(200) NOT NULL, 
    option3 VARCHAR(200) NOT NULL, 
    option4 VARCHAR(200) NOT NULL, 
    correct_answer INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

-- Table to link students to the courses they have access to
CREATE TABLE student_course_access (
    id INTEGER NOT NULL, 
    user_id INTEGER NOT NULL, 
    course_id INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE,
    UNIQUE (user_id, course_id)
);

-- Table to track completion of individual videos
CREATE TABLE video_completions (
    id INTEGER NOT NULL, 
    user_id INTEGER NOT NULL, 
    session_id INTEGER NOT NULL, 
    video_index INTEGER NOT NULL, 
    completed_at DATETIME NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE,
    UNIQUE (user_id, session_id, video_index)
);

-- Table to store student quiz results
CREATE TABLE student_quiz_attempts (
    id INTEGER NOT NULL, 
    user_id INTEGER NOT NULL, 
    session_id INTEGER NOT NULL, 
    score INTEGER NOT NULL, 
    total_questions INTEGER NOT NULL, 
    attempted_on DATETIME NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

-- Table for temporary password reset tokens
CREATE TABLE password_reset_tokens (
    id INTEGER NOT NULL, 
    user_id INTEGER NOT NULL, 
    token VARCHAR(100) NOT NULL, 
    expires_at DATETIME NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    UNIQUE (token)
);

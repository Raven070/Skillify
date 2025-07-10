

-- Drop tables in reverse order of dependency
DROP TABLE IF EXISTS student_quiz_attempts;
DROP TABLE IF EXISTS video_completions;
DROP TABLE IF EXISTS password_reset_tokens;
DROP TABLE IF EXISTS quizzes;
DROP TABLE IF EXISTS student_course_access;
DROP TABLE IF EXISTS session_content; -- NEW
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    account_code TEXT UNIQUE NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    thumbnail_url TEXT,
    status TEXT NOT NULL DEFAULT 'active' -- 'active' or 'coming_soon'
);

CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    thumbnail_url TEXT,
    is_free INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
    -- All videoX_url columns have been REMOVED from here
);

CREATE TABLE session_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    content_order INTEGER NOT NULL, -- The order it appears in (1, 2, 3, etc.)
    content_type TEXT NOT NULL, -- 'video' or 'text_page'
    title TEXT NOT NULL, -- Title for this specific block (e.g., "Introduction Video" or "Reading Material")
    content_data TEXT NOT NULL, -- Stores the video URL or the HTML for the text page
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

CREATE TABLE quizzes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    option1 TEXT NOT NULL,
    option2 TEXT NOT NULL,
    option3 TEXT NOT NULL,
    option4 TEXT NOT NULL,
    correct_answer INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

-- NEW TABLE: This replaces the old session access table
CREATE TABLE student_course_access (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
    UNIQUE(user_id, course_id) -- A user can't be granted access to the same course twice
);

CREATE TABLE video_completions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    video_index INTEGER NOT NULL,
    completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
    UNIQUE(user_id, session_id, video_index)
);

CREATE TABLE student_quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    attempted_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

-- Default admin user (password: admin)
INSERT INTO users (name, email, password, account_code, is_admin) VALUES 
('Admin', 'admin@example.com', 'pbkdf2:sha256:260000$tZ2iXyGDFsFbXyga$55e3c3b52f9b3b8e8f8d0a07c08bf6060c49b8979d3a7d4a6b2c6de3f1b4a1b5', 'ADMIN-001', 1);


-- Add sample "coming soon" courses
INSERT INTO courses (title, description, thumbnail_url, status) VALUES
('ML Concepts and Code', 'Dive into the world of Machine Learning from scratch.', 'https://placehold.co/600x400/7E57C2/FFFFFF?text=ML', 'coming_soon'),
('Robotics', 'Learn to build and program your own robots.', 'https://placehold.co/600x400/7E57C2/FFFFFF?text=Robotics', 'coming_soon');
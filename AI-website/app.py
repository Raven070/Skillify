import sqlite3
import uuid
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import datetime
import secrets

# --- APP CONFIGURATION ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
DATABASE = 'database.db'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
port = int(os.environ.get('PORT', 5000))

# --- DATABASE HELPER FUNCTIONS ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.cli.command('init-db')
def init_db_command():
    init_db()
    print('Initialized the database.')

# --- HOOKS & CONTEXT PROCESSORS ---
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.date.today().year}

@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        user = get_db().execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        g.user = user

# --- GENERAL HELPER FUNCTIONS & DECORATORS ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            flash('You need to be logged in to access this page.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('You must be an admin to view this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- STUDENT-FACING & GENERAL ROUTES ---
@app.route('/')
def index():
    db = get_db()
    courses = db.execute('SELECT * FROM courses ORDER BY id').fetchall()
    accessible_courses = set()
    if g.user:
        accessible_courses_rows = db.execute('SELECT course_id FROM student_course_access WHERE user_id = ?', (g.user['id'],)).fetchall()
        accessible_courses = {row['course_id'] for row in accessible_courses_rows}
    return render_template('index.html', courses=courses, accessible_courses=accessible_courses)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']; email = request.form['email']; password = request.form['password']
        db = get_db(); error = None
        if not name: error = 'Name is required.'
        elif not email: error = 'Email is required.'
        elif not password: error = 'Password is required.'
        elif db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone():
            error = f"Email {email} is already registered."
        if error is None:
            acc_code = f"AI-YOUTH-{str(uuid.uuid4().hex[:6]).upper()}"
            db.execute('INSERT INTO users (name, email, password, account_code) VALUES (?, ?, ?, ?)',
                       (name, email, generate_password_hash(password), acc_code))
            db.commit()
            flash('Registration successful! Please save your Account Code.', 'success')
            return redirect(url_for('welcome', code=acc_code, name=name))
        flash(error, 'error')
    return render_template('register.html')

@app.route('/welcome')
def welcome():
    return render_template('welcome.html', account_code=request.args.get('code'), name=request.args.get('name'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']; password = request.form['password']
        db = get_db(); user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone(); error = None
        if user is None: error = 'Incorrect email.'
        elif not check_password_hash(user['password'], password): error = 'Incorrect password.'
        if error is None:
            session.clear(); session['user_id'] = user['id']; session['is_admin'] = user['is_admin']
            if user['is_admin']: return redirect(url_for('admin_dashboard'))
            return redirect(url_for('courses'))
        flash(error, 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/courses')
@login_required
def courses():
    db = get_db()
    all_courses = db.execute('SELECT * FROM courses ORDER BY id').fetchall()
    accessible_courses_ids = {row['course_id'] for row in db.execute('SELECT course_id FROM student_course_access WHERE user_id = ?', (g.user['id'],)).fetchall()}
    enrolled_courses = []
    other_courses = []
    for course in all_courses:
        if course['id'] in accessible_courses_ids:
            enrolled_courses.append(course)
        else:
            other_courses.append(course)
    return render_template('courses.html', enrolled_courses=enrolled_courses, other_courses=other_courses, accessible_courses=accessible_courses_ids)

@app.route('/request_course_access/<int:course_id>')
@login_required
def request_course_access(course_id):
    course = get_db().execute('SELECT title FROM courses WHERE id = ?', (course_id,)).fetchone()
    if course:
        flash(f"The course '{course['title']}' requires payment. To get access, please contact us and we will help.", 'info')
    return redirect(url_for('courses'))

@app.route('/course/<int:course_id>')
@login_required
def course_detail(course_id):
    db = get_db()
    course = db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course:
        flash('Course not found.', 'error'); return redirect(url_for('courses'))
    
    has_access = db.execute('SELECT 1 FROM student_course_access WHERE user_id = ? AND course_id = ?', (g.user['id'], course_id)).fetchone() is not None
    sessions = db.execute('SELECT * FROM sessions WHERE course_id = ? ORDER BY id', (course_id,)).fetchall()
    
    progress = 0
    g.user_completed_videos = set()
    if has_access:
        user_completed_videos_rows = db.execute('SELECT session_id, video_index FROM video_completions WHERE user_id = ?', (g.user['id'],)).fetchall()
        g.user_completed_videos = set((row['session_id'], row['video_index']) for row in user_completed_videos_rows)
        sessions_mutable = [dict(row) for row in sessions]
        completed_vids_per_sess = {s['id']: db.execute('SELECT COUNT(DISTINCT video_index) FROM video_completions WHERE user_id = ? AND session_id = ?', (g.user['id'], s['id'])).fetchone()[0] for s in sessions_mutable}
        
        total_vids_course = 0; total_comp_vids_course = 0
        for s_dict in sessions_mutable:
            session_vids = [s_dict.get(f'video{j}_url') for j in range(1, 5)]
            num_vids_in_sess = sum(1 for url in session_vids if url and url.strip())
            total_vids_course += num_vids_in_sess
            num_comp_for_this_session = completed_vids_per_sess.get(s_dict['id'], 0)
            total_comp_vids_course += num_comp_for_this_session
            s_dict['is_session_fully_completed'] = (num_vids_in_sess > 0 and num_comp_for_this_session == num_vids_in_sess)
        
        sessions = sessions_mutable
        progress = (total_comp_vids_course / total_vids_course) * 100 if total_vids_course > 0 else 0
        
    return render_template('course_detail.html', course=course, sessions=sessions, progress=progress, has_access=has_access)

@app.route('/session/<int:session_id>/video/<int:video_index>')
@login_required
def session_detail(session_id, video_index):
    db = get_db()
    session_data = db.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
    if not session_data:
        flash('Session not found.', 'error'); return redirect(url_for('courses'))

    course_id = session_data['course_id']
    has_course_access = db.execute('SELECT 1 FROM student_course_access WHERE user_id = ? AND course_id = ?', (g.user['id'], course_id)).fetchone()
    
    if not session_data['is_free'] and not has_course_access:
        flash('You must have access to the course to view this protected session.', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    
    vid_urls = [session_data[f'video{i}_url'] for i in range(1, 5)]
    valid_vids = [url for url in vid_urls if url and url.strip()]
    
    if not (1 <= video_index <= len(valid_vids)):
        flash('Invalid video number.', 'error'); return redirect(url_for('course_detail', course_id=course_id))
    
    current_video_url = valid_vids[video_index - 1]
    completion = db.execute('SELECT 1 FROM video_completions WHERE user_id = ? AND session_id = ? AND video_index = ?', (g.user['id'], session_id, video_index)).fetchone()
    quizzes = db.execute('SELECT * FROM quizzes WHERE session_id = ?', (session_id,)).fetchall()
    
    return render_template('session_detail.html', session=session_data, current_video_url=current_video_url,
                           video_index=video_index, total_videos=len(valid_vids),
                           is_completed=(completion is not None), quizzes=quizzes)

@app.route('/session/<int:session_id>/video/<int:video_index>/mark_complete', methods=['POST'])
@login_required
def mark_video_complete(session_id, video_index):
    db = get_db()
    if not db.execute('SELECT 1 FROM video_completions WHERE user_id = ? AND session_id = ? AND video_index = ?', (g.user['id'], session_id, video_index)).fetchone():
        db.execute('INSERT INTO video_completions (user_id, session_id, video_index) VALUES (?, ?, ?)', (g.user['id'], session_id, video_index)); db.commit()
        flash(f'Video {video_index} marked as complete!', 'success')
    return redirect(url_for('session_detail', session_id=session_id, video_index=video_index))

@app.route('/session/<int:session_id>/submit_quiz', methods=['POST'])
@login_required
def submit_quiz(session_id):
    db = get_db(); sess_data = db.execute('SELECT course_id FROM sessions WHERE id = ?', (session_id,)).fetchone()
    if not sess_data: flash('Session not found.', 'error'); return redirect(url_for('courses'))
    quizzes = db.execute('SELECT * FROM quizzes WHERE session_id = ?', (session_id,)).fetchall(); score = 0
    for quiz in quizzes:
        if request.form.get(f'quiz_{quiz["id"]}') and int(request.form.get(f'quiz_{quiz["id"]}')) == quiz['correct_answer']: score += 1
    
    attempt = db.execute('SELECT id FROM student_quiz_attempts WHERE user_id = ? AND session_id = ?', (g.user['id'], session_id)).fetchone()
    if attempt is None: db.execute('INSERT INTO student_quiz_attempts (user_id, session_id, score, total_questions) VALUES (?, ?, ?, ?)', (g.user['id'], session_id, score, len(quizzes)))
    else: db.execute('UPDATE student_quiz_attempts SET score = ?, total_questions = ?, attempted_on = CURRENT_TIMESTAMP WHERE id = ?', (score, len(quizzes), attempt['id']))
    db.commit(); flash(f'Quiz submitted! You scored {score}/{len(quizzes)}.', 'success')
    return redirect(url_for('course_detail', course_id=sess_data['course_id']))

@app.route('/session/<int:session_id>/finish_session')
@login_required
def finish_session(session_id):
    sess_data = get_db().execute('SELECT s.title as session_title, c.id as course_id, c.title as course_title FROM sessions s JOIN courses c ON s.course_id = c.id WHERE s.id = ?', (session_id,)).fetchone()
    if not sess_data: flash('Session not found.', 'error'); return redirect(url_for('courses'))
    return render_template('finish_page.html', session=sess_data)

@app.route('/contact')
def contact(): return render_template('contact.html')

@app.route('/profile')
@login_required
def profile():
    db = get_db()
    enrolled_courses = db.execute(
        "SELECT DISTINCT c.id, c.title, c.description, c.thumbnail_url, c.duration_weeks, c.student_count FROM courses c "
        "JOIN student_course_access sca ON c.id = sca.course_id "
        "WHERE sca.user_id = ? ORDER BY c.id",
        (g.user['id'],)
    ).fetchall()
    return render_template('profile.html', user=g.user, enrolled_courses=enrolled_courses)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        db = get_db(); user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if user:
            token = secrets.token_urlsafe(16)
            expires_at = datetime.datetime.now() + datetime.timedelta(hours=1)
            db.execute('INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)', (user['id'], token, expires_at)); db.commit()
            reset_url = url_for('reset_password', token=token, _external=True)
            print(f"--- PASSWORD RESET LINK (SIMULATED EMAIL): {reset_url} ---")
        flash('If an account with that email exists, a reset link has been sent (check console).', 'info')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    db = get_db()
    token_data = db.execute('SELECT * FROM password_reset_tokens WHERE token = ? AND expires_at > ?', (token, datetime.datetime.now())).fetchone()
    if not token_data:
        flash('Password reset link is invalid or has expired.', 'error'); return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        password = request.form.get('password')
        if not password or password != request.form.get('confirm_password'):
            flash('Passwords do not match.', 'error'); return render_template('reset_password.html', token=token)
        db.execute('UPDATE users SET password = ? WHERE id = ?', (generate_password_hash(password), token_data['user_id']))
        db.execute('DELETE FROM password_reset_tokens WHERE id = ?', (token_data['id'],)); db.commit()
        flash('Password has been reset successfully. Please log in.', 'success'); return redirect(url_for('login'))
    return render_template('reset_password.html', token=token)

# --- ADMIN ROUTES ---
@app.route('/admin')
@admin_required
def admin_dashboard(): return render_template('admin_dashboard.html')

@app.route('/admin/add_course', methods=['GET', 'POST'])
@admin_required
def admin_add_course():
    if request.method == 'POST':
        title = request.form['title']; desc = request.form['description']; status = request.form['status']
        duration = request.form.get('duration_weeks', 0, type=int); students = request.form.get('student_count', 0, type=int)
        if 'thumbnail' not in request.files or not request.files['thumbnail'].filename:
            flash('Thumbnail file is required.', 'error'); return redirect(request.url)
        file = request.files['thumbnail']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            thumb_path = f'uploads/{filename}'
            get_db().execute('INSERT INTO courses (title, description, thumbnail_url, status, duration_weeks, student_count) VALUES (?, ?, ?, ?, ?, ?)',
                       (title, desc, thumb_path, status, duration, students)); get_db().commit()
            flash(f"Course '{title}' added!", 'success'); return redirect(url_for('courses'))
        else: flash('Invalid thumbnail file type.', 'error'); return redirect(request.url)
    return render_template('admin_add_course.html')

@app.route('/admin/edit_course/<int:course_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_course(course_id):
    db = get_db(); course = db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course: flash('Course not found.', 'error'); return redirect(url_for('admin_manage_courses'))
    if request.method == 'POST':
        title = request.form['title']; desc = request.form['description']; status = request.form['status']
        duration = request.form.get('duration_weeks', 0, type=int); students = request.form.get('student_count', 0, type=int)
        thumb_path = course['thumbnail_url']
        if 'thumbnail' in request.files:
            file = request.files['thumbnail']
            if file and file.filename and allowed_file(file.filename):
                if course['thumbnail_url'] and course['thumbnail_url'].startswith('uploads/'):
                    try: os.remove(os.path.join(app.root_path, 'static', course['thumbnail_url']))
                    except OSError as e: print(f"Error deleting old thumbnail: {e}")
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename)); thumb_path = f'uploads/{filename}'
        
        # CORRECTED: This now includes duration_weeks and student_count in the UPDATE
        db.execute('UPDATE courses SET title = ?, description = ?, status = ?, thumbnail_url = ?, duration_weeks = ?, student_count = ? WHERE id = ?',
                   (title, desc, status, thumb_path, duration, students, course_id)); db.commit()
        flash(f"Course '{title}' updated!", 'success'); return redirect(url_for('admin_manage_courses'))
    return render_template('edit_course.html', course=course)

@app.route('/admin/manage_courses')
@admin_required
def admin_manage_courses():
    courses = get_db().execute('SELECT * FROM courses ORDER BY id DESC').fetchall()
    return render_template('admin_manage_courses.html', courses=courses)

@app.route('/admin/delete_course/<int:course_id>', methods=['POST'])
@admin_required
def admin_delete_course(course_id):
    db = get_db(); course = db.execute('SELECT thumbnail_url FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course: flash('Course not found.', 'error'); return redirect(url_for('admin_manage_courses'))
    
    if course['thumbnail_url'] and course['thumbnail_url'].startswith('uploads/'):
        try: os.remove(os.path.join(app.root_path, 'static', course['thumbnail_url']))
        except OSError as e: print(f"Error deleting course thumbnail: {e}")

    sessions = db.execute('SELECT * FROM sessions WHERE course_id = ?', (course_id,)).fetchall()
    for sess in sessions:
        for i in range(1, 5):
            video_url = sess[f'video{i}_url']
            if video_url and video_url.startswith('uploads/'):
                try: os.remove(os.path.join(app.root_path, 'static', video_url))
                except OSError as e: print(f"Error deleting session video: {e}")
    
    db.execute('DELETE FROM courses WHERE id = ?', (course_id,)); db.commit()
    flash('Course and all its related content have been deleted.', 'success')
    return redirect(url_for('admin_manage_courses'))

@app.route('/admin/add_session', methods=['GET', 'POST'])
@admin_required
def admin_add_session():
    db = get_db(); courses_list = db.execute('SELECT id, title FROM courses WHERE status = "active" ORDER BY title').fetchall()
    if request.method == 'POST':
        course_id = request.form.get('course_id'); title = request.form.get('title'); is_free = 1 if request.form.get('is_free') == '1' else 0
        thumb_path = None
        if 'thumbnail_file' in request.files:
            thumb_file = request.files['thumbnail_file']
            if thumb_file and thumb_file.filename and allowed_file(thumb_file.filename):
                thumb_filename = secure_filename(thumb_file.filename)
                thumb_file.save(os.path.join(app.config['UPLOAD_FOLDER'], thumb_filename)); thumb_path = f'uploads/{thumb_filename}'
        paths = [None] * 4
        for i in range(1, 5):
            video_type = request.form.get(f'video{i}_type')
            if video_type == 'url' and request.form.get(f'video{i}_url', '').strip(): paths[i-1] = request.form.get(f'video{i}_url').strip()
            elif video_type == 'upload' and f'video{i}_file' in request.files:
                file = request.files[f'video{i}_file']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename)); paths[i-1] = f'uploads/{filename}'
        if not all([course_id, title, paths[0]]): flash('Course, Title, and Video 1 are required.', 'error')
        else:
            db.execute('INSERT INTO sessions (course_id, title, thumbnail_url, is_free, video1_url, video2_url, video3_url, video4_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       (int(course_id), title, thumb_path, is_free, paths[0], paths[1], paths[2], paths[3])); db.commit()
            flash(f"Session '{title}' added!", 'success'); return redirect(url_for('course_detail', course_id=int(course_id)))
    return render_template('admin_add_session.html', courses=courses_list)

@app.route('/admin/edit_session/<int:session_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_session(session_id):
    db = get_db(); session_data = db.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
    if not session_data: flash('Session not found.', 'error'); return redirect(url_for('admin_manage_sessions'))
    if request.method == 'POST':
        title = request.form['title']; is_free = 1 if request.form.get('is_free') == '1' else 0
        new_thumb_path = session_data['thumbnail_url']
        if 'thumbnail_file' in request.files:
            thumb_file = request.files['thumbnail_file']
            if thumb_file and thumb_file.filename and allowed_file(thumb_file.filename):
                if session_data['thumbnail_url'] and session_data['thumbnail_url'].startswith('uploads/'):
                    try: os.remove(os.path.join(app.root_path, 'static', session_data['thumbnail_url']))
                    except OSError as e: print(f"Error deleting old session thumbnail: {e}")
                thumb_filename = secure_filename(thumb_file.filename)
                thumb_file.save(os.path.join(app.config['UPLOAD_FOLDER'], thumb_filename)); new_thumb_path = f'uploads/{thumb_filename}'
        
        video_paths = [session_data[f'video{i}_url'] for i in range(1, 5)]
        for i in range(1, 5):
            idx = i - 1; new_url = request.form.get(f'video{i}_url', '').strip(); file = request.files.get(f'video{i}_file')
            if file and file.filename:
                if allowed_file(file.filename):
                    if video_paths[idx] and video_paths[idx].startswith('uploads/'):
                        try: os.remove(os.path.join(app.root_path, 'static', video_paths[idx]))
                        except OSError as e: print(f"Error deleting old video file: {e}")
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename)); video_paths[idx] = f'uploads/{filename}'
            elif new_url:
                if video_paths[idx] and video_paths[idx].startswith('uploads/'):
                    try: os.remove(os.path.join(app.root_path, 'static', video_paths[idx]))
                    except OSError as e: print(f"Error deleting old video file: {e}")
                video_paths[idx] = new_url
        
        db.execute('UPDATE sessions SET title = ?, thumbnail_url = ?, is_free = ?, video1_url = ?, video2_url = ?, video3_url = ?, video4_url = ? WHERE id = ?',
                   (title, new_thumb_path, is_free, video_paths[0], video_paths[1], video_paths[2], video_paths[3], session_id)); db.commit()
        flash(f"Session '{title}' updated!", 'success'); return redirect(url_for('admin_manage_sessions'))
    return render_template('edit_session.html', session=session_data)

@app.route('/admin/manage_sessions')
@admin_required
def admin_manage_sessions():
    db = get_db(); courses_with_sessions = []
    for course in db.execute('SELECT id, title FROM courses ORDER BY title').fetchall():
        course_dict = dict(course)
        course_dict['sessions'] = db.execute('SELECT * FROM sessions WHERE course_id = ? ORDER BY id', (course['id'],)).fetchall()
        courses_with_sessions.append(course_dict)
    return render_template('admin_manage_sessions.html', courses_with_sessions=courses_with_sessions)

@app.route('/admin/delete_session/<int:session_id>', methods=['POST'])
@admin_required
def admin_delete_session(session_id):
    db = get_db(); session_to_delete = db.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
    if not session_to_delete: flash('Session not found.', 'error'); return redirect(url_for('admin_manage_sessions'))
    for i in range(1, 5):
        video_url = session_to_delete[f'video{i}_url']
        if video_url and video_url.startswith('uploads/'):
            try: os.remove(os.path.join(app.root_path, 'static', video_url))
            except OSError as e: print(f"Error deleting session video: {e}")
    if session_to_delete['thumbnail_url'] and session_to_delete['thumbnail_url'].startswith('uploads/'):
        try: os.remove(os.path.join(app.root_path, 'static', session_to_delete['thumbnail_url']))
        except OSError as e: print(f"Error deleting session thumbnail: {e}")
    db.execute('DELETE FROM sessions WHERE id = ?', (session_id,)); db.commit()
    flash('Session has been deleted.', 'success')
    return redirect(url_for('admin_manage_sessions'))

@app.route('/admin/add_quiz', methods=['GET', 'POST'])
@admin_required
def admin_add_quiz():
    db = get_db(); sessions = db.execute('SELECT s.id, s.title, c.title as course_title FROM sessions s JOIN courses c ON s.course_id = c.id ORDER BY c.title, s.title').fetchall()
    if request.method == 'POST':
        sess_id = request.form['session_id']; q = request.form['question']
        opts = [request.form[f'option{i}'] for i in range(1,5)]; correct = request.form['correct_answer']
        if not all([sess_id, q] + opts + [correct]):
            flash('All quiz fields required.', 'error'); return render_template('admin_add_quiz.html', sessions=sessions)
        db.execute('INSERT INTO quizzes (session_id, question, option1, option2, option3, option4, correct_answer) VALUES (?, ?, ?, ?, ?, ?, ?)',
                   (sess_id, q, opts[0], opts[1], opts[2], opts[3], int(correct)))
        db.commit(); flash('Quiz added.', 'success'); return redirect(url_for('admin_dashboard'))
    return render_template('admin_add_quiz.html', sessions=sessions)

@app.route('/admin/grant_access', methods=['POST'])
@admin_required
def admin_grant_access():
    db = get_db(); user_id = request.form['user_id']; course_id = request.form['course_id']
    if not db.execute('SELECT 1 FROM student_course_access WHERE user_id = ? AND course_id = ?', (user_id, course_id)).fetchone():
        db.execute('INSERT INTO student_course_access (user_id, course_id) VALUES (?, ?)', (user_id, course_id)); db.commit()
        flash('Access granted.', 'success')
    else: flash('User already has access to this course.', 'info')
    return redirect(url_for('admin_manage_access', search=request.form.get('current_search', '')))

@app.route('/admin/remove_access', methods=['POST'])
@admin_required
def admin_remove_access():
    db = get_db(); user_id = request.form['user_id']; course_id = request.form['course_id']
    db.execute('DELETE FROM student_course_access WHERE user_id = ? AND course_id = ?', (user_id, course_id)); db.commit()
    flash('Access removed successfully.', 'success')
    return redirect(url_for('admin_manage_access', search=request.form.get('current_search', '')))

@app.route('/admin/access')
@admin_required
def admin_manage_access():
    db = get_db(); search_q = request.args.get('search', '')
    students_list = []
    if search_q:
        students_rows = db.execute("SELECT id, name, email, account_code FROM users WHERE is_admin = 0 AND (name LIKE ? OR email LIKE ? OR account_code LIKE ?)",
                                   (f'%{search_q}%', f'%{search_q}%', f'%{search_q}%')).fetchall()
        for student_row in students_rows:
            student_dict = dict(student_row)
            student_dict['enrolled_courses'] = db.execute("SELECT c.id, c.title FROM courses c JOIN student_course_access sca ON c.id = sca.course_id WHERE sca.user_id = ?", (student_dict['id'],)).fetchall()
            students_list.append(student_dict)
    all_courses = db.execute('SELECT id, title FROM courses ORDER BY title').fetchall()
    return render_template('admin_access.html', students=students_list, all_courses=all_courses, search_query=search_q)

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        print(f"Database not found. Initializing..."); init_db()
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        print(f"Upload folder not found. Creating..."); os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(host='0.0.0.0', port=port)

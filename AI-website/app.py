import os
import uuid
import secrets
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import joinedload
from functools import wraps

# --- APP CONFIGURATION ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a_default_secret_key_for_local_development')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# --- DATABASE MODELS (SQLAlchemy ORM) ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    account_code = db.Column(db.String(50), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    courses = db.relationship('StudentCourseAccess', back_populates='user', cascade="all, delete-orphan")

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    thumbnail_url = db.Column(db.String(200))
    status = db.Column(db.String(20), default='active', nullable=False)
    duration_weeks = db.Column(db.Integer)
    student_count = db.Column(db.Integer)
    sessions = db.relationship('Session', backref='course', lazy=True, cascade="all, delete-orphan")
    students = db.relationship('StudentCourseAccess', back_populates='course', cascade="all, delete-orphan")

class Session(db.Model):
    __tablename__ = 'sessions'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    thumbnail_url = db.Column(db.String(200))
    is_free = db.Column(db.Boolean, default=False, nullable=False)
    video1_url = db.Column(db.String(300))
    video2_url = db.Column(db.String(300))
    video3_url = db.Column(db.String(300))
    video4_url = db.Column(db.String(300))
    quizzes = db.relationship('Quiz', backref='session', lazy=True, cascade="all, delete-orphan")
    completions = db.relationship('VideoCompletion', backref='session', lazy=True, cascade="all, delete-orphan")
    quiz_attempts = db.relationship('StudentQuizAttempt', backref='session', lazy=True, cascade="all, delete-orphan")

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    option1 = db.Column(db.String(200), nullable=False)
    option2 = db.Column(db.String(200), nullable=False)
    option3 = db.Column(db.String(200), nullable=False)
    option4 = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.Integer, nullable=False)

class StudentCourseAccess(db.Model):
    __tablename__ = 'student_course_access'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    user = db.relationship('User', back_populates='courses')
    course = db.relationship('Course', back_populates='students')

class VideoCompletion(db.Model):
    __tablename__ = 'video_completions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    video_index = db.Column(db.Integer, nullable=False)

class StudentQuizAttempt(db.Model):
    __tablename__ = 'student_quiz_attempts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    attempted_on = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

# --- HOOKS & DECORATORS ---
@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = db.session.get(User, session['user_id'])

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.date.today().year}

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- SETUP COMMAND ---
@app.cli.command('init-db')
def init_db_command():
    """Creates all database tables."""
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email='admin@example.com').first():
            admin_user = User(name='Admin', email='admin@example.com', password=generate_password_hash('admin'),
                              account_code='ADMIN-001', is_admin=True)
            db.session.add(admin_user)
            db.session.commit()
            print('Created default admin user.')
    print('Initialized the database.')

# --- ROUTES ---
@app.route('/')
def index():
    courses = Course.query.order_by(Course.id).all()
    accessible_courses = set()
    if g.user:
        accessible_courses = {access.course_id for access in StudentCourseAccess.query.filter_by(user_id=g.user.id).all()}
    return render_template('index.html', courses=courses, accessible_courses=accessible_courses)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']; email = request.form['email']; password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email address already registered.', 'error'); return redirect(url_for('register'))
        new_user = User(name=name, email=email, password=generate_password_hash(password),
                        account_code=f"AI-YOUTH-{str(uuid.uuid4().hex[:6]).upper()}")
        db.session.add(new_user); db.session.commit()
        flash('Registration successful! Please log in.', 'success'); return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']; password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session.clear(); session['user_id'] = user.id; session['is_admin'] = user.is_admin
            return redirect(url_for('admin_dashboard') if user.is_admin else url_for('courses'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear(); flash('You have been logged out.', 'success'); return redirect(url_for('index'))

@app.route('/courses')
@login_required
def courses():
    all_courses = Course.query.order_by(Course.id).all()
    accessible_courses_ids = {access.course_id for access in StudentCourseAccess.query.filter_by(user_id=g.user.id).all()}
    enrolled_courses = [course for course in all_courses if course.id in accessible_courses_ids]
    other_courses = [course for course in all_courses if course.id not in accessible_courses_ids]
    return render_template('courses.html', enrolled_courses=enrolled_courses, other_courses=other_courses)

@app.route('/request_course_access/<int:course_id>')
@login_required
def request_course_access(course_id):
    course = db.session.get(Course, course_id)
    if course:
        flash(f"The course '{course.title}' requires payment. To get access, please contact us.", 'info')
    return redirect(url_for('courses'))

@app.route('/course/<int:course_id>')
@login_required
def course_detail(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        flash('Course not found.', 'error'); return redirect(url_for('courses'))
    
    has_access = StudentCourseAccess.query.filter_by(user_id=g.user.id, course_id=course_id).first() is not None
    
    progress = 0
    if has_access:
        user_completions = VideoCompletion.query.filter_by(user_id=g.user.id).all()
        g.user_completed_videos = {(comp.session_id, comp.video_index) for comp in user_completions}
        
        total_vids_course = 0; total_comp_vids_course = 0
        for sess in course.sessions:
            session_vids = [sess.video1_url, sess.video2_url, sess.video3_url, sess.video4_url]
            num_vids_in_sess = sum(1 for url in session_vids if url and url.strip())
            total_vids_course += num_vids_in_sess
            num_comp_for_this_session = VideoCompletion.query.filter_by(user_id=g.user.id, session_id=sess.id).count()
            total_comp_vids_course += num_comp_for_this_session
            sess.is_session_fully_completed = (num_vids_in_sess > 0 and num_comp_for_this_session == num_vids_in_sess)
        
        progress = (total_comp_vids_course / total_vids_course) * 100 if total_vids_course > 0 else 0
        
    return render_template('course_detail.html', course=course, sessions=course.sessions, progress=progress, has_access=has_access)

@app.route('/session/<int:session_id>/video/<int:video_index>')
@login_required
def session_detail(session_id, video_index):
    session_data = db.session.get(Session, session_id)
    if not session_data:
        flash('Session not found.', 'error'); return redirect(url_for('courses'))

    has_course_access = StudentCourseAccess.query.filter_by(user_id=g.user.id, course_id=session_data.course_id).first()
    if not session_data.is_free and not has_course_access:
        flash('You must have access to the course to view this protected session.', 'error')
        return redirect(url_for('course_detail', course_id=session_data.course_id))
    
    vid_urls = [session_data.video1_url, session_data.video2_url, session_data.video3_url, session_data.video4_url]
    valid_vids = [url for url in vid_urls if url and url.strip()]
    
    if not (1 <= video_index <= len(valid_vids)):
        flash('Invalid video number.', 'error'); return redirect(url_for('course_detail', course_id=session_data.course_id))
    
    current_video_url = valid_vids[video_index - 1]
    completion = VideoCompletion.query.filter_by(user_id=g.user.id, session_id=session_id, video_index=video_index).first()
    quizzes = Quiz.query.filter_by(session_id=session_id).all()
    
    return render_template('session_detail.html', session=session_data, current_video_url=current_video_url,
                           video_index=video_index, total_videos=len(valid_vids),
                           is_completed=(completion is not None), quizzes=quizzes)

@app.route('/session/<int:session_id>/video/<int:video_index>/mark_complete', methods=['POST'])
@login_required
def mark_video_complete(session_id, video_index):
    if not VideoCompletion.query.filter_by(user_id=g.user.id, session_id=session_id, video_index=video_index).first():
        new_completion = VideoCompletion(user_id=g.user.id, session_id=session_id, video_index=video_index)
        db.session.add(new_completion); db.session.commit()
        flash(f'Video {video_index} marked as complete!', 'success')
    return redirect(url_for('session_detail', session_id=session_id, video_index=video_index))

@app.route('/session/<int:session_id>/submit_quiz', methods=['POST'])
@login_required
def submit_quiz(session_id):
    sess = db.session.get(Session, session_id)
    if not sess: flash('Session not found.', 'error'); return redirect(url_for('courses'))
    
    score = sum(1 for quiz in sess.quizzes if request.form.get(f'quiz_{quiz.id}') and int(request.form.get(f'quiz_{quiz.id}')) == quiz.correct_answer)
    
    attempt = StudentQuizAttempt.query.filter_by(user_id=g.user.id, session_id=session_id).first()
    if attempt is None:
        new_attempt = StudentQuizAttempt(user_id=g.user.id, session_id=session_id, score=score, total_questions=len(sess.quizzes))
        db.session.add(new_attempt)
    else:
        attempt.score = score; attempt.total_questions = len(sess.quizzes); attempt.attempted_on = datetime.datetime.utcnow()
    
    db.session.commit(); flash(f'Quiz submitted! You scored {score}/{len(sess.quizzes)}.', 'success')
    return redirect(url_for('course_detail', course_id=sess.course_id))

@app.route('/session/<int:session_id>/finish_session')
@login_required
def finish_session(session_id):
    sess = db.session.get(Session, session_id)
    if not sess: flash('Session not found.', 'error'); return redirect(url_for('courses'))
    return render_template('finish_page.html', session=sess)

@app.route('/contact')
def contact(): return render_template('contact.html')

@app.route('/profile')
@login_required
def profile():
    enrolled_courses = Course.query.join(StudentCourseAccess).filter(StudentCourseAccess.user_id == g.user.id).all()
    return render_template('profile.html', user=g.user, enrolled_courses=enrolled_courses)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(16)
            expires_at = datetime.datetime.now() + datetime.timedelta(hours=1)
            new_token = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
            db.session.add(new_token); db.session.commit()
            reset_url = url_for('reset_password', token=token, _external=True)
            print(f"--- PASSWORD RESET LINK (SIMULATED EMAIL): {reset_url} ---")
        flash('If an account with that email exists, a reset link has been sent (check console).', 'info')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    token_data = PasswordResetToken.query.filter_by(token=token).filter(PasswordResetToken.expires_at > datetime.datetime.now()).first()
    if not token_data:
        flash('Password reset link is invalid or has expired.', 'error'); return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        password = request.form.get('password')
        if not password or password != request.form.get('confirm_password'):
            flash('Passwords do not match.', 'error'); return render_template('reset_password.html', token=token)
        
        user = db.session.get(User, token_data.user_id)
        user.password = generate_password_hash(password)
        db.session.delete(token_data); db.session.commit()
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
            new_course = Course(title=title, description=desc, thumbnail_url=thumb_path, status=status, duration_weeks=duration, student_count=students)
            db.session.add(new_course); db.session.commit()
            flash(f"Course '{title}' added!", 'success'); return redirect(url_for('courses'))
        else: flash('Invalid thumbnail file type.', 'error'); return redirect(request.url)
    return render_template('admin_add_course.html')

@app.route('/admin/edit_course/<int:course_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_course(course_id):
    course = db.session.get(Course, course_id)
    if not course: flash('Course not found.', 'error'); return redirect(url_for('admin_manage_courses'))
    if request.method == 'POST':
        course.title = request.form['title']; course.description = request.form['description']; course.status = request.form['status']
        course.duration_weeks = request.form.get('duration_weeks', 0, type=int); course.student_count = request.form.get('student_count', 0, type=int)
        
        if 'thumbnail' in request.files:
            file = request.files['thumbnail']
            if file and file.filename and allowed_file(file.filename):
                if course.thumbnail_url and course.thumbnail_url.startswith('uploads/'):
                    try: os.remove(os.path.join(app.root_path, 'static', course.thumbnail_url))
                    except OSError as e: print(f"Error deleting old thumbnail: {e}")
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename)); course.thumbnail_url = f'uploads/{filename}'
        
        db.session.commit()
        flash(f"Course '{course.title}' updated!", 'success'); return redirect(url_for('admin_manage_courses'))
    return render_template('edit_course.html', course=course)

@app.route('/admin/manage_courses')
@admin_required
def admin_manage_courses():
    courses = Course.query.order_by(Course.id.desc()).all()
    return render_template('admin_manage_courses.html', courses=courses)

@app.route('/admin/delete_course/<int:course_id>', methods=['POST'])
@admin_required
def admin_delete_course(course_id):
    course = db.session.get(Course, course_id)
    if not course: flash('Course not found.', 'error'); return redirect(url_for('admin_manage_courses'))
    
    if course.thumbnail_url and course.thumbnail_url.startswith('uploads/'):
        try: os.remove(os.path.join(app.root_path, 'static', course.thumbnail_url))
        except OSError as e: print(f"Error deleting course thumbnail: {e}")

    for sess in course.sessions:
        for i in range(1, 5):
            video_url = getattr(sess, f'video{i}_url')
            if video_url and video_url.startswith('uploads/'):
                try: os.remove(os.path.join(app.root_path, 'static', video_url))
                except OSError as e: print(f"Error deleting session video: {e}")
    
    db.session.delete(course); db.session.commit()
    flash('Course and all related content deleted.', 'success')
    return redirect(url_for('admin_manage_courses'))

@app.route('/admin/add_session', methods=['GET', 'POST'])
@admin_required
def admin_add_session():
    courses_list = Course.query.filter_by(status='active').order_by(Course.title).all()
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
        
        if not all([course_id, title, paths[0]]):
            flash('Course, Title, and Video 1 are required.', 'error')
        else:
            new_session = Session(course_id=int(course_id), title=title, thumbnail_url=thumb_path, is_free=is_free,
                                  video1_url=paths[0], video2_url=paths[1], video3_url=paths[2], video4_url=paths[3])
            db.session.add(new_session); db.session.commit()
            flash(f"Session '{title}' added!", 'success'); return redirect(url_for('course_detail', course_id=int(course_id)))
    return render_template('admin_add_session.html', courses=courses_list)

@app.route('/admin/edit_session/<int:session_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_session(session_id):
    sess = db.session.get(Session, session_id)
    if not sess: flash('Session not found.', 'error'); return redirect(url_for('admin_manage_sessions'))
    if request.method == 'POST':
        sess.title = request.form['title']; sess.is_free = 1 if request.form.get('is_free') == '1' else 0
        if 'thumbnail_file' in request.files:
            thumb_file = request.files['thumbnail_file']
            if thumb_file and thumb_file.filename and allowed_file(thumb_file.filename):
                if sess.thumbnail_url and sess.thumbnail_url.startswith('uploads/'):
                    try: os.remove(os.path.join(app.root_path, 'static', sess.thumbnail_url))
                    except OSError as e: print(f"Error deleting old session thumbnail: {e}")
                thumb_filename = secure_filename(thumb_file.filename)
                thumb_file.save(os.path.join(app.config['UPLOAD_FOLDER'], thumb_filename)); sess.thumbnail_url = f'uploads/{thumb_filename}'
        
        for i in range(1, 5):
            new_url = request.form.get(f'video{i}_url', '').strip(); file = request.files.get(f'video{i}_file')
            current_path = getattr(sess, f'video{i}_url')
            if file and file.filename:
                if allowed_file(file.filename):
                    if current_path and current_path.startswith('uploads/'):
                        try: os.remove(os.path.join(app.root_path, 'static', current_path))
                        except OSError as e: print(f"Error deleting old video file: {e}")
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename)); setattr(sess, f'video{i}_url', f'uploads/{filename}')
            elif new_url:
                if current_path and current_path.startswith('uploads/'):
                    try: os.remove(os.path.join(app.root_path, 'static', current_path))
                    except OSError as e: print(f"Error deleting old video file: {e}")
                setattr(sess, f'video{i}_url', new_url)
        
        db.session.commit()
        flash(f"Session '{sess.title}' updated!", 'success'); return redirect(url_for('admin_manage_sessions'))
    return render_template('edit_session.html', session=sess)

@app.route('/admin/manage_sessions')
@admin_required
def admin_manage_sessions():
    courses = Course.query.options(joinedload(Course.sessions)).order_by(Course.title).all()
    return render_template('admin_manage_sessions.html', courses_with_sessions=courses)

@app.route('/admin/delete_session/<int:session_id>', methods=['POST'])
@admin_required
def admin_delete_session(session_id):
    sess = db.session.get(Session, session_id)
    if not sess: flash('Session not found.', 'error'); return redirect(url_for('admin_manage_sessions'))
    
    for i in range(1, 5):
        video_url = getattr(sess, f'video{i}_url')
        if video_url and video_url.startswith('uploads/'):
            try: os.remove(os.path.join(app.root_path, 'static', video_url))
            except OSError as e: print(f"Error deleting session video: {e}")
    if sess.thumbnail_url and sess.thumbnail_url.startswith('uploads/'):
        try: os.remove(os.path.join(app.root_path, 'static', sess.thumbnail_url))
        except OSError as e: print(f"Error deleting session thumbnail: {e}")
    
    db.session.delete(sess); db.session.commit()
    flash('Session has been deleted.', 'success')
    return redirect(url_for('admin_manage_sessions'))

@app.route('/admin/add_quiz', methods=['GET', 'POST'])
@admin_required
def admin_add_quiz():
    sessions = Session.query.join(Course).order_by(Course.title, Session.title).all()
    if request.method == 'POST':
        sess_id = request.form['session_id']; q = request.form['question']
        opts = [request.form[f'option{i}'] for i in range(1,5)]; correct = request.form['correct_answer']
        if not all([sess_id, q] + opts + [correct]):
            flash('All quiz fields are required.', 'error'); return render_template('admin_add_quiz.html', sessions=sessions)
        new_quiz = Quiz(session_id=sess_id, question=q, option1=opts[0], option2=opts[1], option3=opts[2], option4=opts[3], correct_answer=int(correct))
        db.session.add(new_quiz); db.session.commit()
        flash('Quiz added.', 'success'); return redirect(url_for('admin_dashboard'))
    return render_template('admin_add_quiz.html', sessions=sessions)

@app.route('/admin/grant_access', methods=['POST'])
@admin_required
def admin_grant_access():
    user_id = request.form['user_id']; course_id = request.form['course_id']
    if not StudentCourseAccess.query.filter_by(user_id=user_id, course_id=course_id).first():
        new_access = StudentCourseAccess(user_id=user_id, course_id=course_id)
        db.session.add(new_access); db.session.commit()
        flash('Access granted.', 'success')
    else: flash('User already has access to this course.', 'info')
    return redirect(url_for('admin_manage_access', search=request.form.get('current_search', '')))

@app.route('/admin/remove_access', methods=['POST'])
@admin_required
def admin_remove_access():
    user_id = request.form['user_id']; course_id = request.form['course_id']
    access_record = StudentCourseAccess.query.filter_by(user_id=user_id, course_id=course_id).first()
    if access_record:
        db.session.delete(access_record); db.session.commit()
        flash('Access removed successfully.', 'success')
    return redirect(url_for('admin_manage_access', search=request.form.get('current_search', '')))

@app.route('/admin/access')
@admin_required
def admin_manage_access():
    search_q = request.args.get('search', '')
    query = User.query.filter(User.is_admin == False)
    if search_q:
        search_term = f'%{search_q}%'
        query = query.filter(db.or_(User.name.ilike(search_term), User.email.ilike(search_term), User.account_code.ilike(search_term)))
    
    students = query.options(joinedload(User.courses).joinedload(StudentCourseAccess.course)).all()
    all_courses = Course.query.order_by(Course.title).all()
    
    return render_template('admin_access.html', students=students, all_courses=all_courses, search_query=search_q)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False) # Set to False for production

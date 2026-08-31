import os
import re
import uuid
from datetime import datetime, date
from functools import wraps
from pathlib import Path

from flask import (
    Flask, render_template, redirect, url_for, flash, request,
    abort
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect, CSRFError
from dotenv import load_dotenv
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix
from storage import storage
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

ALLOWED_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "webp",
    "doc", "docx", "ppt", "pptx",
    "xls", "xlsx", "txt", "zip"
}

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "dev-secret-key-change-before-production"
)

database_url = os.environ.get("DATABASE_URL", "sqlite:///korepetycje.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

is_production = os.environ.get("APP_ENV", "development").lower() == "production"
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=is_production,
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_SAMESITE="Lax",
    REMEMBER_COOKIE_SECURE=is_production,
    WTF_CSRF_SSL_STRICT=is_production,
)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Zaloguj się, aby przejść dalej."
login_manager.login_message_category = "warning"


# ============================================================
# MODELE
# ============================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")

    assignments = db.relationship(
        "Assignment",
        backref="student",
        lazy=True,
        cascade="all, delete-orphan"
    )

    materials = db.relationship(
        "Material",
        backref="student",
        lazy=True,
        cascade="all, delete-orphan"
    )

    tips = db.relationship(
        "Tip",
        backref="student",
        lazy=True,
        cascade="all, delete-orphan"
    )

    videos = db.relationship(
        "Video",
        backref="student",
        lazy=True,
        cascade="all, delete-orphan"
    )

    archive_record = db.relationship(
        "StudentArchive",
        backref="student",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_archived(self):
        return self.archive_record is not None


class StudentArchive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        unique=True
    )
    archived_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    is_done = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    submission = db.relationship(
        "Submission",
        backref="assignment",
        uselist=False,
        cascade="all, delete-orphan"
    )

    @property
    def status(self):
        if self.submission is None:
            return "Do zrobienia"

        if self.submission.checked_at:
            return "Sprawdzone"

        return "Przesłane"

    @property
    def is_overdue(self):
        return (
            self.due_date is not None
            and self.due_date < date.today()
            and self.status == "Do zrobienia"
        )


class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    answer_text = db.Column(db.Text, nullable=True)

    original_filename = db.Column(db.String(255), nullable=True)
    stored_filename = db.Column(db.String(255), nullable=True)

    teacher_comment = db.Column(db.Text, nullable=True)

    submitted_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    checked_at = db.Column(db.DateTime, nullable=True)

    assignment_id = db.Column(
        db.Integer,
        db.ForeignKey("assignment.id"),
        nullable=False,
        unique=True
    )


class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )


class Tip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(500), nullable=False)
    embed_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )


# ============================================================
# POMOCNICZE
# ============================================================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def teacher_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()

        if current_user.role != "teacher":
            abort(403)

        return view_func(*args, **kwargs)

    return wrapped


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def valid_subject(subject):
    return subject in {"Matematyka", "Geografia"}


def get_student_or_404(student_id):
    student = db.get_or_404(User, student_id)

    if student.role != "student":
        abort(404)

    return student


def youtube_embed_url(url):
    patterns = [
        r"(?:youtube\.com/watch\?v=)([A-Za-z0-9_-]{6,})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{6,})",
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{6,})",
        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{6,})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return f"https://www.youtube.com/embed/{match.group(1)}"

    return None


def student_content(student_id):
    assignments = (
        Assignment.query
        .filter_by(student_id=student_id)
        .order_by(Assignment.due_date.asc(), Assignment.created_at.desc())
        .all()
    )

    materials = (
        Material.query
        .filter_by(student_id=student_id)
        .order_by(Material.uploaded_at.desc())
        .all()
    )

    tips = (
        Tip.query
        .filter_by(student_id=student_id)
        .order_by(Tip.created_at.desc())
        .all()
    )

    videos = (
        Video.query
        .filter_by(student_id=student_id)
        .order_by(Video.created_at.desc())
        .all()
    )

    return assignments, materials, tips, videos


def save_uploaded_file(file, key_prefix):
    original_filename = secure_filename(file.filename)
    extension = original_filename.rsplit(".", 1)[1].lower()
    stored_filename = f"{uuid.uuid4().hex}.{extension}"

    key = f"{key_prefix.strip('/')}/{stored_filename}"
    storage.save(
        file,
        key,
        download_name=original_filename
    )

    return original_filename, stored_filename


def material_storage_key(student_id, subject, stored_filename):
    return (
        f"{student_id}/"
        f"{subject.lower()}/"
        f"{stored_filename}"
    )


def submission_storage_key(student_id, stored_filename):
    return f"submissions/{student_id}/{stored_filename}"


# ============================================================
# STRONA I LOGOWANIE
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "ok",
            "storage": storage.backend,
        }, 200
    except Exception:
        return {
            "status": "error",
            "database": "unavailable",
        }, 503


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if user.role == "student" and user.is_archived:
                flash(
                    "To konto jest obecnie zarchiwizowane. Skontaktuj się z nauczycielem.",
                    "warning"
                )
                return render_template("login.html")

            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Nieprawidłowy e-mail lub hasło.", "danger")

    return render_template("login.html")


@app.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Wylogowano.", "success")
    return redirect(url_for("index"))


@app.route("/panel")
@login_required
def dashboard():
    if current_user.role == "teacher":
        return redirect(url_for("teacher_dashboard"))

    if current_user.is_archived:
        logout_user()
        flash("Twoje konto zostało zarchiwizowane.", "warning")
        return redirect(url_for("login"))

    return redirect(url_for("student_dashboard"))


# ============================================================
# PANEL UCZNIA
# ============================================================

@app.route("/uczen")
@login_required
def student_dashboard():
    if current_user.role != "student":
        return redirect(url_for("teacher_dashboard"))

    if current_user.is_archived:
        logout_user()
        flash("Twoje konto zostało zarchiwizowane.", "warning")
        return redirect(url_for("login"))

    assignments, materials, tips, videos = student_content(current_user.id)

    return render_template(
        "student_dashboard.html",
        assignments=assignments,
        materials=materials,
        tips=tips,
        videos=videos,
    )


@app.route("/zadanie/<int:assignment_id>/oddaj", methods=["GET", "POST"])
@login_required
def submit_assignment(assignment_id):
    assignment = db.get_or_404(Assignment, assignment_id)

    if current_user.role != "student" or assignment.student_id != current_user.id:
        abort(403)

    if request.method == "POST":
        answer_text = request.form.get("answer_text", "").strip()
        file = request.files.get("file")

        if not answer_text and (not file or not file.filename):
            flash("Dodaj opis rozwiązania albo załącz plik.", "danger")
            return render_template(
                "submit_assignment.html",
                assignment=assignment
            )

        submission = assignment.submission

        if not submission:
            submission = Submission(
                assignment_id=assignment.id
            )
            db.session.add(submission)

        submission.answer_text = answer_text
        submission.submitted_at = datetime.utcnow()
        submission.checked_at = None
        submission.teacher_comment = None

        if file and file.filename:
            if not allowed_file(file.filename):
                flash("Ten format pliku nie jest obsługiwany.", "danger")
                return render_template(
                    "submit_assignment.html",
                    assignment=assignment
                )

            if submission.stored_filename:
                storage.delete(
                    submission_storage_key(
                        current_user.id,
                        submission.stored_filename
                    )
                )

            original_filename, stored_filename = save_uploaded_file(
                file,
                f"submissions/{current_user.id}"
            )

            submission.original_filename = original_filename
            submission.stored_filename = stored_filename

        db.session.commit()

        flash("Praca została przesłana do sprawdzenia.", "success")
        return redirect(url_for("student_dashboard"))

    return render_template(
        "submit_assignment.html",
        assignment=assignment
    )


@app.route("/oddana-praca/<int:submission_id>/pobierz")
@login_required
def download_submission(submission_id):
    submission = db.get_or_404(Submission, submission_id)
    assignment = submission.assignment

    allowed = (
        current_user.role == "teacher"
        or (
            current_user.role == "student"
            and assignment.student_id == current_user.id
        )
    )

    if not allowed:
        abort(403)

    if not submission.stored_filename:
        abort(404)

    key = submission_storage_key(
        assignment.student_id,
        submission.stored_filename
    )

    response = storage.download_response(
        key,
        submission.original_filename
    )

    if response is None:
        abort(404)

    return response


# ============================================================
# PANEL NAUCZYCIELA
# ============================================================

@app.route("/nauczyciel")
@teacher_required
def teacher_dashboard():
    students = (
        User.query
        .filter_by(role="student")
        .order_by(User.name.asc())
        .all()
    )

    active_students = [s for s in students if not s.is_archived]
    archived_students = [s for s in students if s.is_archived]

    all_assignments = Assignment.query.all()
    waiting_review = sum(
        1 for a in all_assignments
        if a.submission and not a.submission.checked_at
    )
    overdue = sum(1 for a in all_assignments if a.is_overdue)

    return render_template(
        "teacher_dashboard.html",
        active_students=active_students,
        archived_students=archived_students,
        waiting_review=waiting_review,
        overdue=overdue,
    )


@app.route("/nauczyciel/uczen/nowy", methods=["GET", "POST"])
@teacher_required
def add_student():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Uzupełnij wszystkie pola.", "danger")
            return render_template("student_form.html", mode="add")

        if len(password) < 8:
            flash("Hasło powinno mieć co najmniej 8 znaków.", "danger")
            return render_template("student_form.html", mode="add")

        if User.query.filter_by(email=email).first():
            flash("Konto z takim adresem e-mail już istnieje.", "danger")
            return render_template("student_form.html", mode="add")

        student = User(name=name, email=email, role="student")
        student.set_password(password)

        db.session.add(student)
        db.session.commit()

        flash("Uczeń został dodany.", "success")
        return redirect(url_for("teacher_dashboard"))

    return render_template("student_form.html", mode="add")


@app.route("/nauczyciel/uczen/<int:student_id>")
@teacher_required
def student_detail(student_id):
    student = get_student_or_404(student_id)
    assignments, materials, tips, videos = student_content(student.id)

    waiting_review = sum(
        1 for a in assignments
        if a.submission and not a.submission.checked_at
    )

    return render_template(
        "student_detail.html",
        student=student,
        assignments=assignments,
        materials=materials,
        tips=tips,
        videos=videos,
        waiting_review=waiting_review,
    )


@app.route("/nauczyciel/uczen/<int:student_id>/edytuj", methods=["GET", "POST"])
@teacher_required
def edit_student(student_id):
    student = get_student_or_404(student_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()

        if not name or not email:
            flash("Uzupełnij imię i e-mail.", "danger")
            return render_template(
                "student_form.html",
                mode="edit",
                student=student
            )

        other = User.query.filter(
            User.email == email,
            User.id != student.id
        ).first()

        if other:
            flash("Inne konto używa już tego adresu e-mail.", "danger")
            return render_template(
                "student_form.html",
                mode="edit",
                student=student
            )

        student.name = name
        student.email = email
        db.session.commit()

        flash("Dane ucznia zostały zaktualizowane.", "success")
        return redirect(url_for("student_detail", student_id=student.id))

    return render_template(
        "student_form.html",
        mode="edit",
        student=student
    )


@app.route("/nauczyciel/uczen/<int:student_id>/haslo", methods=["GET", "POST"])
@teacher_required
def reset_student_password(student_id):
    student = get_student_or_404(student_id)

    if request.method == "POST":
        password = request.form.get("password", "")

        if len(password) < 8:
            flash("Hasło powinno mieć co najmniej 8 znaków.", "danger")
            return render_template(
                "reset_password.html",
                student=student
            )

        student.set_password(password)
        db.session.commit()

        flash("Hasło ucznia zostało zmienione.", "success")
        return redirect(url_for("student_detail", student_id=student.id))

    return render_template(
        "reset_password.html",
        student=student
    )


@app.post("/nauczyciel/uczen/<int:student_id>/archiwizuj")
@teacher_required
def archive_student(student_id):
    student = get_student_or_404(student_id)

    if not student.archive_record:
        db.session.add(StudentArchive(student_id=student.id))
        db.session.commit()

    flash("Uczeń został zarchiwizowany.", "success")
    return redirect(url_for("teacher_dashboard"))


@app.post("/nauczyciel/uczen/<int:student_id>/przywroc")
@teacher_required
def restore_student(student_id):
    student = get_student_or_404(student_id)

    if student.archive_record:
        db.session.delete(student.archive_record)
        db.session.commit()

    flash("Uczeń został przywrócony.", "success")
    return redirect(url_for("teacher_dashboard"))


@app.post("/nauczyciel/uczen/<int:student_id>/usun")
@teacher_required
def delete_student(student_id):
    student = get_student_or_404(student_id)

    # Usuwamy pliki materiałów i oddanych prac.
    for material in list(student.materials):
        storage.delete(
            material_storage_key(
                student.id,
                material.subject,
                material.stored_filename
            )
        )

    for assignment in list(student.assignments):
        if assignment.submission and assignment.submission.stored_filename:
            storage.delete(
                submission_storage_key(
                    student.id,
                    assignment.submission.stored_filename
                )
            )

    db.session.delete(student)
    db.session.commit()

    flash("Konto ucznia zostało trwale usunięte.", "success")
    return redirect(url_for("teacher_dashboard"))


# ============================================================
# ZADANIA
# ============================================================

@app.route(
    "/nauczyciel/uczen/<int:student_id>/zadanie/nowe",
    methods=["GET", "POST"]
)
@teacher_required
def add_assignment(student_id):
    student = get_student_or_404(student_id)

    if request.method == "POST":
        return save_assignment_form(student, None)

    return render_template(
        "assignment_form.html",
        student=student,
        assignment=None
    )


@app.route(
    "/nauczyciel/zadanie/<int:assignment_id>/edytuj",
    methods=["GET", "POST"]
)
@teacher_required
def edit_assignment(assignment_id):
    assignment = db.get_or_404(Assignment, assignment_id)
    student = assignment.student

    if request.method == "POST":
        return save_assignment_form(student, assignment)

    return render_template(
        "assignment_form.html",
        student=student,
        assignment=assignment
    )


def save_assignment_form(student, assignment):
    subject = request.form.get("subject", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    due_date_raw = request.form.get("due_date", "").strip()

    if not valid_subject(subject):
        flash("Wybierz poprawny przedmiot.", "danger")
        return render_template(
            "assignment_form.html",
            student=student,
            assignment=assignment
        )

    if not title:
        flash("Podaj tytuł zadania.", "danger")
        return render_template(
            "assignment_form.html",
            student=student,
            assignment=assignment
        )

    due_date = None
    if due_date_raw:
        try:
            due_date = datetime.strptime(due_date_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Niepoprawna data.", "danger")
            return render_template(
                "assignment_form.html",
                student=student,
                assignment=assignment
            )

    if assignment is None:
        assignment = Assignment(student_id=student.id)
        db.session.add(assignment)

    assignment.subject = subject
    assignment.title = title
    assignment.description = description
    assignment.due_date = due_date

    db.session.commit()

    flash("Zadanie zostało zapisane.", "success")
    return redirect(url_for("student_detail", student_id=student.id))


@app.post("/nauczyciel/zadanie/<int:assignment_id>/usun")
@teacher_required
def delete_assignment(assignment_id):
    assignment = db.get_or_404(Assignment, assignment_id)
    student_id = assignment.student_id

    if assignment.submission and assignment.submission.stored_filename:
        storage.delete(
            submission_storage_key(
                student_id,
                assignment.submission.stored_filename
            )
        )

    db.session.delete(assignment)
    db.session.commit()

    flash("Zadanie zostało usunięte.", "success")
    return redirect(url_for("student_detail", student_id=student_id))


@app.route(
    "/nauczyciel/zadanie/<int:assignment_id>/sprawdz",
    methods=["GET", "POST"]
)
@teacher_required
def review_submission(assignment_id):
    assignment = db.get_or_404(Assignment, assignment_id)

    if not assignment.submission:
        flash("Uczeń nie przesłał jeszcze rozwiązania.", "warning")
        return redirect(
            url_for("student_detail", student_id=assignment.student_id)
        )

    submission = assignment.submission

    if request.method == "POST":
        comment = request.form.get("teacher_comment", "").strip()
        action = request.form.get("action", "save")

        submission.teacher_comment = comment

        if action == "checked":
            submission.checked_at = datetime.utcnow()
            flash("Praca została oznaczona jako sprawdzona.", "success")
        else:
            submission.checked_at = None
            flash("Komentarz został zapisany.", "success")

        db.session.commit()

        return redirect(
            url_for("student_detail", student_id=assignment.student_id)
        )

    return render_template(
        "review_submission.html",
        assignment=assignment,
        submission=submission
    )


# ============================================================
# MATERIAŁY
# ============================================================

@app.route(
    "/nauczyciel/uczen/<int:student_id>/material/nowy",
    methods=["GET", "POST"]
)
@teacher_required
def add_material(student_id):
    student = get_student_or_404(student_id)

    if request.method == "POST":
        return save_material_form(student, None)

    return render_template(
        "material_form.html",
        student=student,
        material=None
    )


@app.route(
    "/nauczyciel/material/<int:material_id>/edytuj",
    methods=["GET", "POST"]
)
@teacher_required
def edit_material(material_id):
    material = db.get_or_404(Material, material_id)
    student = material.student

    if request.method == "POST":
        return save_material_form(student, material)

    return render_template(
        "material_form.html",
        student=student,
        material=material
    )


def save_material_form(student, material):
    subject = request.form.get("subject", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    file = request.files.get("file")

    if not valid_subject(subject):
        flash("Wybierz poprawny przedmiot.", "danger")
        return render_template(
            "material_form.html",
            student=student,
            material=material
        )

    if not title:
        flash("Podaj tytuł materiału.", "danger")
        return render_template(
            "material_form.html",
            student=student,
            material=material
        )

    if material is None and (not file or not file.filename):
        flash("Wybierz plik.", "danger")
        return render_template(
            "material_form.html",
            student=student,
            material=material
        )

    old_key = None
    old_subject = None

    if material is None:
        material = Material(
            student_id=student.id,
            original_filename="",
            stored_filename=""
        )
        db.session.add(material)
    else:
        old_subject = material.subject
        old_key = material_storage_key(
            student.id,
            material.subject,
            material.stored_filename
        )

    if file and file.filename:
        if not allowed_file(file.filename):
            flash("Ten format pliku nie jest obsługiwany.", "danger")
            return render_template(
                "material_form.html",
                student=student,
                material=material
            )

        original_filename, stored_filename = save_uploaded_file(
            file,
            f"{student.id}/{subject.lower()}"
        )

        if old_key:
            storage.delete(old_key)

        material.original_filename = original_filename
        material.stored_filename = stored_filename

    elif old_key and old_subject != subject:
        new_key = material_storage_key(
            student.id,
            subject,
            material.stored_filename
        )
        storage.move(old_key, new_key)

    material.subject = subject
    material.title = title
    material.description = description

    db.session.commit()

    flash("Materiał został zapisany.", "success")
    return redirect(url_for("student_detail", student_id=student.id))


@app.route("/material/<int:material_id>/pobierz")
@login_required
def download_material(material_id):
    material = db.get_or_404(Material, material_id)

    if current_user.role == "student" and material.student_id != current_user.id:
        abort(403)

    if current_user.role not in {"student", "teacher"}:
        abort(403)

    key = material_storage_key(
        material.student_id,
        material.subject,
        material.stored_filename
    )

    response = storage.download_response(
        key,
        material.original_filename
    )

    if response is None:
        abort(404)

    return response


@app.post("/nauczyciel/material/<int:material_id>/usun")
@teacher_required
def delete_material(material_id):
    material = db.get_or_404(Material, material_id)
    student_id = material.student_id

    storage.delete(
        material_storage_key(
            material.student_id,
            material.subject,
            material.stored_filename
        )
    )

    db.session.delete(material)
    db.session.commit()

    flash("Materiał został usunięty.", "success")
    return redirect(url_for("student_detail", student_id=student_id))


# ============================================================
# WSKAZÓWKI
# ============================================================

@app.route(
    "/nauczyciel/uczen/<int:student_id>/wskazowka/nowa",
    methods=["GET", "POST"]
)
@teacher_required
def add_tip(student_id):
    student = get_student_or_404(student_id)

    if request.method == "POST":
        return save_tip_form(student, None)

    return render_template(
        "tip_form.html",
        student=student,
        tip=None
    )


@app.route(
    "/nauczyciel/wskazowka/<int:tip_id>/edytuj",
    methods=["GET", "POST"]
)
@teacher_required
def edit_tip(tip_id):
    tip = db.get_or_404(Tip, tip_id)
    student = tip.student

    if request.method == "POST":
        return save_tip_form(student, tip)

    return render_template(
        "tip_form.html",
        student=student,
        tip=tip
    )


def save_tip_form(student, tip):
    subject = request.form.get("subject", "").strip()
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if not valid_subject(subject):
        flash("Wybierz poprawny przedmiot.", "danger")
        return render_template("tip_form.html", student=student, tip=tip)

    if not title or not content:
        flash("Podaj tytuł i treść wskazówki.", "danger")
        return render_template("tip_form.html", student=student, tip=tip)

    if tip is None:
        tip = Tip(student_id=student.id)
        db.session.add(tip)

    tip.subject = subject
    tip.title = title
    tip.content = content

    db.session.commit()

    flash("Wskazówka została zapisana.", "success")
    return redirect(url_for("student_detail", student_id=student.id))


@app.post("/nauczyciel/wskazowka/<int:tip_id>/usun")
@teacher_required
def delete_tip(tip_id):
    tip = db.get_or_404(Tip, tip_id)
    student_id = tip.student_id

    db.session.delete(tip)
    db.session.commit()

    flash("Wskazówka została usunięta.", "success")
    return redirect(url_for("student_detail", student_id=student_id))


# ============================================================
# FILMY
# ============================================================

@app.route(
    "/nauczyciel/uczen/<int:student_id>/film/nowy",
    methods=["GET", "POST"]
)
@teacher_required
def add_video(student_id):
    student = get_student_or_404(student_id)

    if request.method == "POST":
        return save_video_form(student, None)

    return render_template(
        "video_form.html",
        student=student,
        video=None
    )


@app.route(
    "/nauczyciel/film/<int:video_id>/edytuj",
    methods=["GET", "POST"]
)
@teacher_required
def edit_video(video_id):
    video = db.get_or_404(Video, video_id)
    student = video.student

    if request.method == "POST":
        return save_video_form(student, video)

    return render_template(
        "video_form.html",
        student=student,
        video=video
    )


def save_video_form(student, video):
    subject = request.form.get("subject", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    url = request.form.get("url", "").strip()

    if not valid_subject(subject):
        flash("Wybierz poprawny przedmiot.", "danger")
        return render_template("video_form.html", student=student, video=video)

    if not title or not url:
        flash("Podaj tytuł i link do filmu.", "danger")
        return render_template("video_form.html", student=student, video=video)

    if video is None:
        video = Video(student_id=student.id)
        db.session.add(video)

    video.subject = subject
    video.title = title
    video.description = description
    video.url = url
    video.embed_url = youtube_embed_url(url)

    db.session.commit()

    flash("Film został zapisany.", "success")
    return redirect(url_for("student_detail", student_id=student.id))


@app.post("/nauczyciel/film/<int:video_id>/usun")
@teacher_required
def delete_video(video_id):
    video = db.get_or_404(Video, video_id)
    student_id = video.student_id

    db.session.delete(video)
    db.session.commit()

    flash("Film został usunięty.", "success")
    return redirect(url_for("student_detail", student_id=student_id))


# ============================================================
# BŁĘDY
# ============================================================

@app.errorhandler(CSRFError)
def handle_csrf_error(_error):
    flash(
        "Sesja formularza wygasła. Odśwież stronę i spróbuj ponownie.",
        "warning"
    )
    return redirect(request.referrer or url_for("index"))


@app.errorhandler(403)
def forbidden(_error):
    return render_template(
        "error.html",
        code=403,
        message="Brak dostępu do tej strony."
    ), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template(
        "error.html",
        code=404,
        message="Nie znaleziono strony."
    ), 404


@app.errorhandler(413)
def file_too_large(_error):
    flash("Plik jest za duży. Maksymalny rozmiar to 25 MB.", "danger")
    return redirect(request.referrer or url_for("dashboard"))



if __name__ == "__main__":
    app.run(debug=True)

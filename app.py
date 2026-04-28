# =========================
# IMPORTS
# =========================
import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet

# =========================
# APP CONFIGURATION
# =========================
app = Flask(__name__)

# Secret key used for session management.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or Fernet.generate_key().decode(
    "utf-8"
)

# SQLite database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cloudvault.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db = SQLAlchemy(app)

# =========================
# FILE UPLOAD CONFIGURATION
# =========================
UPLOAD_FOLDER = "uploads"  # Directory where encrypted files are stored
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "docx"}  # Allowed file types
MAX_FILE_SIZE = 2 * 1024 * 1024  # Max file size: 2 MB

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# Helper function to validate file extensions
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# =========================
# ENCRYPTION SETUP
# =========================
# NOTE: This generates a new key each time the app runs.
# This means previously uploaded files CANNOT be decrypted after restart.
# Future improvement: store key in environment variable or secure storage.
ENCRYPTION_KEY = Fernet.generate_key()
cipher = Fernet(ENCRYPTION_KEY)


# =========================
# LOGIN MANAGER SETUP
# =========================
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


# =========================
# DATABASE MODELS
# =========================


# User model for authentication and role management
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="user")  # 'user' or 'admin'


# File metadata model
class FileRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)  # Original filename
    stored_filename = db.Column(db.String(200), nullable=False)  # Encrypted file name
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    upload_time = db.Column(db.DateTime, default=db.func.current_timestamp())
    encrypted = db.Column(db.Boolean, default=True)


# Model for access requests between users
class AccessRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("file_record.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    status = db.Column(db.String(20), default="Pending")  # Pending, Approved, Denied


# =========================
# USER SESSION HANDLING
# =========================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =========================
# ROUTES - AUTHENTICATION
# =========================


@app.route("/")
def home():
    return render_template("home.html")


# User registration
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        # Validate input
        if not username or not email or not password:
            flash("All fields are required.")
            return redirect(url_for("register"))

        # Prevent duplicate users
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            flash("Username or email already exists.")
            return redirect(url_for("register"))

        # Hash password before storing
        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username, email=email, password=hashed_password, role="user"
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Account created. Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


# User login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        # Validate credentials
        if not user or not check_password_hash(user.password, password):
            flash("Invalid username or password.")
            return redirect(url_for("login"))

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("login.html")


# Logout route
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.")
    return redirect(url_for("login"))


# =========================
# ROUTES - DASHBOARD
# =========================
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/account")
@login_required
def account():
    uploaded_count = FileRecord.query.filter_by(owner_id=current_user.id).count()
    request_count = AccessRequest.query.filter_by(user_id=current_user.id).count()
    approved_count = AccessRequest.query.filter_by(
        user_id=current_user.id, status="Approved"
    ).count()
    pending_count = AccessRequest.query.filter_by(
        user_id=current_user.id, status="Pending"
    ).count()

    return render_template(
        "account.html",
        uploaded_count=uploaded_count,
        request_count=request_count,
        approved_count=approved_count,
        pending_count=pending_count,
    )


# =========================
# ROUTES - FILE UPLOAD
# =========================
@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    allowed_extensions = sorted(ALLOWED_EXTENSIONS)
    max_file_size_mb = MAX_FILE_SIZE // (1024 * 1024)

    if request.method == "POST":
        uploaded_file = request.files.get("file")

        # Validate file presence
        if not uploaded_file or uploaded_file.filename == "":
            flash("Please select a file before uploading.", "error")
            return redirect(url_for("upload"))

        filename = secure_filename(uploaded_file.filename)

        # Validate file type
        if not allowed_file(filename):
            flash(
                f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}.',
                "error",
            )
            return redirect(url_for("upload"))

        file_data = uploaded_file.read()

        # Validate file size/content
        if len(file_data) == 0:
            flash(
                "Empty files are not allowed. Please choose a file with content.",
                "error",
            )
            return redirect(url_for("upload"))

        if len(file_data) > MAX_FILE_SIZE:
            flash(f"File is too large. Max size is {max_file_size_mb} MB.", "error")
            return redirect(url_for("upload"))

        # Encrypt file before saving
        encrypted_data = cipher.encrypt(file_data)

        # Create unique stored filename
        stored_filename = f"{current_user.id}_{filename}.enc"
        file_path = os.path.join(UPLOAD_FOLDER, stored_filename)

        # Save encrypted file to disk
        with open(file_path, "wb") as f:
            f.write(encrypted_data)

        # Save metadata to database
        file_record = FileRecord(
            filename=filename, stored_filename=stored_filename, owner_id=current_user.id
        )

        db.session.add(file_record)
        db.session.commit()

        flash(f'"{filename}" uploaded and encrypted successfully.', "success")
        return redirect(url_for("my_files"))

    return render_template(
        "upload.html",
        allowed_extensions=allowed_extensions,
        max_file_size_mb=max_file_size_mb,
    )


# =========================
# ROUTES - FILE MANAGEMENT
# =========================


# Show only files owned by current user
@app.route("/my-files")
@login_required
def my_files():
    files = FileRecord.query.filter_by(owner_id=current_user.id).all()
    return render_template("my_files.html", files=files)


# Download your own file (decrypts before sending)
@app.route("/download/<int:file_id>")
@login_required
def download_file(file_id):
    file_record = FileRecord.query.get_or_404(file_id)

    # Ensure user owns the file
    if file_record.owner_id != current_user.id:
        flash("You are not allowed to download this file.")
        return redirect(url_for("my_files"))

    encrypted_path = os.path.join(UPLOAD_FOLDER, file_record.stored_filename)

    # Read encrypted file
    with open(encrypted_path, "rb") as f:
        encrypted_data = f.read()

    # Decrypt file
    decrypted_data = cipher.decrypt(encrypted_data)

    # Write temp decrypted file
    temp_path = os.path.join(UPLOAD_FOLDER, "decrypted_" + file_record.filename)

    with open(temp_path, "wb") as f:
        f.write(decrypted_data)

    # Send file to user
    return send_file(temp_path, as_attachment=True, download_name=file_record.filename)


@app.route("/delete-file/<int:file_id>", methods=["POST"])
@login_required
def delete_file(file_id):
    file_record = FileRecord.query.get_or_404(file_id)

    # Ensure users can only delete their own files.
    if file_record.owner_id != current_user.id:
        flash("You are not allowed to delete this file.", "error")
        return redirect(url_for("my_files"))

    encrypted_path = os.path.join(UPLOAD_FOLDER, file_record.stored_filename)

    if os.path.exists(encrypted_path):
        os.remove(encrypted_path)

    AccessRequest.query.filter_by(file_id=file_record.id).delete()
    db.session.delete(file_record)
    db.session.commit()

    flash(f'"{file_record.filename}" was deleted successfully.', "success")
    return redirect(url_for("my_files"))


# =========================
# ROUTES - ACCESS REQUESTS
# =========================


# Request access to other users' files
@app.route("/request-access", methods=["GET", "POST"])
@login_required
def request_access():
    files = FileRecord.query.all()

    if request.method == "POST":
        file_id = request.form.get("file_id")

        new_request = AccessRequest(file_id=file_id, user_id=current_user.id)

        db.session.add(new_request)
        db.session.commit()

        flash("Access request submitted.")
        return redirect(url_for("dashboard"))

    return render_template("request_access.html", files=files)


# Admin approves request
@app.route("/approve/<int:request_id>")
@login_required
def approve_request(request_id):
    if current_user.role != "admin":
        return redirect(url_for("dashboard"))

    req = AccessRequest.query.get_or_404(request_id)
    req.status = "Approved"
    db.session.commit()

    return redirect(url_for("admin"))


# Admin denies request
@app.route("/deny/<int:request_id>")
@login_required
def deny_request(request_id):
    if current_user.role != "admin":
        return redirect(url_for("dashboard"))

    req = AccessRequest.query.get_or_404(request_id)
    req.status = "Denied"
    db.session.commit()

    return redirect(url_for("admin"))


# =========================
# ROUTES - ADMIN
# =========================
@app.route("/admin")
@login_required
def admin():
    if current_user.role != "admin":
        flash("Admin access only.")
        return redirect(url_for("dashboard"))

    users = User.query.all()
    requests = AccessRequest.query.all()

    request_data = []
    for req in requests:
        requester = User.query.get(req.user_id)
        file_record = FileRecord.query.get(req.file_id)
        owner = User.query.get(file_record.owner_id) if file_record else None

        request_data.append(
            {
                "id": req.id,
                "status": req.status,
                "requester_name": requester.username if requester else "Unknown user",
                "requester_email": requester.email if requester else "",
                "file_name": file_record.filename if file_record else "Deleted file",
                "file_owner": owner.username if owner else "Unknown owner",
            }
        )

    return render_template("admin.html", users=users, requests=request_data)


# =========================
# ROUTES - USER REQUESTS
# =========================
@app.route("/my-requests")
@login_required
def my_requests():
    requests = AccessRequest.query.filter_by(user_id=current_user.id).all()

    request_data = []
    for req in requests:
        file = FileRecord.query.get(req.file_id)
        request_data.append(
            {
                "id": req.id,
                "file_name": file.filename if file else "Unknown",
                "status": req.status,
            }
        )

    return render_template("my_requests.html", requests=request_data)


# Download file via approved access request
@app.route("/download-request/<int:request_id>")
@login_required
def download_request(request_id):
    access_request = AccessRequest.query.get_or_404(request_id)

    if access_request.user_id != current_user.id:
        flash("You are not allowed to access this request.")
        return redirect(url_for("dashboard"))

    if access_request.status != "Approved":
        flash("This request is not approved yet.")
        return redirect(url_for("my_requests"))

    file_record = FileRecord.query.get_or_404(access_request.file_id)
    encrypted_path = os.path.join(UPLOAD_FOLDER, file_record.stored_filename)

    with open(encrypted_path, "rb") as f:
        encrypted_data = f.read()

    decrypted_data = cipher.decrypt(encrypted_data)

    temp_path = os.path.join(UPLOAD_FOLDER, "decrypted_" + file_record.filename)

    with open(temp_path, "wb") as f:
        f.write(decrypted_data)

    return send_file(temp_path, as_attachment=True, download_name=file_record.filename)


# =========================
# APP ENTRY POINT
# =========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # Create default admin user if not exists
        admin_user = User.query.filter_by(username="admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@cloudvault.com",
                password=generate_password_hash("admin123"),
                role="admin",
            )
            db.session.add(admin_user)
            db.session.commit()

    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")

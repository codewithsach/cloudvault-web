import io
import os
import shutil
import sys
from types import SimpleNamespace
from uuid import uuid4
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app as app_module  # noqa: E402
from app import AccessRequest, FileRecord, User, db  # noqa: E402


@pytest.fixture
def app(request, monkeypatch):
    test_root = ROOT / "tests" / "_tmp" / f"{request.node.name}_{uuid4().hex}"
    database_path = test_root / "cloudvault-test.db"
    upload_path = test_root / "uploads"
    upload_path.mkdir(parents=True)

    app_module.app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
        WTF_CSRF_ENABLED=False,
    )
    monkeypatch.setattr(app_module, "UPLOAD_FOLDER", str(upload_path))

    with app_module.app.app_context():
        db.drop_all()
        db.create_all()
        yield app_module.app
        db.session.remove()
        db.drop_all()
    shutil.rmtree(test_root, ignore_errors=True)


@pytest.fixture
def client(app):
    return app.test_client()


def _create_user(username, email, password="password123", role="user"):
    user = User(
        username=username,
        email=email,
        password=generate_password_hash(password),
        role=role,
    )
    db.session.add(user)
    db.session.commit()
    return SimpleNamespace(
        id=user.id,
        username=user.username,
        email=user.email,
        password=password,
        role=user.role,
    )


@pytest.fixture
def normal_user(app):
    with app.app_context():
        return _create_user("alice", "alice@example.com")


@pytest.fixture
def second_user(app):
    with app.app_context():
        return _create_user("bob", "bob@example.com")


@pytest.fixture
def admin_user(app):
    with app.app_context():
        return _create_user("admin", "admin@example.com", role="admin")


@pytest.fixture
def login(client):
    def _login(username, password="password123", follow_redirects=True):
        return client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=follow_redirects,
        )

    return _login


@pytest.fixture
def uploaded_file(app, client, normal_user, login):
    login(normal_user.username)
    response = client.post(
        "/upload",
        data={"file": (io.BytesIO(b"secret file content"), "notes.txt")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        file_record = FileRecord.query.filter_by(owner_id=normal_user.id).one()
        encrypted_path = os.path.join(
            app_module.UPLOAD_FOLDER, file_record.stored_filename
        )
        return {
            "id": file_record.id,
            "filename": file_record.filename,
            "stored_filename": file_record.stored_filename,
            "owner_id": file_record.owner_id,
            "path": encrypted_path,
            "plaintext": b"secret file content",
        }


@pytest.fixture
def access_request(app, uploaded_file, second_user):
    with app.app_context():
        request = AccessRequest(
            file_id=uploaded_file["id"],
            user_id=second_user.id,
            status="Pending",
        )
        db.session.add(request)
        db.session.commit()
        return {
            "id": request.id,
            "file_id": request.file_id,
            "user_id": request.user_id,
        }

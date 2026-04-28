import io
import os

import app as app_module
from app import FileRecord


def test_authenticated_user_can_upload_allowed_file(app, client, normal_user, login):
    login(normal_user.username)

    response = client.post(
        "/upload",
        data={"file": (io.BytesIO(b"hello upload"), "hello.txt")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"uploaded and encrypted successfully" in response.data
    with app.app_context():
        file_record = FileRecord.query.filter_by(owner_id=normal_user.id).one()
        assert file_record.filename == "hello.txt"
        assert file_record.encrypted is True


def test_uploaded_file_is_encrypted_on_disk(app, uploaded_file):
    with open(uploaded_file["path"], "rb") as encrypted_file:
        encrypted_content = encrypted_file.read()

    assert encrypted_content != uploaded_file["plaintext"]
    assert app_module.cipher.decrypt(encrypted_content) == uploaded_file["plaintext"]


def test_upload_rejects_missing_file(client, normal_user, login):
    login(normal_user.username)

    response = client.post("/upload", data={}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Please select a file before uploading." in response.data


def test_upload_rejects_empty_file(client, normal_user, login):
    login(normal_user.username)

    response = client.post(
        "/upload",
        data={"file": (io.BytesIO(b""), "empty.txt")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Empty files are not allowed." in response.data


def test_upload_rejects_disallowed_extension(client, normal_user, login):
    login(normal_user.username)

    response = client.post(
        "/upload",
        data={"file": (io.BytesIO(b"bad"), "malware.exe")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"File type not allowed." in response.data


def test_upload_rejects_files_larger_than_max_size(client, normal_user, login):
    login(normal_user.username)
    oversized = b"a" * (app_module.MAX_FILE_SIZE + 1)

    response = client.post(
        "/upload",
        data={"file": (io.BytesIO(oversized), "large.txt")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"File is too large." in response.data


def test_secure_filename_is_respected_for_dangerous_names(
    app, client, normal_user, login
):
    login(normal_user.username)

    response = client.post(
        "/upload",
        data={"file": (io.BytesIO(b"safe content"), "../../evil.txt")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        file_record = FileRecord.query.filter_by(owner_id=normal_user.id).one()
        assert file_record.filename == "evil.txt"
        assert ".." not in file_record.stored_filename
        assert "/" not in file_record.stored_filename
        assert "\\" not in file_record.stored_filename
        assert os.path.exists(
            os.path.join(app_module.UPLOAD_FOLDER, file_record.stored_filename)
        )


def test_users_only_see_their_own_files(
    client, normal_user, second_user, uploaded_file, login
):
    client.get("/logout", follow_redirects=True)
    login(second_user.username)

    response = client.get("/my-files")

    assert response.status_code == 200
    assert uploaded_file["filename"].encode() not in response.data

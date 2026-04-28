import os

from app import AccessRequest, FileRecord, db


def test_logged_in_user_can_request_access(
    app, client, second_user, uploaded_file, login
):
    login(second_user.username)

    response = client.post(
        "/request-access",
        data={"file_id": uploaded_file["id"]},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Access request submitted." in response.data
    with app.app_context():
        request = AccessRequest.query.filter_by(
            user_id=second_user.id, file_id=uploaded_file["id"]
        ).one()
        assert request.status == "Pending"


def test_my_requests_shows_current_users_requests(
    client, second_user, access_request, login
):
    login(second_user.username)

    response = client.get("/my-requests")

    assert response.status_code == 200
    assert b"notes.txt" in response.data
    assert b"Pending" in response.data


def test_users_cannot_download_requests_belonging_to_another_user(
    client, normal_user, access_request, login
):
    login(normal_user.username)

    response = client.get(
        f"/download-request/{access_request['id']}", follow_redirects=True
    )

    assert response.status_code == 200
    assert b"You are not allowed to access this request." in response.data


def test_users_cannot_download_unapproved_requests(
    client, second_user, access_request, login
):
    login(second_user.username)

    response = client.get(
        f"/download-request/{access_request['id']}", follow_redirects=True
    )

    assert response.status_code == 200
    assert b"This request is not approved yet." in response.data


def test_approved_requests_allow_download_original_content(
    app, client, second_user, access_request, uploaded_file, login
):
    with app.app_context():
        request = AccessRequest.query.get(access_request["id"])
        request.status = "Approved"
        db.session.commit()

    login(second_user.username)
    response = client.get(f"/download-request/{access_request['id']}")

    assert response.status_code == 200
    assert response.data == uploaded_file["plaintext"]
    assert response.headers["Content-Disposition"].startswith("attachment;")


def test_download_request_for_deleted_file_is_handled_safely(
    app, client, second_user, access_request, uploaded_file, login
):
    with app.app_context():
        request = AccessRequest.query.get(access_request["id"])
        request.status = "Approved"
        file_record = FileRecord.query.get(uploaded_file["id"])
        if os.path.exists(uploaded_file["path"]):
            os.remove(uploaded_file["path"])
        db.session.delete(file_record)
        db.session.commit()

    login(second_user.username)
    response = client.get(f"/download-request/{access_request['id']}")

    assert response.status_code == 404


def test_file_download_requires_approved_request_belonging_to_current_user(
    client, normal_user, second_user, access_request, login
):
    login(normal_user.username)
    response = client.get(
        f"/download-request/{access_request['id']}", follow_redirects=True
    )
    assert b"You are not allowed to access this request." in response.data

    client.get("/logout", follow_redirects=True)
    login(second_user.username)
    response = client.get(
        f"/download-request/{access_request['id']}", follow_redirects=True
    )
    assert b"This request is not approved yet." in response.data

from werkzeug.security import check_password_hash

from app import AccessRequest, User


def test_passwords_are_never_stored_in_plaintext(app, normal_user):
    with app.app_context():
        user = User.query.get(normal_user.id)
        assert user.password != "password123"
        assert check_password_hash(user.password, "password123")


def test_non_admin_users_cannot_modify_access_request_status(
    app, client, normal_user, access_request, login
):
    login(normal_user.username)

    client.get(f"/approve/{access_request['id']}", follow_redirects=True)
    client.get(f"/deny/{access_request['id']}", follow_redirects=True)

    with app.app_context():
        request = AccessRequest.query.get(access_request["id"])
        assert request.status == "Pending"


def test_direct_owner_download_requires_ownership(
    client, second_user, uploaded_file, login
):
    login(second_user.username)

    response = client.get(f"/download/{uploaded_file['id']}", follow_redirects=True)

    assert response.status_code == 200
    assert b"You are not allowed to download this file." in response.data

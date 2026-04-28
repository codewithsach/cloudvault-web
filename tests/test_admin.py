from app import AccessRequest


def test_normal_users_cannot_access_admin(client, normal_user, login):
    login(normal_user.username)

    response = client.get("/admin", follow_redirects=True)

    assert response.status_code == 200
    assert b"Admin access only." in response.data
    assert b"User Dashboard" in response.data


def test_admin_users_can_access_admin(client, admin_user, login):
    login(admin_user.username)

    response = client.get("/admin")

    assert response.status_code == 200
    assert b"Admin Panel" in response.data


def test_normal_users_cannot_approve_access_requests(
    app, client, normal_user, access_request, login
):
    login(normal_user.username)

    response = client.get(f"/approve/{access_request['id']}", follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        request = AccessRequest.query.get(access_request["id"])
        assert request.status == "Pending"


def test_normal_users_cannot_deny_access_requests(
    app, client, normal_user, access_request, login
):
    login(normal_user.username)

    response = client.get(f"/deny/{access_request['id']}", follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        request = AccessRequest.query.get(access_request["id"])
        assert request.status == "Pending"


def test_admin_users_can_approve_access_requests(
    app, client, admin_user, access_request, login
):
    login(admin_user.username)

    response = client.get(f"/approve/{access_request['id']}", follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        request = AccessRequest.query.get(access_request["id"])
        assert request.status == "Approved"


def test_admin_users_can_deny_access_requests(
    app, client, admin_user, access_request, login
):
    login(admin_user.username)

    response = client.get(f"/deny/{access_request['id']}", follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        request = AccessRequest.query.get(access_request["id"])
        assert request.status == "Denied"


def test_admin_request_display_shows_names_and_file_details(
    client, admin_user, access_request, uploaded_file, second_user, login
):
    login(admin_user.username)

    response = client.get("/admin")

    assert response.status_code == 200
    assert second_user.username.encode() in response.data
    assert second_user.email.encode() in response.data
    assert uploaded_file["filename"].encode() in response.data

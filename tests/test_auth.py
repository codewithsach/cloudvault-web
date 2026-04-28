from werkzeug.security import check_password_hash

from app import User


def test_get_register_returns_200(client):
    response = client.get("/register")

    assert response.status_code == 200
    assert b"Register" in response.data


def test_register_creates_user_with_hashed_password(app, client):
    response = client.post(
        "/register",
        data={
            "username": "newuser",
            "email": "new@example.com",
            "password": "secret123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username="newuser").one()
        assert user.password != "secret123"
        assert check_password_hash(user.password, "secret123")


def test_register_rejects_missing_fields(client):
    response = client.post(
        "/register",
        data={"username": "", "email": "missing@example.com", "password": "secret123"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"All fields are required." in response.data


def test_register_rejects_duplicate_username(app, client, normal_user):
    response = client.post(
        "/register",
        data={
            "username": normal_user.username,
            "email": "unique@example.com",
            "password": "secret123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Username or email already exists." in response.data


def test_register_rejects_duplicate_email(app, client, normal_user):
    response = client.post(
        "/register",
        data={
            "username": "unique",
            "email": normal_user.email,
            "password": "secret123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Username or email already exists." in response.data


def test_get_login_returns_200(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert b"Login" in response.data


def test_login_succeeds_with_valid_credentials(client, normal_user):
    response = client.post(
        "/login",
        data={"username": normal_user.username, "password": "password123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_login_rejects_invalid_credentials(client, normal_user):
    response = client.post(
        "/login",
        data={"username": normal_user.username, "password": "wrong"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invalid username or password." in response.data


def test_logout_logs_out_authenticated_user(client, normal_user, login):
    login(normal_user.username)
    response = client.get("/logout", follow_redirects=True)

    assert response.status_code == 200
    assert b"Logged out successfully." in response.data
    protected = client.get("/dashboard", follow_redirects=False)
    assert protected.status_code == 302
    assert "/login" in protected.headers["Location"]


def test_protected_routes_redirect_anonymous_users(client):
    protected_routes = [
        "/dashboard",
        "/account",
        "/upload",
        "/my-files",
        "/my-requests",
        "/request-access",
        "/admin",
    ]

    for route in protected_routes:
        response = client.get(route, follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

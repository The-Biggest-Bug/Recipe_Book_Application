def test_register_requires_matching_passwords(client):
    response = client.post(
        "/register",
        data={
            "username": "chef",
            "email": "chef@example.com",
            "password": "letmein1",
            "confirm_password": "different1",
        },
    )

    assert response.status_code == 200
    assert b"do not match" in response.data


def test_register_rejects_weak_password(client):
    response = client.post(
        "/register",
        data={
            "username": "chef",
            "email": "chef@example.com",
            "password": "short",
            "confirm_password": "short",
        },
    )

    assert response.status_code == 200
    assert b"at least 8 characters" in response.data


def test_register_rejects_password_without_digit(client):
    response = client.post(
        "/register",
        data={
            "username": "chef",
            "email": "chef@example.com",
            "password": "onlyletters",
            "confirm_password": "onlyletters",
        },
    )

    assert response.status_code == 200
    assert b"include at least one number" in response.data


def test_register_then_login_succeeds(client):
    register_response = client.post(
        "/register",
        data={
            "username": "chef",
            "email": "chef@example.com",
            "password": "letmein1",
            "confirm_password": "letmein1",
        },
        follow_redirects=True,
    )
    assert b"Account created successfully" in register_response.data

    login_response = client.post(
        "/login",
        data={"username_or_email": "chef", "password": "letmein1"},
        follow_redirects=True,
    )
    assert b"Welcome back, chef!" in login_response.data


def test_login_with_wrong_password_fails(client, registered_user):
    response = client.post(
        "/login",
        data={"username_or_email": registered_user["username"], "password": "wrong-password"},
    )

    assert response.status_code == 200
    assert b"Invalid username, email, or password" in response.data


def test_login_required_redirects_anonymous_users(client):
    response = client.get("/favorites", follow_redirects=True)

    assert response.status_code == 200
    assert b"Please log in to view this page" in response.data


def test_logged_in_user_can_reach_profile(logged_in_client):
    response = logged_in_client.get("/profile")

    assert response.status_code == 200
    assert b"chef" in response.data


def test_change_password_requires_current_password(logged_in_client):
    response = logged_in_client.post(
        "/change-password",
        data={
            "current_password": "wrong-password",
            "new_password": "newpass1",
            "confirm_password": "newpass1",
        },
    )

    assert response.status_code == 200
    assert b"Current password is incorrect" in response.data


def test_change_password_success(logged_in_client):
    response = logged_in_client.post(
        "/change-password",
        data={
            "current_password": "letmein1",
            "new_password": "newpass1",
            "confirm_password": "newpass1",
        },
        follow_redirects=True,
    )

    assert b"Password updated successfully" in response.data

    logged_in_client.get("/logout")
    login_response = logged_in_client.post(
        "/login",
        data={"username_or_email": "chef", "password": "newpass1"},
        follow_redirects=True,
    )
    assert b"Welcome back, chef!" in login_response.data

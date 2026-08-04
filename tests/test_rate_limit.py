def test_login_is_rate_limited_after_repeated_failures(rate_limited_client):
    for _ in range(5):
        response = rate_limited_client.post(
            "/login",
            data={"username_or_email": "nobody", "password": "wrong-password"},
        )
        assert response.status_code == 200

    blocked_response = rate_limited_client.post(
        "/login",
        data={"username_or_email": "nobody", "password": "wrong-password"},
    )

    assert blocked_response.status_code == 429


def test_login_get_requests_are_not_rate_limited(rate_limited_client):
    for _ in range(10):
        response = rate_limited_client.get("/login")
        assert response.status_code == 200

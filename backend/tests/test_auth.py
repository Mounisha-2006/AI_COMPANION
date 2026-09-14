def test_register_user_success(client):
    response = client.post("/auth/register", json={
        "name": "Test User",
        "email": "testuser@example.com",
        "password": "securepassword123"
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "testuser@example.com"
    assert data["user"]["name"] == "Test User"
    assert "id" in data["user"]
    # Password hash should NOT be returned
    assert "password_hash" not in data["user"]

def test_register_user_duplicate_email(client):
    # First registration
    client.post("/auth/register", json={
        "name": "Dup User",
        "email": "dup@example.com",
        "password": "password123"
    })
    # Second registration with same email
    response = client.post("/auth/register", json={
        "name": "Dup User Two",
        "email": "dup@example.com",
        "password": "password456"
    })
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()

def test_login_success(client):
    # Register
    client.post("/auth/register", json={
        "name": "Login User",
        "email": "login@example.com",
        "password": "correct_password"
    })
    # Login
    response = client.post("/auth/login", json={
        "email": "login@example.com",
        "password": "correct_password"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login@example.com"

def test_login_invalid_password(client):
    response = client.post("/auth/login", json={
        "email": "login@example.com",
        "password": "wrong_password"
    })
    assert response.status_code == 401

def test_auth_me_protected(client):
    # Unauthorized without token
    res = client.get("/auth/me")
    assert res.status_code == 401

    # Authorized with token
    reg = client.post("/auth/register", json={
        "name": "Me User",
        "email": "me@example.com",
        "password": "password123"
    })
    token = reg.json()["access_token"]
    res_me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "me@example.com"

import pytest
from datetime import timedelta
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User

@pytest.mark.asyncio
async def test_registration_success(client):
    payload = {
        "email": "newuser@example.com",
        "name": "New User",
        "password": "strongpassword123"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["name"] == payload["name"]
    assert data["role"] == "USER"
    assert data["is_active"] is True
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data

@pytest.mark.asyncio
async def test_registration_duplicate_email(client, test_user):
    payload = {
        "email": test_user.email,
        "name": "Duplicate User",
        "password": "strongpassword123"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_registration_validation_short_password(client):
    payload = {
        "email": "shortpw@example.com",
        "name": "Short Pw",
        "password": "123"  # Less than 8 chars
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_registration_validation_password_over_bcrypt_limit(client):
    payload = {
        "email": "longpw@example.com",
        "name": "Long Password",
        "password": "x" * 73,
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Value error, Password must be no more than 72 bytes."

@pytest.mark.asyncio
async def test_registration_validation_password_utf8_bytes_over_bcrypt_limit(client):
    payload = {
        "email": "unicode-longpw@example.com",
        "name": "Unicode Password",
        "password": "é" * 37,
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Value error, Password must be no more than 72 bytes."

@pytest.mark.asyncio
async def test_login_success(client, test_user):
    login_payload = {
        "email": test_user.email,
        "password": "Password123!"
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_password(client, test_user):
    login_payload = {
        "email": test_user.email,
        "password": "WrongPassword!"
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    login_payload = {
        "email": "nonexistent@example.com",
        "password": "SomePassword123!"
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_current_user_me(client, test_user):
    token = create_access_token(test_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email

@pytest.mark.asyncio
async def test_jwt_invalid_token(client):
    headers = {"Authorization": "Bearer invalid.jwt.token"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_jwt_expired_token(client, test_user):
    # Expired token in the past
    token = create_access_token(test_user.id, expires_delta=timedelta(seconds=-10))
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_jwt_refresh_token_as_access_token_rejected(client, test_user):
    # Using refresh token on protected endpoint expecting access token
    refresh_tok = create_refresh_token(test_user.id)
    headers = {"Authorization": f"Bearer {refresh_tok}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_refresh_token_flow(client, test_user):
    refresh_tok = create_refresh_token(test_user.id)
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_tok})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

@pytest.mark.asyncio
async def test_refresh_token_with_invalid_token(client):
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "fake.refresh.token"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_logout_endpoint(client):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()

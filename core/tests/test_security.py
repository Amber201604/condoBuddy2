"""Unit tests for core/security.py — password hashing, JWT, role guards."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "")
os.environ.setdefault("MINIO_ENDPOINT", "")
os.environ.setdefault("MQTT_BROKER_HOST", "")

from datetime import timedelta

import pytest
from jose import jwt

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
)
from app.config import get_settings

settings = get_settings()


class TestPasswordHashing:
    def test_hash_and_verify(self):
        raw = "my_secure_password"
        hashed = get_password_hash(raw)
        assert hashed != raw
        assert verify_password(raw, hashed)

    def test_wrong_password_fails(self):
        hashed = get_password_hash("correct_password")
        assert not verify_password("wrong_password", hashed)

    def test_different_hashes_for_same_password(self):
        h1 = get_password_hash("same")
        h2 = get_password_hash("same")
        assert h1 != h2  # bcrypt salts differ

    def test_empty_password(self):
        hashed = get_password_hash("")
        assert verify_password("", hashed)
        assert not verify_password("notempty", hashed)


class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token(data={"sub": "user-123"})
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == "user-123"
        assert "exp" in payload

    def test_custom_expiry(self):
        token = create_access_token(
            data={"sub": "user-456"},
            expires_delta=timedelta(minutes=5),
        )
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == "user-456"

    def test_token_contains_custom_data(self):
        token = create_access_token(data={"sub": "u1", "role": "admin"})
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["role"] == "admin"

    def test_invalid_token_raises(self):
        from jose import JWTError
        with pytest.raises(JWTError):
            jwt.decode("invalid.token.here", settings.secret_key, algorithms=[settings.algorithm])


class TestAuthEndpoints:
    def test_register_success(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "newuser@test.com",
            "password": "password123",
            "full_name": "New User",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newuser@test.com"
        assert data["full_name"] == "New User"
        assert "id" in data

    def test_register_duplicate_email(self, client):
        email = "dup@test.com"
        client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "password123",
            "full_name": "First",
        })
        resp = client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "password456",
            "full_name": "Second",
        })
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"]

    def test_login_success(self, client):
        email = "loginuser@test.com"
        client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "pass123",
            "full_name": "Login User",
        })
        resp = client.post("/api/v1/auth/login", data={
            "username": email,
            "password": "pass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        email = "wrongpw@test.com"
        client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "correct",
            "full_name": "User",
        })
        resp = client.post("/api/v1/auth/login", data={
            "username": email,
            "password": "incorrect",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/v1/auth/login", data={
            "username": "nobody@test.com",
            "password": "whatever",
        })
        assert resp.status_code == 401

    def test_me_endpoint(self, client):
        email = "meuser@test.com"
        client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "pass123",
            "full_name": "Me User",
        })
        login = client.post("/api/v1/auth/login", data={
            "username": email,
            "password": "pass123",
        })
        token = login.json()["access_token"]
        resp = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200
        assert resp.json()["email"] == email

    def test_me_without_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_change_password(self, client):
        email = "changepw@test.com"
        client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "oldpass",
            "full_name": "PW User",
        })
        login = client.post("/api/v1/auth/login", data={
            "username": email,
            "password": "oldpass",
        })
        token = login.json()["access_token"]
        resp = client.post("/api/v1/auth/change-password", json={
            "current_password": "oldpass",
            "new_password": "newpass123",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        # Verify old password no longer works
        resp2 = client.post("/api/v1/auth/login", data={
            "username": email,
            "password": "oldpass",
        })
        assert resp2.status_code == 401

    def test_change_password_wrong_current(self, client):
        email = "wrongcur@test.com"
        client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "current",
            "full_name": "User",
        })
        login = client.post("/api/v1/auth/login", data={
            "username": email,
            "password": "current",
        })
        token = login.json()["access_token"]
        resp = client.post("/api/v1/auth/change-password", json={
            "current_password": "wrong",
            "new_password": "newpass123",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400

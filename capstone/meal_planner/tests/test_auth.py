"""
Authentication tests — register, login, token validation.
"""
import pytest


# ─── Positive ─────────────────────────────────────────────────────────────────

def test_register_success(client):
    resp = client.post("/auth/register", json={
        "username": "alice",
        "email": "alice@example.com",
        "password": "strongpass1",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@example.com"
    assert "password" not in data


def test_login_returns_token(client):
    client.post("/auth/register", json={
        "username": "bob",
        "email": "bob@example.com",
        "password": "strongpass1",
    })
    resp = client.post("/auth/login", data={
        "username": "bob",
        "password": "strongpass1",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_get_me_with_valid_token(client, auth):
    resp = client.get("/auth/me", headers=auth)
    assert resp.status_code == 200
    assert resp.json()["username"] == "testuser"


# ─── Negative ─────────────────────────────────────────────────────────────────

def test_register_username_too_short(client):
    resp = client.post("/auth/register", json={
        "username": "ab",
        "email": "ab@example.com",
        "password": "strongpass1",
    })
    assert resp.status_code == 422


def test_register_password_too_short(client):
    resp = client.post("/auth/register", json={
        "username": "validname",
        "email": "v@example.com",
        "password": "short",
    })
    assert resp.status_code == 422


def test_register_duplicate_username(client):
    payload = {"username": "dup", "email": "dup@example.com", "password": "pass1234"}
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 400


def test_register_duplicate_email(client):
    client.post("/auth/register", json={
        "username": "user1", "email": "same@example.com", "password": "pass1234"
    })
    resp = client.post("/auth/register", json={
        "username": "user2", "email": "same@example.com", "password": "pass1234"
    })
    assert resp.status_code == 400


def test_login_wrong_password(client):
    client.post("/auth/register", json={
        "username": "charlie", "email": "c@example.com", "password": "correctpass"
    })
    resp = client.post("/auth/login", data={
        "username": "charlie", "password": "wrongpass"
    })
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = client.post("/auth/login", data={
        "username": "nobody", "password": "irrelevant"
    })
    assert resp.status_code == 401


def test_protected_endpoint_without_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_protected_endpoint_with_invalid_token(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer not.a.real.token"})
    assert resp.status_code == 401

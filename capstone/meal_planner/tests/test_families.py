"""
Family management tests — create, list, edit members, delete, ownership isolation.
"""
import pytest


MEMBER = {
    "name": "Alice",
    "age": 30,
    "calorie_target": 2000,
    "diet_tags": [{"tag": "halal", "is_forbidden": False}],
}


# ─── Positive ─────────────────────────────────────────────────────────────────

def test_create_family(client, auth):
    resp = client.post("/families/", json={
        "name": "The Smiths",
        "members": [MEMBER],
    }, headers=auth)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "The Smiths"
    assert len(data["members"]) == 1
    assert data["members"][0]["name"] == "Alice"


def test_list_families_returns_own(client, auth):
    client.post("/families/", json={"name": "Family A", "members": [MEMBER]}, headers=auth)
    resp = client.get("/families/", headers=auth)
    assert resp.status_code == 200
    names = [f["name"] for f in resp.json()]
    assert "Family A" in names


def test_get_family_by_id(client, auth, family):
    resp = client.get(f"/families/{family['id']}", headers=auth)
    assert resp.status_code == 200
    assert resp.json()["id"] == family["id"]


def test_update_member_tags(client, auth, family):
    member_id = family["members"][0]["id"]
    resp = client.put(
        f"/families/{family['id']}/members/{member_id}",
        json={
            "age": 31,
            "calorie_target": 1800,
            "diet_tags": [{"tag": "vegetarian", "is_forbidden": False}],
        },
        headers=auth,
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["calorie_target"] == 1800
    assert any(t["tag"] == "vegetarian" for t in updated["diet_tags"])


def test_delete_family(client, auth, family):
    resp = client.delete(f"/families/{family['id']}", headers=auth)
    assert resp.status_code == 200
    # Confirm it's gone
    assert client.get(f"/families/{family['id']}", headers=auth).status_code == 404


# ─── Negative ─────────────────────────────────────────────────────────────────

def test_other_user_cannot_access_family(client, auth, auth2, family):
    """User 2 must not see User 1's family."""
    resp = client.get(f"/families/{family['id']}", headers=auth2)
    assert resp.status_code == 404


def test_other_user_cannot_delete_family(client, auth, auth2, family):
    resp = client.delete(f"/families/{family['id']}", headers=auth2)
    assert resp.status_code == 404


def test_get_nonexistent_family(client, auth):
    resp = client.get("/families/99999", headers=auth)
    assert resp.status_code == 404


def test_list_families_requires_auth(client):
    resp = client.get("/families/")
    assert resp.status_code == 401

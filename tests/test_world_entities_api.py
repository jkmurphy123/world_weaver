from fastapi.testclient import TestClient

from world_weaver.app import create_app


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_world_entity_routes_require_authentication(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_API_TOKEN", "test-token")

    client = TestClient(create_app())
    response = client.get("/api/world/world-main/factions")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"


def test_faction_crud_happy_path(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_API_TOKEN", "test-token")
    client = TestClient(create_app())

    create_response = client.post(
        "/api/world/world-main/factions",
        headers=_auth("test-token"),
        json={
            "name": "Copper Compact",
            "ideology": "regulated trade supremacy",
            "influence": 67,
            "confidence_tier": "established",
        },
    )
    assert create_response.status_code == 201
    faction_id = create_response.json()["id"]

    list_response = client.get("/api/world/world-main/factions", headers=_auth("test-token"))
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/api/world/world-main/factions/{faction_id}", headers=_auth("test-token"))
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Copper Compact"

    update_response = client.patch(
        f"/api/world/world-main/factions/{faction_id}",
        headers=_auth("test-token"),
        json={"influence": 72, "confidence_tier": "core_canon"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["influence"] == 72
    assert update_response.json()["confidence_tier"] == "core_canon"

    delete_response = client.delete(f"/api/world/world-main/factions/{faction_id}", headers=_auth("test-token"))
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/world/world-main/factions/{faction_id}", headers=_auth("test-token"))
    assert missing_response.status_code == 404


def test_duplicate_unique_entity_name_returns_conflict(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_API_TOKEN", "test-token")
    client = TestClient(create_app())

    payload = {
        "name": "Sunward Accord",
        "ideology": "mutual reconstruction",
        "influence": 40,
        "confidence_tier": "established",
    }
    first = client.post("/api/world/world-main/factions", headers=_auth("test-token"), json=payload)
    second = client.post("/api/world/world-main/factions", headers=_auth("test-token"), json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Faction already exists in this world"


def test_validation_and_world_scoping_for_character_routes(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_API_TOKEN", "test-token")
    client = TestClient(create_app())

    invalid = client.post(
        "/api/world/world-main/characters",
        headers=_auth("test-token"),
        json={"name": "Elan Voss", "role": "editor", "affiliation": "Daily Relay"},
    )
    assert invalid.status_code == 422

    created = client.post(
        "/api/world/world-a/characters",
        headers=_auth("test-token"),
        json={
            "name": "Elan Voss",
            "role": "editor",
            "affiliation": "Daily Relay",
            "status": "active",
            "confidence_tier": "established",
        },
    )
    assert created.status_code == 201
    created_id = created.json()["id"]

    wrong_world = client.get(f"/api/world/world-b/characters/{created_id}", headers=_auth("test-token"))
    assert wrong_world.status_code == 404


def test_lore_tags_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_API_TOKEN", "test-token")
    client = TestClient(create_app())

    created = client.post(
        "/api/world/world-main/lore",
        headers=_auth("test-token"),
        json={
            "title": "The Aether Compact",
            "body": "A treaty signed beneath the glass moon.",
            "tags": ["treaty", "history", "moon"],
            "confidence_tier": "core_canon",
        },
    )

    assert created.status_code == 201
    assert created.json()["tags"] == ["treaty", "history", "moon"]

    fetched = client.get(
        f"/api/world/world-main/lore/{created.json()['id']}",
        headers=_auth("test-token"),
    )
    assert fetched.status_code == 200
    assert fetched.json()["tags"] == ["treaty", "history", "moon"]

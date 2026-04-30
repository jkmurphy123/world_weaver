from fastapi.testclient import TestClient

from world_weaver.app import create_app


def test_local_world_entity_routes_are_not_mounted(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))

    client = TestClient(create_app())

    response = client.get("/api/world/world-main/factions")

    assert response.status_code == 404

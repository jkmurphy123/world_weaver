from datetime import date

from fastapi.testclient import TestClient

from world_weaver.app import create_app
from world_weaver.services.story_service import StoryService
from world_weaver.services.world_generation import WorldGenerationService


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_stories_can_be_loaded_by_date(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    world = WorldGenerationService().generate_world_bible(
        name="Chronicle Sphere",
        genre="science fantasy",
        tone="investigative",
        premise="A hidden archive leaks state secrets to ordinary citizens.",
        seed=42,
    )
    service = StoryService(tmp_path / "stories")
    service.save_batch(service.generate_daily_batch(target_date=date(2026, 4, 9), world_bible=world))

    client = TestClient(create_app())
    response = client.get("/stories/2026-04-09")

    assert response.status_code == 200
    payload = response.json()
    assert payload["date"] == "2026-04-09"
    assert len(payload["stories"]) == 4


def test_stories_by_date_returns_404_when_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    client = TestClient(create_app())

    response = client.get("/stories/2026-04-11")

    assert response.status_code == 404

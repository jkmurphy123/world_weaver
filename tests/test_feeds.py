from datetime import UTC, date, datetime
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient

from world_weaver.app import create_app
from world_weaver.schemas import Story, StoryBatch, StoryMetadata
from world_weaver.services.story_service import StoryService


def _seed_story_batches(tmp_path) -> None:
    service = StoryService(tmp_path / "stories")
    first_batch = StoryBatch(
        date=date(2026, 4, 8),
        stories=[
            Story(
                headline="Older dispatch",
                summary="First summary",
                body="First body",
                category="world",
                metadata=StoryMetadata(
                    story_id="story-2026-04-08-001",
                    published_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
                    target_date=date(2026, 4, 8),
                    world_id="chronicle-sphere-42",
                ),
            ),
        ],
    )
    second_batch = StoryBatch(
        date=date(2026, 4, 9),
        stories=[
            Story(
                headline="Latest bulletin",
                summary="Second summary",
                body="Second body",
                category="science",
                metadata=StoryMetadata(
                    story_id="story-2026-04-09-001",
                    published_at=datetime(2026, 4, 9, 12, 30, tzinfo=UTC),
                    target_date=date(2026, 4, 9),
                    world_id="chronicle-sphere-42",
                ),
            ),
        ],
    )
    service.save_batch(first_batch)
    service.save_batch(second_batch)


def test_rss_feed_contains_required_fields_and_ordering(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    _seed_story_batches(tmp_path)
    client = TestClient(create_app())

    response = client.get("/feeds/rss.xml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/rss+xml")
    root = ET.fromstring(response.text)
    assert root.tag == "rss"

    items = root.findall("./channel/item")
    assert len(items) == 2
    assert [item.findtext("storyId") for item in items] == [
        "story-2026-04-09-001",
        "story-2026-04-08-001",
    ]
    assert items[0].findtext("targetDate") == "2026-04-09"
    assert items[0].findtext("worldId") == "chronicle-sphere-42"
    assert items[0].findtext("category") == "science"


def test_atom_feed_contains_required_fields_and_ordering(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    _seed_story_batches(tmp_path)
    client = TestClient(create_app())

    response = client.get("/feeds/atom.xml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/atom+xml")
    root = ET.fromstring(response.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    entries = root.findall("atom:entry", ns)
    assert len(entries) == 2
    assert [entry.findtext("atom:storyId", namespaces=ns) for entry in entries] == [
        "story-2026-04-09-001",
        "story-2026-04-08-001",
    ]
    assert entries[0].findtext("atom:targetDate", namespaces=ns) == "2026-04-09"
    assert entries[0].findtext("atom:worldId", namespaces=ns) == "chronicle-sphere-42"
    assert entries[0].find("atom:category", ns).attrib["term"] == "science"

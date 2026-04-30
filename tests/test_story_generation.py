import json
from datetime import date, datetime, timezone

import pytest

from world_weaver.llm.base import PromptRequest
from world_weaver.schemas import WorldBible
from world_weaver.services.story_service import StoryService
from world_weaver.services.world_generation import WorldGenerationService


def _build_world() -> WorldBible:
    service = WorldGenerationService(clock=lambda: datetime(2026, 4, 9, tzinfo=timezone.utc))
    return service.generate_world_bible(
        name="Chronicle Sphere",
        genre="science fantasy",
        tone="investigative",
        premise="A hidden archive leaks state secrets to ordinary citizens.",
        seed=42,
    )


def test_generate_daily_batch_has_required_story_fields(tmp_path) -> None:
    world = _build_world()
    story_service = StoryService(stories_dir=tmp_path / "stories")
    target = date(2026, 4, 9)

    batch = story_service.generate_daily_batch(target_date=target, world_bible=world, count=4)

    assert batch.date == target
    assert len(batch.stories) == 4
    first = batch.stories[0]
    assert first.headline
    assert first.summary
    assert first.body
    assert first.category
    assert first.metadata.target_date == target
    assert first.metadata.story_id.startswith("story-2026-04-09-")


def test_story_batch_is_persisted_and_loaded_by_date(tmp_path) -> None:
    world = _build_world()
    stories_dir = tmp_path / "stories"
    story_service = StoryService(stories_dir=stories_dir)
    target = date(2026, 4, 9)

    batch = story_service.generate_daily_batch(target_date=target, world_bible=world, count=2)
    saved = story_service.save_batch(batch)
    reloaded = story_service.load_batch(target)

    assert saved.name == "2026-04-09.json"
    assert saved.exists()
    assert reloaded is not None
    assert reloaded.date == target
    assert len(reloaded.stories) == 2


def test_load_batch_returns_none_for_missing_date(tmp_path) -> None:
    service = StoryService(stories_dir=tmp_path / "stories")
    assert service.load_batch(date(2026, 4, 10)) is None


class _StubReporterProvider:
    def __init__(self, payload: str) -> None:
        self._payload = payload
        self.requests: list[PromptRequest] = []

    def generate_json(self, request: PromptRequest) -> str:
        self.requests.append(request)
        return self._payload


def test_generate_reported_batch_validates_reporter_output(tmp_path) -> None:
    news_context = {
        "metadata": {"schema_version": "worldcodex.context.v1", "export_type": "news_context", "world_id": "chronicle-sphere"},
        "places": [{"id": "place.archive", "name": "Archive District"}],
        "factions": [{"id": "org.council", "name": "Archive Council"}],
    }
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "reporter_daily.md").write_text("You are the News Reporter.", encoding="utf-8")
    provider = _StubReporterProvider(
        json.dumps(
            {
                "date": "2026-04-09",
                "stories": [
                    {
                        "headline": "Council vote reshapes transit grid",
                        "summary": "A late vote changes freight access routes.",
                        "body": "Long-form article body.",
                        "category": "politics",
                        "metadata": {
                            "story_id": "story-2026-04-09-001",
                            "published_at": "2026-04-09T10:00:00+00:00",
                            "target_date": "2026-04-09",
                            "world_id": "chronicle-sphere-42",
                        },
                    }
                ],
            }
        )
    )
    service = StoryService(stories_dir=tmp_path / "stories", provider=provider, prompts_dir=prompts_dir)

    batch = service.generate_reported_batch(
        target_date=date(2026, 4, 9),
        news_context=news_context,
        model="mock-reporter-v1",
        count=1,
        target_body_words=500,
    )

    assert batch.date == date(2026, 4, 9)
    assert len(batch.stories) == 1
    assert provider.requests[0].model == "mock-reporter-v1"
    request_payload = json.loads(provider.requests[0].user_prompt)
    assert request_payload["target_body_words"] == 500
    assert request_payload["news_context"]["metadata"]["world_id"] == "chronicle-sphere"
    assert "world_bible" not in request_payload


def test_generate_reported_batch_rejects_invalid_json(tmp_path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "reporter_daily.md").write_text("You are the News Reporter.", encoding="utf-8")
    provider = _StubReporterProvider("{not json")
    service = StoryService(stories_dir=tmp_path / "stories", provider=provider, prompts_dir=prompts_dir)

    with pytest.raises(ValueError, match="invalid JSON"):
        service.generate_reported_batch(
            target_date=date(2026, 4, 9),
            news_context={"metadata": {"world_id": "chronicle-sphere"}},
            model="mock-reporter-v1",
            count=1,
        )


def test_generate_reported_batch_rejects_invalid_schema(tmp_path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "reporter_daily.md").write_text("You are the News Reporter.", encoding="utf-8")
    provider = _StubReporterProvider(json.dumps({"date": "2026-04-09", "stories": [{"headline": "Missing fields"}]}))
    service = StoryService(stories_dir=tmp_path / "stories", provider=provider, prompts_dir=prompts_dir)

    with pytest.raises(ValueError, match="StoryBatch schema"):
        service.generate_reported_batch(
            target_date=date(2026, 4, 9),
            news_context={"metadata": {"world_id": "chronicle-sphere"}},
            model="mock-reporter-v1",
            count=1,
        )

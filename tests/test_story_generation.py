from datetime import date, datetime, timezone

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

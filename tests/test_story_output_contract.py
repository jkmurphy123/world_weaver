import json
from pathlib import Path

from world_weaver.schemas import StoryBatch


def test_story_batch_example_fixture_validates_against_schema() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "story_batch_example.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    batch = StoryBatch.model_validate(payload)

    assert batch.date.isoformat() == "2026-04-10"
    assert len(batch.stories) == 4
    assert batch.stories[0].metadata.story_id == "story-2026-04-10-001"

from __future__ import annotations

import json
import random
from datetime import date, datetime, timezone
from pathlib import Path

from world_weaver.schemas import Story, StoryBatch, StoryMetadata, WorldBible


class StoryService:
    """Generate and persist daily story batches."""

    def __init__(self, stories_dir: Path) -> None:
        self._stories_dir = stories_dir

    def generate_daily_batch(self, *, target_date: date, world_bible: WorldBible, count: int = 4) -> StoryBatch:
        seed = world_bible.metadata.seed + target_date.toordinal()
        rng = random.Random(seed)
        categories = ["politics", "culture", "science", "business", "world"]

        stories: list[Story] = []
        for index in range(1, count + 1):
            category = rng.choice(categories)
            region = world_bible.regions[0].name
            faction = world_bible.factions[0].name
            hook = world_bible.story_hooks[0]
            story_id = f"story-{target_date.isoformat()}-{index:03d}"

            stories.append(
                Story(
                    headline=f"{faction} stirs tensions in {region}",
                    summary=f"{faction} intensifies pressure as events unfold in {region}.",
                    body=f"{hook} Local sources report escalating consequences across {region}.",
                    category=category,
                    metadata=StoryMetadata(
                        story_id=story_id,
                        published_at=datetime.now(timezone.utc),
                        target_date=target_date,
                        world_id=f"{world_bible.metadata.name.lower().replace(' ', '-')}-{world_bible.metadata.seed}",
                    ),
                )
            )

        return StoryBatch(date=target_date, stories=stories)

    def save_batch(self, batch: StoryBatch) -> Path:
        self._stories_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._stories_dir / f"{batch.date.isoformat()}.json"
        output_path.write_text(json.dumps(batch.model_dump(mode="json"), indent=2), encoding="utf-8")
        return output_path

    def load_batch(self, target_date: date) -> StoryBatch | None:
        path = self._stories_dir / f"{target_date.isoformat()}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return StoryBatch.model_validate(payload)

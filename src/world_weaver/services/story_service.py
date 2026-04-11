from __future__ import annotations

import json
import random
from datetime import date, datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from world_weaver.llm.base import LLMProvider, PromptRequest
from world_weaver.schemas import Story, StoryBatch, StoryMetadata, WorldBible


class StoryService:
    """Generate and persist daily story batches."""

    def __init__(
        self,
        stories_dir: Path,
        *,
        provider: LLMProvider | None = None,
        prompts_dir: Path | None = None,
    ) -> None:
        self._stories_dir = stories_dir
        self._provider = provider
        self._prompts_dir = prompts_dir

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

    def generate_reported_batch(
        self,
        *,
        target_date: date,
        world_bible: WorldBible,
        model: str,
        count: int = 4,
    ) -> StoryBatch:
        if self._provider is None:
            raise ValueError("Reporter generation requires an LLM provider")
        if self._prompts_dir is None:
            raise ValueError("Reporter generation requires a prompts directory")

        request = PromptRequest(
            system_prompt=self._load_prompt_template("reporter_daily.md"),
            user_prompt=json.dumps(
                {
                    "target_date": target_date.isoformat(),
                    "edition": "morning",
                    "story_count": count,
                    "world_bible": world_bible.model_dump(mode="json"),
                },
                separators=(",", ":"),
            ),
            model=model,
        )
        raw_response = self._provider.generate_json(request)

        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise ValueError("Reporter returned invalid JSON") from exc

        try:
            batch = StoryBatch.model_validate(payload)
        except ValidationError as exc:
            raise ValueError("Reporter output did not match StoryBatch schema") from exc

        if batch.date != target_date:
            raise ValueError("Reporter output date did not match requested target date")

        return batch

    @staticmethod
    def load_world_bible(path: Path) -> WorldBible:
        if not path.exists():
            raise FileNotFoundError(f"World bible not found at {path}")

        payload = json.loads(path.read_text(encoding="utf-8"))
        return WorldBible.model_validate(payload)

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

    def _load_prompt_template(self, filename: str) -> str:
        return (self._prompts_dir / filename).read_text(encoding="utf-8")

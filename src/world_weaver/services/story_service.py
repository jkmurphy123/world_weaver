from __future__ import annotations

import json
import random
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

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
                    body=(
                        f"{hook} Officials in {region} said the latest moves by {faction} "
                        "shifted the day's political balance and forced local institutions to respond."
                        "\n\n"
                        f"Residents, trade groups, and civil agencies described a widening ripple effect across {region}, "
                        "with transport plans, public messaging, and neighborhood routines all adjusting to the change."
                        "\n\n"
                        f"Analysts following {faction} said the immediate disruption may be manageable, "
                        f"but the longer-term consequences could reshape alliances and public expectations throughout {region}."
                    ),
                    category=category,
                    metadata=StoryMetadata(
                        story_id=story_id,
                        published_at=datetime.now(timezone.utc),
                        target_date=target_date,
                        world_id=f"{world_bible.metadata.name.lower().replace(' ', '-')}-{world_bible.metadata.seed}",
                    ),
                    referenced_entities=[faction, region],
                    continuity_effects=[
                        f"{faction} escalated a consequential dispute in {region}.",
                        f"Authorities in {region} are still assessing the longer-term impact of the latest move by {faction}.",
                    ],
                )
            )

        return StoryBatch(date=target_date, stories=stories)

    def generate_reported_batch(
        self,
        *,
        target_date: date,
        news_context: dict[str, Any],
        model: str,
        count: int = 4,
        target_body_words: int = 500,
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
                    "target_body_words": target_body_words,
                    "news_context": news_context,
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

    def load_latest_batch(self) -> StoryBatch | None:
        if not self._stories_dir.exists():
            return None

        story_paths = sorted(self._stories_dir.glob("*.json"), reverse=True)
        for path in story_paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return StoryBatch.model_validate(payload)
        return None

    def _load_prompt_template(self, filename: str) -> str:
        return (self._prompts_dir / filename).read_text(encoding="utf-8")

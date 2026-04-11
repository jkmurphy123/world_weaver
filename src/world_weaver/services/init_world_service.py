from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Callable

from world_weaver.llm.base import LLMProvider, PromptRequest
from world_weaver.schemas import WorldBible

Clock = Callable[[], datetime]


class InitWorldService:
    """Create and persist the initial world bible using a world-architect LLM."""

    def __init__(
        self,
        *,
        provider: LLMProvider,
        prompts_dir: Path,
        worlds_dir: Path,
        clock: Clock | None = None,
    ) -> None:
        self._provider = provider
        self._prompts_dir = prompts_dir
        self._worlds_dir = worlds_dir
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def generate_initial_world(self, *, seed_prompt: str, model: str) -> WorldBible:
        if not seed_prompt.strip():
            raise ValueError("Seed prompt must not be empty")

        request = PromptRequest(
            system_prompt=self._load_prompt_template("world_architect_initial.md"),
            user_prompt=seed_prompt.strip(),
            model=model,
        )
        raw_response = self._provider.generate_json(request)

        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise ValueError("World architect returned invalid JSON") from exc

        world = WorldBible.model_validate(payload)
        self._validate_baseline_entities(world)
        return world

    def save_world(self, world: WorldBible) -> tuple[Path, Path]:
        self._worlds_dir.mkdir(parents=True, exist_ok=True)
        json_path = self._worlds_dir / "world_bible.json"
        markdown_path = self._worlds_dir / "world_bible.md"

        json_path.write_text(json.dumps(world.model_dump(mode="json"), indent=2), encoding="utf-8")
        markdown_path.write_text(self._to_markdown_summary(world), encoding="utf-8")
        return json_path, markdown_path

    def generate_and_save(self, *, seed_prompt: str, model: str) -> tuple[WorldBible, Path, Path]:
        world = self.generate_initial_world(seed_prompt=seed_prompt, model=model)
        json_path, markdown_path = self.save_world(world)
        return world, json_path, markdown_path

    def _load_prompt_template(self, filename: str) -> str:
        path = self._prompts_dir / filename
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _validate_baseline_entities(world: WorldBible) -> None:
        if not world.people:
            raise ValueError("World bible must include at least one person")
        if not world.organizations:
            raise ValueError("World bible must include at least one organization")
        if not world.locations:
            raise ValueError("World bible must include at least one location")
        if not world.timeline:
            raise ValueError("World bible must include at least one timeline fact")

    @staticmethod
    def _to_markdown_summary(world: WorldBible) -> str:
        world_name = world.world.name if world.world else world.metadata.name
        genre = world.world.genre if world.world else world.metadata.genre
        tone = world.world.tone if world.world else world.metadata.tone

        lines = [
            f"# World Bible - {world_name}",
            "",
            f"- Genre: {genre}",
            f"- Tone: {tone}",
            f"- Premise: {world.premise}",
            "",
            "## People",
        ]
        lines.extend(f"- {person.name}: {person.role} ({person.affiliation})" for person in world.people)

        lines.append("")
        lines.append("## Organizations")
        lines.extend(f"- {org.name}: {org.description}" for org in world.organizations)

        lines.append("")
        lines.append("## Locations")
        lines.extend(f"- {location.name}: {location.description}" for location in world.locations)

        lines.append("")
        lines.append("## Timeline")
        lines.extend(f"- {event.date.isoformat()} - {event.title}: {event.summary}" for event in world.timeline)

        return "\n".join(lines) + "\n"

from __future__ import annotations

import random
import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from world_weaver.schemas import Faction, Region, WorldBible, WorldMetadata

Clock = Callable[[], datetime]


class WorldGenerationService:
    """Deterministic world bible generation with pluggable pipeline steps."""

    def __init__(self, clock: Clock | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def generate_world_bible(
        self,
        *,
        name: str,
        genre: str,
        tone: str,
        premise: str,
        seed: int,
    ) -> WorldBible:
        rng = random.Random(seed)
        regions = self._generate_regions(rng=rng, genre=genre)
        factions = self._generate_factions(rng=rng, tone=tone)
        story_hooks = self._generate_story_hooks(
            rng=rng,
            premise=premise,
            regions=regions,
            factions=factions,
        )
        metadata = WorldMetadata(
            name=name,
            genre=genre,
            tone=tone,
            seed=seed,
            generated_at=self._clock(),
        )
        return WorldBible(
            metadata=metadata,
            premise=premise,
            regions=regions,
            factions=factions,
            story_hooks=story_hooks,
        )

    def to_persistence_row(self, world_bible: WorldBible) -> dict[str, Any]:
        return {
            "world_id": self._make_world_id(world_bible.metadata.name, world_bible.metadata.seed),
            "name": world_bible.metadata.name,
            "genre": world_bible.metadata.genre,
            "tone": world_bible.metadata.tone,
            "seed": world_bible.metadata.seed,
            "generated_at": world_bible.metadata.generated_at.isoformat(),
            "bible_json": world_bible.model_dump_json(),
        }

    def _generate_regions(self, *, rng: random.Random, genre: str) -> list[Region]:
        climates = ["temperate", "arid", "frozen", "storm-lashed", "lush"]
        nouns = ["Reach", "Vale", "Front", "Wastes", "Archipelago"]
        return [
            Region(
                name=f"{genre.title()} {rng.choice(nouns)}",
                climate=rng.choice(climates),
                landmarks=[f"{rng.choice(['Obelisk', 'Citadel', 'Rift', 'Spire'])} of Echoes"],
            )
        ]

    def _generate_factions(self, *, rng: random.Random, tone: str) -> list[Faction]:
        labels = ["Consortium", "Order", "Collective", "Syndicate", "Covenant"]
        ideologies = [
            "pragmatic expansion",
            "strict preservation",
            "radical reform",
            "technocratic control",
            "mystic balance",
        ]
        return [
            Faction(
                name=f"{tone.title()} {rng.choice(labels)}",
                ideology=rng.choice(ideologies),
                influence=rng.randint(35, 90),
            )
        ]

    def _generate_story_hooks(
        self,
        *,
        rng: random.Random,
        premise: str,
        regions: list[Region],
        factions: list[Faction],
    ) -> list[str]:
        templates = [
            "{faction} races to control {region} as {premise}",
            "A fragile truce in {region} breaks when {faction} exploits {premise}",
            "Smugglers reveal secrets in {region}, forcing {faction} to respond to {premise}",
        ]
        return [
            rng.choice(templates).format(
                faction=factions[0].name,
                region=regions[0].name,
                premise=premise.lower(),
            )
        ]

    @staticmethod
    def _make_world_id(name: str, seed: int) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        return f"{slug}-{seed}"

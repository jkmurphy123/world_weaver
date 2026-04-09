import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from world_weaver.schemas import Faction, Region, WorldBible, WorldMetadata
from world_weaver.services.world_generation import WorldGenerationService


def test_world_bible_schema_requires_non_empty_regions_and_factions() -> None:
    with pytest.raises(ValidationError):
        WorldBible(
            metadata=WorldMetadata(
                name="Aster", genre="fantasy", tone="hopeful", seed=11, generated_at=datetime.now(timezone.utc)
            ),
            premise="A star engine fractured reality.",
            regions=[],
            factions=[],
            story_hooks=["A rebellion begins in orbit."],
        )


def test_generate_world_bible_is_deterministic_with_fixed_clock() -> None:
    fixed_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    service = WorldGenerationService(clock=lambda: fixed_now)

    world_a = service.generate_world_bible(
        name="Asterfall",
        genre="science fantasy",
        tone="noir",
        premise="An ancient archive predicts every betrayal.",
        seed=77,
    )
    world_b = service.generate_world_bible(
        name="Asterfall",
        genre="science fantasy",
        tone="noir",
        premise="An ancient archive predicts every betrayal.",
        seed=77,
    )

    assert world_a == world_b


def test_generate_world_bible_pipeline_steps_are_mockable() -> None:
    fixed_now = datetime(2026, 2, 2, tzinfo=timezone.utc)
    service = WorldGenerationService(clock=lambda: fixed_now)

    stub_regions = [Region(name="Glass Reach", climate="temperate", landmarks=["Needle Bridge"])]
    stub_factions = [Faction(name="Dawn Order", ideology="strict preservation", influence=63)]
    stub_hooks = ["Dawn Order weaponizes a forgotten treaty."]

    with (
        patch.object(service, "_generate_regions", return_value=stub_regions) as regions_patch,
        patch.object(service, "_generate_factions", return_value=stub_factions) as factions_patch,
        patch.object(service, "_generate_story_hooks", return_value=stub_hooks) as hooks_patch,
    ):
        world = service.generate_world_bible(
            name="Shardhaven",
            genre="fantasy",
            tone="grim",
            premise="Moonlight reveals buried empires.",
            seed=14,
        )

    regions_patch.assert_called_once()
    factions_patch.assert_called_once()
    hooks_patch.assert_called_once()
    assert world.regions == stub_regions
    assert world.factions == stub_factions
    assert world.story_hooks == stub_hooks


def test_to_persistence_row_returns_sqlite_ready_shape() -> None:
    fixed_now = datetime(2026, 3, 3, tzinfo=timezone.utc)
    service = WorldGenerationService(clock=lambda: fixed_now)
    world = service.generate_world_bible(
        name="Clockwork Sea",
        genre="steampunk",
        tone="adventurous",
        premise="A submerged city rises every equinox.",
        seed=101,
    )

    row = service.to_persistence_row(world)

    assert row["world_id"] == "clockwork-sea-101"
    assert isinstance(row["name"], str)
    assert isinstance(row["genre"], str)
    assert isinstance(row["tone"], str)
    assert isinstance(row["seed"], int)
    assert row["generated_at"] == fixed_now.isoformat()

    parsed = json.loads(row["bible_json"])
    assert parsed["metadata"]["name"] == "Clockwork Sea"
    assert parsed["metadata"]["seed"] == 101

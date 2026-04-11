import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from world_weaver.llm.base import PromptRequest
from world_weaver.schemas import Faction, Region, WorldBible, WorldMetadata
from world_weaver.services.init_world_service import InitWorldService
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


class _StubProvider:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.requests: list[PromptRequest] = []

    def generate_json(self, request: PromptRequest) -> str:
        self.requests.append(request)
        return json.dumps(self._payload)


def _world_payload() -> dict:
    return {
        "world": {
            "id": "world-main",
            "name": "New Meridian",
            "genre": "cyberpunk",
            "tone": "investigative",
            "premise": "Corporations run a vertical city-state.",
            "calendar_mode": "real_time_daily",
        },
        "style_guide": {
            "news_voice": "factual, dry, suspicious of power",
            "allowed_story_types": ["politics", "business", "science", "culture"],
            "taboos": ["meta references"],
        },
        "continuity": {
            "current_date": "2074-01-01",
            "major_facts": ["The Meridian Council controls trade and media licenses."],
            "rules": ["No supernatural powers."],
        },
        "locations": [
            {
                "id": "loc-central",
                "name": "Meridian Central",
                "description": "Corporate core district.",
                "confidence_tier": "core_canon",
            }
        ],
        "organizations": [
            {
                "id": "org-council",
                "name": "Meridian Council",
                "description": "Ruling consortium.",
                "confidence_tier": "core_canon",
            }
        ],
        "people": [
            {
                "id": "person-vex",
                "name": "Vex",
                "role": "Hacker icon",
                "affiliation": "Free Circuit",
                "status": "missing",
                "confidence_tier": "established",
            }
        ],
        "timeline": [
            {
                "id": "event-2074-launch",
                "date": "2074-01-01",
                "title": "Founding event",
                "summary": "The world bible baseline is established.",
                "confidence_tier": "core_canon",
            }
        ],
        "metadata": {
            "name": "New Meridian",
            "genre": "cyberpunk",
            "tone": "investigative",
            "seed": 42,
            "generated_at": "2026-04-11T00:00:00+00:00",
        },
        "premise": "Corporations run a vertical city-state.",
        "regions": [{"name": "The Crown", "climate": "humid", "landmarks": ["Axiom Tower"]}],
        "factions": [{"name": "Meridian Council", "ideology": "managed order", "influence": 90}],
        "story_hooks": ["A data leak destabilizes a major council election."],
    }


def test_init_world_service_validates_and_persists_world_artifacts(tmp_path) -> None:
    provider = _StubProvider(_world_payload())
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "world_architect_initial.md").write_text("Prompt template", encoding="utf-8")
    worlds_dir = tmp_path / "worlds"

    service = InitWorldService(provider=provider, prompts_dir=prompts_dir, worlds_dir=worlds_dir)
    world, json_path, markdown_path = service.generate_and_save(
        seed_prompt="A floating city ruled by syndicates.",
        model="test-model",
    )

    assert world.metadata.name == "New Meridian"
    assert len(world.people) >= 1
    assert len(world.organizations) >= 1
    assert len(world.locations) >= 1
    assert len(world.timeline) >= 1
    assert json_path.exists()
    assert markdown_path.exists()
    assert provider.requests[0].model == "test-model"

    persisted = json.loads(json_path.read_text(encoding="utf-8"))
    assert persisted["world"]["name"] == "New Meridian"
    assert persisted["people"][0]["name"] == "Vex"


def test_init_world_service_rejects_missing_baseline_entities(tmp_path) -> None:
    invalid_payload = _world_payload()
    invalid_payload["people"] = []
    provider = _StubProvider(invalid_payload)
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "world_architect_initial.md").write_text("Prompt template", encoding="utf-8")

    service = InitWorldService(provider=provider, prompts_dir=prompts_dir, worlds_dir=tmp_path / "worlds")
    with pytest.raises(ValueError, match="at least one person"):
        service.generate_initial_world(seed_prompt="Seed", model="test-model")

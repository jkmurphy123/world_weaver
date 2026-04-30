from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from world_weaver.llm.base import PromptRequest
from world_weaver.llm.mock_provider import MockLLMProvider
from world_weaver.schemas import Story, StoryBatch, StoryMetadata
from world_weaver.services.patch_service import (
    WorldCodexPatchProposalService,
    validate_worldcodex_patch_payload,
)


class _StubPatchProvider:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.requests: list[PromptRequest] = []

    def generate_json(self, request: PromptRequest) -> str:
        self.requests.append(request)
        return self.payload

    def check_connection(self, model: str) -> object:
        return object()


def _story_batch() -> StoryBatch:
    return StoryBatch(
        date=date(2026, 4, 30),
        stories=[
            Story(
                headline="Council changes freight access",
                summary="The council changed freight access after a tense vote.",
                body="A complete story body.",
                category="politics",
                referenced_entities=["org.meridian_council", "place.glass_harbor"],
                continuity_effects=["Freight access rules changed in Glass Harbor."],
                metadata=StoryMetadata(
                    story_id="story-2026-04-30-001",
                    published_at=datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc),
                    target_date=date(2026, 4, 30),
                    world_id="titan-osa",
                ),
            )
        ],
    )


def _news_context() -> dict:
    return {
        "metadata": {
            "schema_version": "worldcodex.context.v1",
            "export_type": "news_context",
            "world_id": "titan-osa",
        },
        "places": [{"id": "place.glass_harbor", "name": "Glass Harbor"}],
        "factions": [{"id": "org.meridian_council", "name": "Meridian Council"}],
    }


def test_worldcodex_patch_proposal_service_generates_patch(tmp_path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "worldcodex_patch_proposal.md").write_text(
        "Produce a WorldCodex patch proposal using worldcodex.patch.v1.",
        encoding="utf-8",
    )
    provider = _StubPatchProvider(
        json.dumps(
            {
                "schema_version": "worldcodex.patch.v1",
                "id": "patch-2026-04-30-newsroom",
                "description": "Newsroom proposals.",
                "operations": [
                    {
                        "op": "add_timeline_event",
                        "atom": {
                            "id": "event.newsroom_2026_04_30_001",
                            "type": "event",
                            "name": "Council changes freight access",
                            "summary": "The council changed freight access after a tense vote.",
                            "tags": ["newsroom"],
                            "data": {
                                "date_or_era": "2026-04-30",
                                "participants": ["org.meridian_council"],
                                "locations": ["place.glass_harbor"],
                            },
                        },
                    }
                ],
            }
        )
    )
    service = WorldCodexPatchProposalService(
        provider=provider,
        prompts_dir=prompts_dir,
        patches_dir=tmp_path / "patches",
    )

    patch = service.generate_patch(
        target_date="2026-04-30",
        news_context=_news_context(),
        story_batch=_story_batch(),
        model="mock-worldcodex-patch-v1",
    )

    assert patch["schema_version"] == "worldcodex.patch.v1"
    assert patch["operations"][0]["op"] == "add_timeline_event"
    request_payload = json.loads(provider.requests[0].user_prompt)
    assert request_payload["news_context"]["metadata"]["world_id"] == "titan-osa"
    assert "world_bible" not in request_payload


def test_worldcodex_patch_proposal_service_saves_and_loads_patch(tmp_path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "worldcodex_patch_proposal.md").write_text("worldcodex.patch.v1", encoding="utf-8")
    service = WorldCodexPatchProposalService(
        provider=_StubPatchProvider("{}"),
        prompts_dir=prompts_dir,
        patches_dir=tmp_path / "patches",
    )
    patch = {
        "schema_version": "worldcodex.patch.v1",
        "id": "patch-2026-04-30-newsroom",
        "description": "Newsroom proposals.",
        "operations": [
            {
                "op": "update_atom",
                "atom_id": "org.meridian_council",
                "set": {"data.status": "under scrutiny"},
            }
        ],
    }

    path = service.save_patch(patch, filename_stem="2026-04-30")
    loaded = service.load_patch("2026-04-30")

    assert path.name == "2026-04-30.json"
    assert loaded == patch


def test_worldcodex_patch_validation_rejects_old_canon_patch_shape() -> None:
    with pytest.raises(ValueError, match="schema_version"):
        validate_worldcodex_patch_payload(
            {
                "date": "2026-04-30",
                "timeline_events": [],
                "open_threads_added": [],
            }
        )


def test_mock_provider_generates_worldcodex_patch() -> None:
    provider = MockLLMProvider()
    request = PromptRequest(
        system_prompt="Produce a WorldCodex patch proposal using worldcodex.patch.v1.",
        user_prompt=json.dumps(
            {
                "target_date": "2026-04-30",
                "news_context": _news_context(),
                "story_batch": _story_batch().model_dump(mode="json"),
            }
        ),
        model="mock-worldcodex-patch-v1",
    )

    payload = json.loads(provider.generate_json(request))

    assert payload["schema_version"] == "worldcodex.patch.v1"
    assert payload["operations"][0]["op"] == "add_timeline_event"
    assert payload["operations"][0]["atom"]["type"] == "event"
    assert payload["operations"][1]["subject"] == "org.meridian_council"

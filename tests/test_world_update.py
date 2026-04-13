import json
from datetime import date, datetime, timezone

from typer.testing import CliRunner

from world_weaver.cli import app
from world_weaver.llm.base import PromptRequest
from world_weaver.schemas import CanonUpdatePatch
from world_weaver.services.merge_service import MergeService
from world_weaver.services.patch_service import PatchService
from world_weaver.services.story_service import StoryService
from world_weaver.services.world_generation import WorldGenerationService


runner = CliRunner()


def _build_world():
    service = WorldGenerationService(clock=lambda: datetime(2026, 4, 9, tzinfo=timezone.utc))
    return service.generate_world_bible(
        name="Chronicle Sphere",
        genre="science fantasy",
        tone="investigative",
        premise="A hidden archive leaks state secrets to ordinary citizens.",
        seed=42,
    )


class _StubPatchProvider:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.requests: list[PromptRequest] = []

    def generate_json(self, request: PromptRequest) -> str:
        self.requests.append(request)
        return self.payload


def test_patch_service_generates_valid_canon_update_patch(tmp_path) -> None:
    world = _build_world()
    batch = StoryService(stories_dir=tmp_path / "stories").generate_daily_batch(
        target_date=date(2026, 4, 9),
        world_bible=world,
        count=1,
    )
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "world_architect_patch.md").write_text("Produce a canon update patch.", encoding="utf-8")

    provider = _StubPatchProvider(
        json.dumps(
            {
                "date": "2026-04-09",
                "new_people": [],
                "updated_people": [],
                "new_organizations": [],
                "updated_organizations": [],
                "new_locations": [],
                "updated_locations": [],
                "timeline_events": [
                    {
                        "id": "event-2026-04-09-001",
                        "date": "2026-04-09",
                        "title": "Chronicle Sphere tensions intensify",
                        "summary": "A durable conflict enters canon.",
                        "confidence_tier": "established",
                    }
                ],
                "open_threads_added": [
                    {
                        "id": "thread-2026-04-09-001",
                        "title": "Transit strike fallout",
                        "description": "Officials still have not settled competing demands.",
                        "status": "open",
                        "confidence_tier": "established",
                    }
                ],
                "open_threads_resolved": [],
                "major_facts_added": [
                    {
                        "id": "fact-2026-04-09-001",
                        "text": "A regional dispute now shapes public life in Chronicle Sphere.",
                        "tier": "established",
                    }
                ],
                "continuity_warnings": [],
            }
        )
    )
    service = PatchService(provider=provider, prompts_dir=prompts_dir, patches_dir=tmp_path / "patches")

    patch = service.generate_patch(
        target_date="2026-04-09",
        world_bible=world,
        story_batch=batch,
        model="mock-world-architect-v1",
    )

    assert isinstance(patch, CanonUpdatePatch)
    assert patch.date == date(2026, 4, 9)
    assert len(patch.timeline_events) == 1
    assert len(provider.requests) == 1


def test_merge_service_applies_patch_without_dropping_existing_canon(tmp_path) -> None:
    world = _build_world()
    patch = CanonUpdatePatch.model_validate(
        {
            "date": "2026-04-10",
            "new_people": [],
            "updated_people": [],
            "new_organizations": [],
            "updated_organizations": [],
            "new_locations": [],
            "updated_locations": [],
            "timeline_events": [
                {
                    "id": "event-2026-04-10-001",
                    "date": "2026-04-10",
                    "title": "Council expands emergency powers",
                    "summary": "A durable institutional shift is now part of canon.",
                    "confidence_tier": "established",
                }
            ],
            "open_threads_added": [
                {
                    "id": "thread-2026-04-10-001",
                    "title": "Emergency powers backlash",
                    "description": "Opposition groups are organizing a response.",
                    "status": "open",
                    "confidence_tier": "established",
                }
            ],
            "open_threads_resolved": [],
            "major_facts_added": [
                {
                    "id": "fact-2026-04-10-001",
                    "text": "Emergency powers are now a central political fault line.",
                    "tier": "established",
                }
            ],
            "continuity_warnings": ["Conflicting casualty totals remain unverified."],
        }
    )
    service = MergeService(worlds_dir=tmp_path / "worlds", snapshots_dir=tmp_path / "snapshots")

    merged_world, report = service.apply_patch(world_bible=world, patch=patch)

    assert len(merged_world.people) == len(world.people)
    assert len(merged_world.organizations) == len(world.organizations)
    assert merged_world.continuity is not None
    assert merged_world.continuity.current_date == date(2026, 4, 10)
    assert len(merged_world.timeline) == len(world.timeline) + 1
    assert len(merged_world.open_threads) == 1
    assert report.timeline_events_added == 1
    assert report.open_threads_added == 1
    assert report.major_facts_added == 1
    assert report.warnings == ["Conflicting casualty totals remain unverified."]


def test_update_world_command_generates_patch_and_snapshot(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_LLM_PROVIDER", "mock")

    init_result = runner.invoke(app, ["init-world", "--prompt", "A synthetic island city ruled by corporate blocs."])
    assert init_result.exit_code == 0

    generate_result = runner.invoke(app, ["generate-news", "--date", "2026-04-13"])
    assert generate_result.exit_code == 0

    update_result = runner.invoke(app, ["update-world", "--date", "2026-04-13"])

    assert update_result.exit_code == 0
    assert "Updated world canon for 2026-04-13" in update_result.stdout
    assert (tmp_path / "patches" / "2026-04-13.json").exists()
    assert (tmp_path / "snapshots" / "2026-04-13" / "world_before.json").exists()
    assert (tmp_path / "snapshots" / "2026-04-13" / "world_after.json").exists()

    updated_world = json.loads((tmp_path / "worlds" / "world_bible.json").read_text(encoding="utf-8"))
    assert updated_world["continuity"]["current_date"] == "2026-04-13"
    assert len(updated_world["timeline"]) >= 2
    assert len(updated_world["open_threads"]) >= 1

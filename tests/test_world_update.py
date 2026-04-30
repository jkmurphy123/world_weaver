import json
from datetime import date, datetime, timezone
from pathlib import Path

from typer.testing import CliRunner

from world_weaver.cli import app
from world_weaver.llm.base import PromptRequest
from world_weaver.schemas import CanonUpdatePatch
from world_weaver.services.merge_service import MergeService
from world_weaver.services.patch_service import PatchService
from world_weaver.services.story_service import StoryService
from world_weaver.services.world_generation import WorldGenerationService
from world_weaver.worldcodex_client import CommandResult


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


class _FakeWorldCodexClient:
    def __init__(self) -> None:
        self.news_context = {
            "metadata": {
                "schema_version": "worldcodex.context.v1",
                "export_type": "news_context",
                "world_id": "world-new-meridian",
            },
            "places": [{"id": "place.central", "name": "Meridian Central"}],
            "factions": [{"id": "org.council", "name": "Meridian Council"}],
        }
        self.validated_patches: list[Path] = []
        self.previewed_patches: list[Path] = []
        self.applied_patches: list[Path] = []

    def export_context(self, context_type: str) -> dict:
        return self.news_context

    def validate_patch(self, patch_path: Path) -> CommandResult:
        self.validated_patches.append(patch_path)
        return CommandResult(args=(), returncode=0, stdout="validated", stderr="")

    def preview_patch(self, patch_path: Path) -> CommandResult:
        self.previewed_patches.append(patch_path)
        return CommandResult(args=(), returncode=0, stdout="previewed", stderr="")

    def apply_patch(self, patch_path: Path) -> CommandResult:
        self.applied_patches.append(patch_path)
        return CommandResult(args=(), returncode=0, stdout="applied", stderr="")


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


def test_patch_service_generates_valid_patch_from_manual_note(tmp_path) -> None:
    world = _build_world()
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "world_architect_manual_update.md").write_text(
        "Given the current world bible and an operator-provided canon note, produce a canon update patch JSON.",
        encoding="utf-8",
    )
    provider = _StubPatchProvider(
        json.dumps(
            {
                "date": "2026-04-09",
                "new_people": [
                    {
                        "id": "person-mara-voss",
                        "name": "Mara Voss",
                        "role": "Chief executive",
                        "affiliation": "Helix Dynamics",
                        "status": "active",
                        "confidence_tier": "established",
                    }
                ],
                "updated_people": [],
                "new_organizations": [
                    {
                        "id": "org-helix-dynamics",
                        "name": "Helix Dynamics",
                        "description": "Orbital freight and predictive logistics corporation.",
                        "confidence_tier": "established",
                    }
                ],
                "updated_organizations": [],
                "new_locations": [
                    {
                        "id": "loc-glass-harbor",
                        "name": "Glass Harbor",
                        "description": "A deep-water corporate port district.",
                        "confidence_tier": "established",
                    }
                ],
                "updated_locations": [],
                "timeline_events": [],
                "open_threads_added": [],
                "open_threads_resolved": [],
                "major_facts_added": [],
                "continuity_warnings": [],
            }
        )
    )
    service = PatchService(provider=provider, prompts_dir=prompts_dir, patches_dir=tmp_path / "patches")

    patch = service.generate_patch_from_note(
        target_date="2026-04-09",
        world_bible=world,
        source_text="Add Helix Dynamics in Glass Harbor, led by Mara Voss.",
        model="mock-world-architect-v1",
    )

    assert patch.date == date(2026, 4, 9)
    assert patch.new_organizations[0].name == "Helix Dynamics"
    assert patch.new_locations[0].name == "Glass Harbor"
    assert patch.new_people[0].name == "Mara Voss"


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
    fake_worldcodex = _FakeWorldCodexClient()
    monkeypatch.setattr("world_weaver.cli.build_worldcodex_client", lambda **_: fake_worldcodex)

    stories_dir = tmp_path / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)
    (stories_dir / "2026-04-13.json").write_text(
        json.dumps(
            {
                "date": "2026-04-13",
                "stories": [
                    {
                        "headline": "Council changes freight access",
                        "summary": "The council changed freight access after a tense vote.",
                        "body": "A complete story body.",
                        "category": "politics",
                        "referenced_entities": ["org.council", "place.central"],
                        "continuity_effects": ["Freight access rules changed."],
                        "metadata": {
                            "story_id": "story-2026-04-13-001",
                            "published_at": "2026-04-13T12:00:00+00:00",
                            "target_date": "2026-04-13",
                            "world_id": "world-new-meridian",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    update_result = runner.invoke(app, ["update-world", "--date", "2026-04-13"])

    assert update_result.exit_code == 0
    assert "WorldCodex patch previewed for 2026-04-13" in update_result.stdout
    patch_path = tmp_path / "patches" / "2026-04-13.json"
    assert patch_path.exists()
    assert fake_worldcodex.validated_patches == [patch_path]
    assert fake_worldcodex.previewed_patches == [patch_path]
    assert fake_worldcodex.applied_patches == []
    assert (tmp_path / "snapshots" / "2026-04-13" / "story_batch.json").exists()
    assert (tmp_path / "snapshots" / "2026-04-13" / "worldcodex_patch.json").exists()
    assert (tmp_path / "snapshots" / "2026-04-13" / "worldcodex_validate.txt").exists()
    assert (tmp_path / "snapshots" / "2026-04-13" / "worldcodex_preview.txt").exists()


def test_add_canon_command_is_deprecated(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))

    add_result = runner.invoke(
        app,
        [
            "add-canon",
            "--date",
            "2026-04-14",
            "--text",
            "Add a corporation called Helix Dynamics in Glass Harbor, led by Mara Voss.",
        ],
    )

    assert add_result.exit_code == 2
    assert "manual canon edits belong in WorldCodex" in add_result.stdout or "WorldCodex now owns world-building" in add_result.stdout
    assert not (tmp_path / "worlds" / "world_bible.json").exists()


def test_add_canon_dry_run_is_deprecated_without_mutating_files(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))

    dry_run_result = runner.invoke(
        app,
        [
            "add-canon",
            "--dry-run",
            "--date",
            "2026-04-14",
            "--text",
            "Add a corporation called Helix Dynamics in Glass Harbor, led by Mara Voss.",
        ],
    )

    assert dry_run_result.exit_code == 2
    assert "WorldCodex now owns world-building" in dry_run_result.stdout
    assert not (tmp_path / "patches").exists()

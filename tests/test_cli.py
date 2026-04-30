import json
from pathlib import Path

from typer.testing import CliRunner

from world_weaver.cli import app
from world_weaver.worldcodex_client import CommandResult


runner = CliRunner()


class _FakeWorldCodexClient:
    def __init__(self, news_context: dict | None = None) -> None:
        self.news_context = news_context or {
            "metadata": {
                "schema_version": "worldcodex.context.v1",
                "export_type": "news_context",
                "world_id": "world-new-meridian",
            },
            "places": [{"id": "place.central", "name": "Meridian Central"}],
            "factions": [{"id": "org.council", "name": "Meridian Council"}],
            "open_threads": [{"id": "conflict.trade", "summary": "Trade routes remain contested."}],
        }
        self.exported_contexts: list[str] = []
        self.validated_patches: list[Path] = []
        self.previewed_patches: list[Path] = []
        self.applied_patches: list[Path] = []

    def export_context(self, context_type: str) -> dict:
        self.exported_contexts.append(context_type)
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


def test_cli_help_works() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.stdout


def test_serve_help_works() -> None:
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "Run the newsroom API server." in result.stdout


def test_generate_news_command_persists_batch_by_date(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_LLM_PROVIDER", "mock")
    fake_worldcodex = _FakeWorldCodexClient()
    monkeypatch.setattr("world_weaver.cli.build_worldcodex_client", lambda **_: fake_worldcodex)

    result = runner.invoke(app, ["generate-news", "--date", "2026-04-09", "--body-words", "500"])

    assert result.exit_code == 0
    assert "Generated 4 stories for 2026-04-09" in result.stdout
    output_path = tmp_path / "stories" / "2026-04-09.json"
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(payload["stories"][0]["body"].split()) >= 400
    assert fake_worldcodex.exported_contexts == ["news-context"]


def test_generate_news_command_accepts_worldcodex_news_context_shape(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_LLM_PROVIDER", "mock")
    fake_worldcodex = _FakeWorldCodexClient(
        {
            "metadata": {
                "schema_version": "worldcodex.context.v1",
                "export_type": "news_context",
                "world_id": "world-new-meridian",
                "world_title": "New Meridian",
            },
            "places": [
                {
                    "id": "place.meridian_central",
                    "type": "place",
                    "name": "Meridian Central",
                    "summary": "Corporate core district.",
                }
            ],
            "factions": [
                {
                    "id": "org.meridian_council",
                    "type": "org",
                    "name": "Meridian Council",
                    "summary": "Ruling consortium.",
                }
            ],
            "characters": [
                {
                    "id": "character.vex",
                    "type": "character",
                    "name": "Vex",
                    "summary": "Hacker icon.",
                }
            ],
            "timeline": [
                {
                    "id": "event.founding",
                    "summary": "The world baseline is established.",
                    "participants": ["org.meridian_council"],
                    "locations": ["place.meridian_central"],
                }
            ],
        }
    )
    monkeypatch.setattr("world_weaver.cli.build_worldcodex_client", lambda **_: fake_worldcodex)

    result = runner.invoke(app, ["generate-news", "--date", "2026-04-11"])

    assert result.exit_code == 0
    assert "Generated 4 stories for 2026-04-11" in result.stdout
    output_path = tmp_path / "stories" / "2026-04-11.json"
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["stories"][0]["metadata"]["world_id"] == "world-new-meridian"
    assert "org.meridian_council" in payload["stories"][0]["referenced_entities"]


def test_propose_world_patch_command_generates_worldcodex_patch(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_LLM_PROVIDER", "mock")
    fake_worldcodex = _FakeWorldCodexClient()
    monkeypatch.setattr("world_weaver.cli.build_worldcodex_client", lambda **_: fake_worldcodex)

    stories_dir = tmp_path / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)
    (stories_dir / "2026-04-30.json").write_text(
        json.dumps(
            {
                "date": "2026-04-30",
                "stories": [
                    {
                        "headline": "Council changes freight access",
                        "summary": "The council changed freight access after a tense vote.",
                        "body": "A complete story body.",
                        "category": "politics",
                        "referenced_entities": ["org.council", "place.central"],
                        "continuity_effects": ["Freight access rules changed."],
                        "metadata": {
                            "story_id": "story-2026-04-30-001",
                            "published_at": "2026-04-30T12:00:00+00:00",
                            "target_date": "2026-04-30",
                            "world_id": "world-new-meridian",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["propose-world-patch", "--date", "2026-04-30"])

    assert result.exit_code == 0
    assert "Generated WorldCodex patch proposal for 2026-04-30" in result.stdout
    patch_path = tmp_path / "patches" / "2026-04-30.json"
    assert patch_path.exists()
    patch = json.loads(patch_path.read_text(encoding="utf-8"))
    assert patch["schema_version"] == "worldcodex.patch.v1"
    assert patch["operations"][0]["op"] == "add_timeline_event"


def test_set_llm_provider_command_persists_selection(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    monkeypatch.setenv("NEWSROOM_ENV_FILE", str(env_path))

    result = runner.invoke(app, ["set-llm-provider", "--provider", "openai", "--model", "gpt-4.1"])

    assert result.exit_code == 0
    assert "Saved provider=openai model=gpt-4.1" in result.stdout
    persisted = env_path.read_text(encoding="utf-8")
    assert "NEWSROOM_LLM_PROVIDER=openai" in persisted
    assert "NEWSROOM_LLM_MODEL=gpt-4.1" in persisted


def test_test_llm_connection_uses_selected_mock_provider(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "NEWSROOM_LLM_PROVIDER=mock\nNEWSROOM_LLM_MODEL=mock-world-architect-v1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("NEWSROOM_ENV_FILE", str(env_path))

    result = runner.invoke(app, ["test-llm-connection"])

    assert result.exit_code == 0
    assert "LLM connection OK: provider=mock" in result.stdout


def test_init_world_command_is_deprecated(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))

    result = runner.invoke(app, ["init-world", "--prompt", "A dense floating city ruled by data cartels."])

    assert result.exit_code == 2
    assert "deprecated because WorldCodex now owns world-building" in result.stdout
    assert not (tmp_path / "worlds" / "world_bible.json").exists()


def test_init_world_command_with_prompt_file_is_deprecated(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    prompt_file = tmp_path / "seed.txt"
    prompt_file.write_text("Megacorps rule a stacked harbor metropolis.", encoding="utf-8")

    result = runner.invoke(app, ["init-world", "--prompt-file", str(prompt_file)])

    assert result.exit_code == 2
    assert "Create the world in WorldCodex" in result.stdout


def test_init_world_without_prompt_prints_deprecation_guidance() -> None:
    result = runner.invoke(app, ["init-world"])
    assert result.exit_code == 2
    assert "WorldCodex now owns world-building" in result.stdout


def test_update_world_command_previews_worldcodex_patch_without_applying(tmp_path, monkeypatch) -> None:
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
    assert "No canon changes applied" in update_result.stdout
    patch_path = tmp_path / "patches" / "2026-04-13.json"
    assert patch_path.exists()
    assert fake_worldcodex.validated_patches == [patch_path]
    assert fake_worldcodex.previewed_patches == [patch_path]
    assert fake_worldcodex.applied_patches == []
    assert (tmp_path / "snapshots" / "2026-04-13" / "worldcodex_validate.txt").exists()
    assert (tmp_path / "snapshots" / "2026-04-13" / "worldcodex_preview.txt").exists()
    assert not (tmp_path / "snapshots" / "2026-04-13" / "worldcodex_apply.txt").exists()


def test_update_world_command_applies_when_requested(tmp_path, monkeypatch) -> None:
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

    update_result = runner.invoke(app, ["update-world", "--date", "2026-04-13", "--apply"])

    assert update_result.exit_code == 0
    assert "WorldCodex patch applied for 2026-04-13" in update_result.stdout
    patch_path = tmp_path / "patches" / "2026-04-13.json"
    assert fake_worldcodex.validated_patches == [patch_path]
    assert fake_worldcodex.previewed_patches == [patch_path]
    assert fake_worldcodex.applied_patches == [patch_path]
    assert (tmp_path / "snapshots" / "2026-04-13" / "worldcodex_apply.txt").exists()


def test_world_summary_command_is_deprecated(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))

    result = runner.invoke(app, ["world-summary", "--output", "json"])

    assert result.exit_code == 2
    assert "Use `world export <world> world-bible`" in result.stdout

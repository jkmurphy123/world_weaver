import json
from pathlib import Path

from typer.testing import CliRunner

from world_weaver.cli import app
from world_weaver.storage.sqlite_world_store import SqliteWorldStore, WorldEntityRepository


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

    def export_context(self, context_type: str) -> dict:
        self.exported_contexts.append(context_type)
        return self.news_context


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

    result = runner.invoke(app, ["generate-news", "--date", "2026-04-09"])

    assert result.exit_code == 0
    assert "Generated 4 stories for 2026-04-09" in result.stdout
    assert (tmp_path / "stories" / "2026-04-09.json").exists()
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


def test_init_world_command_accepts_prompt_text(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_LLM_PROVIDER", "mock")

    result = runner.invoke(app, ["init-world", "--prompt", "A dense floating city ruled by data cartels."])

    assert result.exit_code == 0
    assert "Initialized world" in result.stdout
    assert (tmp_path / "worlds" / "world_bible.json").exists()
    assert (tmp_path / "worlds" / "world_bible.md").exists()


def test_init_world_command_refreshes_sqlite_projection(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_LLM_PROVIDER", "mock")

    result = runner.invoke(app, ["init-world", "--prompt", "A dense floating city ruled by data cartels."])

    assert result.exit_code == 0
    summary_result = runner.invoke(app, ["world-summary", "--output", "json"])
    assert summary_result.exit_code == 0
    payload = json.loads(summary_result.stdout)
    assert payload["sqlite_entity_counts"] == {
        "factions": 1,
        "locations": 2,
        "characters": 1,
        "lore_entries": 3,
    }


def test_init_world_command_accepts_prompt_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_LLM_PROVIDER", "mock")
    prompt_file = tmp_path / "seed.txt"
    prompt_file.write_text("Megacorps rule a stacked harbor metropolis.", encoding="utf-8")

    result = runner.invoke(app, ["init-world", "--prompt-file", str(prompt_file)])

    assert result.exit_code == 0
    assert (tmp_path / "worlds" / "world_bible.json").exists()


def test_init_world_requires_exactly_one_prompt_input() -> None:
    result = runner.invoke(app, ["init-world"])
    assert result.exit_code != 0
    combined_output = f"{result.stdout}\n{result.stderr}"
    assert "Provide exactly one of --prompt or --prompt-file" in combined_output


def test_update_world_command_refreshes_sqlite_projection(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_LLM_PROVIDER", "mock")

    init_result = runner.invoke(app, ["init-world", "--prompt", "A synthetic island city ruled by corporate blocs."])
    assert init_result.exit_code == 0
    generate_result = runner.invoke(app, ["generate-news", "--date", "2026-04-13"])
    assert generate_result.exit_code == 0

    update_result = runner.invoke(app, ["update-world", "--date", "2026-04-13"])

    assert update_result.exit_code == 0
    summary_result = runner.invoke(app, ["world-summary", "--output", "json"])
    assert summary_result.exit_code == 0
    payload = json.loads(summary_result.stdout)
    assert payload["canon_counts"]["open_threads"] >= 1
    assert payload["sqlite_entity_counts"] == {
        "factions": 1,
        "locations": 2,
        "characters": 1,
        "lore_entries": 5,
    }


def test_world_summary_command_outputs_json_with_story_and_sqlite_counts(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(data_dir))

    worlds_dir = data_dir / "worlds"
    worlds_dir.mkdir(parents=True, exist_ok=True)
    world_path = worlds_dir / "world_bible.json"
    world_path.write_text(
        json.dumps(
            {
                "world": {
                    "id": "world-new-meridian",
                    "name": "New Meridian",
                    "genre": "cyberpunk",
                    "tone": "gritty",
                    "calendar_mode": "real_time_daily",
                },
                "style_guide": {
                    "allowed_story_types": ["politics", "business", "culture"],
                    "taboos": ["out-of-world references"],
                },
                "continuity": {"current_date": "2074-04-09"},
                "locations": [{"id": "loc-1"}],
                "organizations": [{"id": "org-1"}],
                "governments": [{"id": "gov-1"}],
                "corporations": [{"id": "corp-1"}],
                "people": [{"id": "person-1"}],
                "technologies": [{"id": "tech-1"}],
                "conflicts": [{"id": "conflict-1"}],
                "open_threads": [{"id": "thread-1"}],
                "timeline": [{"id": "event-1"}],
            }
        ),
        encoding="utf-8",
    )

    stories_dir = data_dir / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)
    (stories_dir / "2026-04-10.json").write_text(
        json.dumps(
            {
                "date": "2026-04-10",
                "stories": [
                    {
                        "headline": "Meridian Council debates a transit levy",
                        "summary": "A contentious vote moved to committee.",
                        "body": "Debate intensified after labor unions staged a march.",
                        "category": "politics",
                        "metadata": {
                            "story_id": "story-2026-04-10-001",
                            "published_at": "2026-04-10T12:00:00Z",
                            "target_date": "2026-04-10",
                            "world_id": "world-new-meridian",
                        },
                    },
                    {
                        "headline": "Dock cooperatives report cargo surge",
                        "summary": "Independent terminals posted strong numbers.",
                        "body": "Meridian's southern docks led the quarterly gain.",
                        "category": "business",
                        "metadata": {
                            "story_id": "story-2026-04-10-002",
                            "published_at": "2026-04-10T13:00:00Z",
                            "target_date": "2026-04-10",
                            "world_id": "world-new-meridian",
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    store = SqliteWorldStore(
        db_path=data_dir / "world.db",
        migrations_dir=Path(__file__).resolve().parents[1] / "src" / "world_weaver" / "storage" / "migrations",
    )
    store.run_migrations()
    repo = WorldEntityRepository(store)
    repo.create(
        "factions",
        "world-new-meridian",
        {
            "name": "Meridian Council",
            "ideology": "stability-first governance",
            "influence": 88,
            "confidence_tier": "core_canon",
        },
    )
    repo.create(
        "locations",
        "world-new-meridian",
        {
            "name": "Meridian Central",
            "region": "Core District",
            "description": "Administrative and financial center.",
            "confidence_tier": "core_canon",
        },
    )
    repo.create(
        "characters",
        "world-new-meridian",
        {
            "name": "Amara Osei-Mensah",
            "role": "ceo",
            "affiliation": "ZephyrNet",
            "status": "active",
            "confidence_tier": "core_canon",
        },
    )
    repo.create(
        "lore_entries",
        "world-new-meridian",
        {
            "title": "The Meridian Compact",
            "body": "Foundational agreement among the five corporations.",
            "tags": ["governance"],
            "confidence_tier": "established",
        },
    )

    result = runner.invoke(app, ["world-summary", "--output", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["world"]["id"] == "world-new-meridian"
    assert payload["canon_counts"]["locations"] == 1
    assert payload["latest_stories"]["date"] == "2026-04-10"
    assert payload["latest_stories"]["categories"] == {"business": 1, "politics": 1}
    assert payload["sqlite_entity_counts"] == {
        "factions": 1,
        "locations": 1,
        "characters": 1,
        "lore_entries": 1,
    }

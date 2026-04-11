import json
from pathlib import Path

from typer.testing import CliRunner

from world_weaver.cli import app
from world_weaver.storage.sqlite_world_store import SqliteWorldStore, WorldEntityRepository


runner = CliRunner()


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

    init_result = runner.invoke(app, ["init-world", "--prompt", "A synthetic island city ruled by corporate blocs."])
    assert init_result.exit_code == 0

    result = runner.invoke(app, ["generate-news", "--date", "2026-04-09"])

    assert result.exit_code == 0
    assert "Generated 4 stories for 2026-04-09" in result.stdout
    assert (tmp_path / "stories" / "2026-04-09.json").exists()


def test_generate_news_command_accepts_canonical_world_bible_shape(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_LLM_PROVIDER", "mock")

    worlds_dir = tmp_path / "worlds"
    worlds_dir.mkdir(parents=True, exist_ok=True)
    (worlds_dir / "world_bible.json").write_text(
        json.dumps(
            {
                "world": {
                    "id": "world-new-meridian",
                    "name": "New Meridian",
                    "genre": "cyberpunk",
                    "tone": "investigative",
                    "premise": "Corporate blocs govern a vertical city-state.",
                    "calendar_mode": "real_time_daily",
                },
                "style_guide": {
                    "news_voice": "factual and skeptical",
                    "allowed_story_types": ["politics", "business", "culture"],
                    "taboos": ["out-of-world references"],
                },
                "continuity": {
                    "current_date": "2074-04-11",
                    "major_facts": [
                        {
                            "id": "fact-1",
                            "text": "The Meridian Council controls trade and media licenses.",
                            "tier": "core_canon",
                        }
                    ],
                    "rules": ["No supernatural powers."],
                },
                "locations": [
                    {
                        "id": "loc-1",
                        "name": "Meridian Central",
                        "type": "district",
                        "description": "Corporate core district.",
                        "confidence_tier": "core_canon",
                    }
                ],
                "organizations": [
                    {
                        "id": "org-1",
                        "name": "Meridian Council",
                        "type": "governing_consortium",
                        "description": "Ruling consortium.",
                        "confidence_tier": "core_canon",
                    }
                ],
                "people": [
                    {
                        "id": "person-1",
                        "name": "Vex",
                        "role": "Hacker icon",
                        "affiliation": "Free Circuit",
                        "status": "missing",
                        "confidence_tier": "established",
                    }
                ],
                "timeline": [
                    {
                        "id": "event-1",
                        "date": "2074-01-01",
                        "title": "Founding event",
                        "summary": "The world bible baseline is established.",
                        "confidence_tier": "core_canon",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["generate-news", "--date", "2026-04-11"])

    assert result.exit_code == 0
    assert "Generated 4 stories for 2026-04-11" in result.stdout
    assert (tmp_path / "stories" / "2026-04-11.json").exists()


def test_init_world_command_accepts_prompt_text(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_LLM_PROVIDER", "mock")

    result = runner.invoke(app, ["init-world", "--prompt", "A dense floating city ruled by data cartels."])

    assert result.exit_code == 0
    assert "Initialized world" in result.stdout
    assert (tmp_path / "worlds" / "world_bible.json").exists()
    assert (tmp_path / "worlds" / "world_bible.md").exists()


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

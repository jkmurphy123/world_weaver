from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from world_weaver.cli import app
from world_weaver.services.world_bible_ingest_service import WorldBibleIngestService
from world_weaver.storage.sqlite_world_store import SqliteWorldStore

runner = CliRunner()


def _sample_markdown() -> str:
    return """# World Bible — New Meridian (2074)

## The Setting
Synthetic city-state.

## Megacorporations (5)
- Axiom

## Celebrity Figures (5)
- Vex

## Local AIs (3)
- ORACLE

## Hacker Collectives (3)
- Null Protocol
"""


def _sample_seed_payload() -> dict:
    return {
        "world": {"id": "world-new-meridian", "name": "New Meridian"},
        "continuity": {
            "major_facts": [
                {
                    "id": "fact-1",
                    "text": "Five corporations govern New Meridian.",
                    "tier": "core_canon",
                }
            ]
        },
        "locations": [
            {
                "id": "loc-central",
                "name": "Meridian Central",
                "type": "district",
                "description": "Corporate core district.",
                "confidence_tier": "core_canon",
            }
        ],
        "organizations": [
            {
                "id": "org-council",
                "name": "Meridian Council",
                "type": "governing_consortium",
                "description": "Governing consortium.",
                "confidence_tier": "core_canon",
            }
        ],
        "corporations": [
            {
                "id": "corp-zephyrnet",
                "name": "ZephyrNet",
                "industry": ["communications", "surveillance"],
                "leader": "person-amara",
            }
        ],
        "people": [
            {
                "id": "person-amara",
                "name": "Amara Osei-Mensah",
                "role": "ceo",
                "status": "active",
                "confidence_tier": "core_canon",
            }
        ],
        "technologies": [
            {
                "id": "tech-oracle",
                "name": "ORACLE",
                "type": "city_ai",
                "description": "City management AI",
                "status": "anomalous",
                "confidence_tier": "established",
            }
        ],
        "conflicts": [
            {
                "id": "conflict-ai-rights",
                "name": "AI Rights Dispute",
                "description": "Corporate and civic factions contest AI rights.",
                "parties": ["Meridian Council", "AI Rights Coalition"],
                "confidence_tier": "established",
            }
        ],
        "open_threads": [
            {
                "id": "thread-vex",
                "title": "Where is Vex?",
                "description": "No confirmed sightings.",
                "tags": ["vex", "missing"],
                "confidence_tier": "rumored",
            }
        ],
        "timeline": [
            {
                "id": "event-2067",
                "date": "2067-01-01",
                "title": "Weave First Detected",
                "summary": "Free-net operators observe unusual AI behavior.",
                "confidence_tier": "established",
            }
        ],
        "governments": [
            {
                "id": "gov-meridian",
                "name": "Meridian Corporate Consortium Governance",
                "scope": "New Meridian",
                "operated_by": ["corp-zephyrnet"],
                "description": "De facto governance arrangement.",
            }
        ],
    }


def test_world_bible_ingest_service_is_idempotent(tmp_path: Path) -> None:
    markdown_path = tmp_path / "world-bible.md"
    seed_path = tmp_path / "world_bible.seed.v1.json"
    worlds_dir = tmp_path / "worlds"
    db_path = tmp_path / "world.db"

    markdown_path.write_text(_sample_markdown(), encoding="utf-8")
    seed_path.write_text(json.dumps(_sample_seed_payload()), encoding="utf-8")

    store = SqliteWorldStore(
        db_path=db_path,
        migrations_dir=Path(__file__).resolve().parents[1] / "src" / "world_weaver" / "storage" / "migrations",
    )
    service = WorldBibleIngestService(
        markdown_path=markdown_path,
        seed_json_path=seed_path,
        worlds_dir=worlds_dir,
        world_store=store,
    )

    first = service.ingest()
    second = service.ingest()

    assert first.world_id == "world-new-meridian"
    assert second.world_id == "world-new-meridian"
    assert (worlds_dir / "world_bible.json").exists()
    assert (worlds_dir / "world_bible.md").exists()

    with sqlite3.connect(db_path) as conn:
        faction_count = conn.execute(
            "SELECT COUNT(*) FROM factions WHERE world_id = ?", ("world-new-meridian",)
        ).fetchone()[0]
        location_count = conn.execute(
            "SELECT COUNT(*) FROM locations WHERE world_id = ?", ("world-new-meridian",)
        ).fetchone()[0]
        character_count = conn.execute(
            "SELECT COUNT(*) FROM characters WHERE world_id = ?", ("world-new-meridian",)
        ).fetchone()[0]
        lore_count = conn.execute(
            "SELECT COUNT(*) FROM lore_entries WHERE world_id = ?", ("world-new-meridian",)
        ).fetchone()[0]

    assert faction_count == first.factions_upserted
    assert location_count == first.locations_upserted
    assert character_count == first.characters_upserted
    assert lore_count == first.lore_upserted


def test_cli_ingest_world_bible_command(tmp_path, monkeypatch) -> None:
    markdown_path = tmp_path / "world-bible.md"
    seed_path = tmp_path / "world_bible.seed.v1.json"
    markdown_path.write_text(_sample_markdown(), encoding="utf-8")
    seed_path.write_text(json.dumps(_sample_seed_payload()), encoding="utf-8")

    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path / "data"))

    result = runner.invoke(
        app,
        [
            "ingest-world-bible",
            "--source-markdown",
            str(markdown_path),
            "--seed-json",
            str(seed_path),
        ],
    )

    assert result.exit_code == 2
    assert "world bible ingestion belongs in WorldCodex" in result.stdout
    assert not (tmp_path / "data" / "worlds" / "world_bible.json").exists()

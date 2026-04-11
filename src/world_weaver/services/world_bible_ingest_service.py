from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from world_weaver.storage.sqlite_world_store import SqliteWorldStore

CONFIDENCE_TO_INFLUENCE = {
    "core_canon": 90,
    "established": 70,
    "rumored": 45,
    "deprecated": 20,
}


@dataclass(frozen=True)
class IngestReport:
    world_id: str
    world_bible_path: Path
    world_markdown_path: Path
    factions_upserted: int
    locations_upserted: int
    characters_upserted: int
    lore_upserted: int


class WorldBibleIngestService:
    """Ingest a curated world bible markdown + mapped seed JSON into canonical files and SQLite entities."""

    def __init__(
        self,
        *,
        markdown_path: Path,
        seed_json_path: Path,
        worlds_dir: Path,
        world_store: SqliteWorldStore,
    ) -> None:
        self._markdown_path = markdown_path
        self._seed_json_path = seed_json_path
        self._worlds_dir = worlds_dir
        self._world_store = world_store

    def ingest(self, *, world_id_override: str | None = None) -> IngestReport:
        markdown = self._markdown_path.read_text(encoding="utf-8")
        self._validate_markdown(markdown)

        seed_payload = json.loads(self._seed_json_path.read_text(encoding="utf-8"))
        world = seed_payload.get("world", {})
        world_id = world_id_override or world.get("id") or "world-main"

        self._worlds_dir.mkdir(parents=True, exist_ok=True)
        world_bible_path = self._worlds_dir / "world_bible.json"
        world_markdown_path = self._worlds_dir / "world_bible.md"

        world_bible_path.write_text(json.dumps(seed_payload, indent=2), encoding="utf-8")
        world_markdown_path.write_text(markdown, encoding="utf-8")

        self._world_store.run_migrations()

        factions = self._build_factions(seed_payload)
        locations = self._build_locations(seed_payload)
        characters = self._build_characters(seed_payload)
        lore_entries = self._build_lore(seed_payload)

        with self._world_store.connection() as conn:
            self._upsert_factions(conn, world_id=world_id, rows=factions)
            self._upsert_locations(conn, world_id=world_id, rows=locations)
            self._upsert_characters(conn, world_id=world_id, rows=characters)
            self._upsert_lore(conn, world_id=world_id, rows=lore_entries)

        return IngestReport(
            world_id=world_id,
            world_bible_path=world_bible_path,
            world_markdown_path=world_markdown_path,
            factions_upserted=len(factions),
            locations_upserted=len(locations),
            characters_upserted=len(characters),
            lore_upserted=len(lore_entries),
        )

    @staticmethod
    def _validate_markdown(markdown: str) -> None:
        title_match = re.search(r"^#\s+World Bible\s+—\s+.+\(\d{4}\)", markdown, flags=re.MULTILINE)
        if not title_match:
            raise ValueError("World bible markdown is missing expected title format")
        required_sections = (
            "## The Setting",
            "## Megacorporations (5)",
            "## Celebrity Figures (5)",
            "## Local AIs (3)",
            "## Hacker Collectives (3)",
        )
        missing = [section for section in required_sections if section not in markdown]
        if missing:
            raise ValueError(f"World bible markdown is missing required sections: {', '.join(missing)}")

    @staticmethod
    def _build_factions(seed_payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        for corp in seed_payload.get("corporations", []):
            industry = corp.get("industry") or []
            ideology = ", ".join(industry) if industry else "corporate control"
            rows.append(
                {
                    "name": corp["name"],
                    "ideology": ideology,
                    "influence": 90,
                    "confidence_tier": "core_canon",
                }
            )

        for org in seed_payload.get("organizations", []):
            tier = org.get("confidence_tier") or "established"
            rows.append(
                {
                    "name": org["name"],
                    "ideology": (org.get("type") or "organization").replace("_", " "),
                    "influence": CONFIDENCE_TO_INFLUENCE.get(tier, 70),
                    "confidence_tier": tier,
                }
            )

        for gov in seed_payload.get("governments", []):
            rows.append(
                {
                    "name": gov["name"],
                    "ideology": "de_facto_governance",
                    "influence": 95,
                    "confidence_tier": "core_canon",
                }
            )

        deduped: dict[str, dict[str, Any]] = {}
        for row in rows:
            deduped[row["name"]] = row
        return list(deduped.values())

    @staticmethod
    def _build_locations(seed_payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for loc in seed_payload.get("locations", []):
            rows.append(
                {
                    "name": loc["name"],
                    "region": (loc.get("type") or "district").replace("_", " "),
                    "description": loc.get("description") or "No description provided",
                    "confidence_tier": loc.get("confidence_tier") or "established",
                }
            )
        return rows

    @staticmethod
    def _build_characters(seed_payload: dict[str, Any]) -> list[dict[str, Any]]:
        corp_by_leader_id: dict[str, str] = {}
        for corp in seed_payload.get("corporations", []):
            leader_id = corp.get("leader")
            if leader_id:
                corp_by_leader_id[leader_id] = corp.get("name") or "Independent"

        rows: list[dict[str, Any]] = []
        for person in seed_payload.get("people", []):
            person_id = person.get("id")
            affiliation = person.get("affiliation") or corp_by_leader_id.get(person_id) or "Independent"
            rows.append(
                {
                    "name": person["name"],
                    "role": person.get("role") or "figure",
                    "affiliation": affiliation,
                    "status": person.get("status") or "active",
                    "confidence_tier": person.get("confidence_tier") or "established",
                }
            )
        return rows

    @staticmethod
    def _build_lore(seed_payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        continuity = seed_payload.get("continuity", {})
        for fact in continuity.get("major_facts", []):
            if isinstance(fact, str):
                text = fact
                tier = "established"
                fact_id = f"fact-{abs(hash(text)) % 100000}"
            else:
                text = fact.get("text") or ""
                tier = fact.get("tier") or "established"
                fact_id = fact.get("id") or f"fact-{abs(hash(text)) % 100000}"
            rows.append(
                {
                    "title": f"Canon Fact: {fact_id}",
                    "body": text,
                    "tags": ["continuity", "major_fact"],
                    "confidence_tier": tier,
                }
            )

        for tech in seed_payload.get("technologies", []):
            body = tech.get("description") or ""
            if tech.get("status"):
                body = f"{body}\nStatus: {tech['status']}".strip()
            rows.append(
                {
                    "title": f"Technology: {tech['name']}",
                    "body": body,
                    "tags": ["technology", tech.get("type", "unknown")],
                    "confidence_tier": tech.get("confidence_tier") or "established",
                }
            )

        for conflict in seed_payload.get("conflicts", []):
            rows.append(
                {
                    "title": f"Conflict: {conflict['name']}",
                    "body": conflict.get("description") or "",
                    "tags": ["conflict", *(conflict.get("parties", []))],
                    "confidence_tier": conflict.get("confidence_tier") or "established",
                }
            )

        for thread in seed_payload.get("open_threads", []):
            rows.append(
                {
                    "title": f"Open Thread: {thread['title']}",
                    "body": thread.get("description") or "",
                    "tags": ["open_thread", *(thread.get("tags", []))],
                    "confidence_tier": thread.get("confidence_tier") or "rumored",
                }
            )

        for event in seed_payload.get("timeline", []):
            event_title = event.get("title") or event.get("id") or "Untitled Event"
            rows.append(
                {
                    "title": f"Timeline: {event_title}",
                    "body": f"Date: {event.get('date')}\n{event.get('summary', '')}".strip(),
                    "tags": ["timeline"],
                    "confidence_tier": event.get("confidence_tier") or "established",
                }
            )

        deduped: dict[str, dict[str, Any]] = {}
        for row in rows:
            deduped[row["title"]] = row
        return list(deduped.values())

    @staticmethod
    def _upsert_factions(conn: sqlite3.Connection, *, world_id: str, rows: list[dict[str, Any]]) -> None:
        conn.executemany(
            """
            INSERT INTO factions (world_id, name, ideology, influence, confidence_tier)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(world_id, name) DO UPDATE SET
                ideology = excluded.ideology,
                influence = excluded.influence,
                confidence_tier = excluded.confidence_tier,
                updated_at = datetime('now')
            """,
            [
                (world_id, row["name"], row["ideology"], row["influence"], row["confidence_tier"])
                for row in rows
            ],
        )

    @staticmethod
    def _upsert_locations(conn: sqlite3.Connection, *, world_id: str, rows: list[dict[str, Any]]) -> None:
        conn.executemany(
            """
            INSERT INTO locations (world_id, name, region, description, confidence_tier)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(world_id, name) DO UPDATE SET
                region = excluded.region,
                description = excluded.description,
                confidence_tier = excluded.confidence_tier,
                updated_at = datetime('now')
            """,
            [
                (world_id, row["name"], row["region"], row["description"], row["confidence_tier"])
                for row in rows
            ],
        )

    @staticmethod
    def _upsert_characters(conn: sqlite3.Connection, *, world_id: str, rows: list[dict[str, Any]]) -> None:
        conn.executemany(
            """
            INSERT INTO characters (world_id, name, role, affiliation, status, confidence_tier)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(world_id, name) DO UPDATE SET
                role = excluded.role,
                affiliation = excluded.affiliation,
                status = excluded.status,
                confidence_tier = excluded.confidence_tier,
                updated_at = datetime('now')
            """,
            [
                (
                    world_id,
                    row["name"],
                    row["role"],
                    row["affiliation"],
                    row["status"],
                    row["confidence_tier"],
                )
                for row in rows
            ],
        )

    @staticmethod
    def _upsert_lore(conn: sqlite3.Connection, *, world_id: str, rows: list[dict[str, Any]]) -> None:
        conn.executemany(
            """
            INSERT INTO lore_entries (world_id, title, body, tags, confidence_tier)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(world_id, title) DO UPDATE SET
                body = excluded.body,
                tags = excluded.tags,
                confidence_tier = excluded.confidence_tier,
                updated_at = datetime('now')
            """,
            [
                (
                    world_id,
                    row["title"],
                    row["body"],
                    json.dumps(row["tags"]),
                    row["confidence_tier"],
                )
                for row in rows
            ],
        )

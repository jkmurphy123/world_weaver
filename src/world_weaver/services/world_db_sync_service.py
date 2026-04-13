from __future__ import annotations

import sqlite3
from typing import Any

from world_weaver.schemas import WorldBible
from world_weaver.services.world_bible_ingest_service import WorldBibleIngestService
from world_weaver.storage.sqlite_world_store import SqliteWorldStore


class WorldDbSyncService:
    """Refresh the SQLite entity projection from the canonical world bible JSON shape."""

    def __init__(self, *, world_store: SqliteWorldStore) -> None:
        self._world_store = world_store

    def refresh_from_world_bible(self, world_bible: WorldBible, *, world_id_override: str | None = None) -> str:
        payload = world_bible.model_dump(mode="json")
        world = payload.get("world", {}) if isinstance(payload.get("world"), dict) else {}
        world_id = world_id_override or world.get("id") or "world-main"

        factions = WorldBibleIngestService._build_factions(payload)
        locations = WorldBibleIngestService._build_locations(payload)
        characters = WorldBibleIngestService._build_characters(payload)
        lore_entries = WorldBibleIngestService._build_lore(payload)

        self._world_store.run_migrations()
        with self._world_store.connection() as conn:
            self._refresh_factions(conn, world_id=world_id, rows=factions)
            self._refresh_locations(conn, world_id=world_id, rows=locations)
            self._refresh_characters(conn, world_id=world_id, rows=characters)
            self._refresh_lore(conn, world_id=world_id, rows=lore_entries)

        return world_id

    @staticmethod
    def _refresh_factions(conn: sqlite3.Connection, *, world_id: str, rows: list[dict[str, Any]]) -> None:
        WorldBibleIngestService._upsert_factions(conn, world_id=world_id, rows=rows)
        WorldDbSyncService._delete_stale_rows(conn, table="factions", world_id=world_id, key_column="name", rows=rows)

    @staticmethod
    def _refresh_locations(conn: sqlite3.Connection, *, world_id: str, rows: list[dict[str, Any]]) -> None:
        WorldBibleIngestService._upsert_locations(conn, world_id=world_id, rows=rows)
        WorldDbSyncService._delete_stale_rows(conn, table="locations", world_id=world_id, key_column="name", rows=rows)

    @staticmethod
    def _refresh_characters(conn: sqlite3.Connection, *, world_id: str, rows: list[dict[str, Any]]) -> None:
        WorldBibleIngestService._upsert_characters(conn, world_id=world_id, rows=rows)
        WorldDbSyncService._delete_stale_rows(conn, table="characters", world_id=world_id, key_column="name", rows=rows)

    @staticmethod
    def _refresh_lore(conn: sqlite3.Connection, *, world_id: str, rows: list[dict[str, Any]]) -> None:
        WorldBibleIngestService._upsert_lore(conn, world_id=world_id, rows=rows)
        WorldDbSyncService._delete_stale_rows(conn, table="lore_entries", world_id=world_id, key_column="title", rows=rows)

    @staticmethod
    def _delete_stale_rows(
        conn: sqlite3.Connection,
        *,
        table: str,
        world_id: str,
        key_column: str,
        rows: list[dict[str, Any]],
    ) -> None:
        keep_values = sorted(
            {
                str(row[key_column]).strip()
                for row in rows
                if key_column in row and str(row[key_column]).strip()
            }
        )
        if not keep_values:
            conn.execute(f"DELETE FROM {table} WHERE world_id = ?", (world_id,))
            return

        placeholders = ", ".join("?" for _ in keep_values)
        conn.execute(
            f"DELETE FROM {table} WHERE world_id = ? AND {key_column} NOT IN ({placeholders})",
            [world_id, *keep_values],
        )

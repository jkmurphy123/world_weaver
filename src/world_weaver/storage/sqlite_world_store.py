from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class SqliteWorldStore:
    def __init__(self, db_path: Path, migrations_dir: Path) -> None:
        self._db_path = db_path
        self._migrations_dir = migrations_dir
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def run_migrations(self) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
            for migration_path in sorted(self._migrations_dir.glob("*.sql")):
                version = migration_path.name
                if version in applied:
                    continue
                conn.executescript(migration_path.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))

    def connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn


class WorldEntityRepository:
    def __init__(self, store: SqliteWorldStore) -> None:
        self._store = store

    def list(self, table: str, world_id: str) -> list[dict[str, Any]]:
        with self._store.connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE world_id = ? ORDER BY id ASC",
                (world_id,),
            ).fetchall()
        return [self._deserialize_row(row) for row in rows]

    def get(self, table: str, world_id: str, entity_id: int) -> dict[str, Any] | None:
        with self._store.connection() as conn:
            row = conn.execute(
                f"SELECT * FROM {table} WHERE world_id = ? AND id = ?",
                (world_id, entity_id),
            ).fetchone()
        if row is None:
            return None
        return self._deserialize_row(row)

    def create(self, table: str, world_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        columns = ["world_id", *payload.keys()]
        placeholders = ", ".join("?" for _ in columns)
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"

        serialized = self._serialize_payload(payload)
        values = [world_id, *serialized.values()]

        with self._store.connection() as conn:
            cursor = conn.execute(sql, values)
            entity_id = cursor.lastrowid
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (entity_id,)).fetchone()

        return self._deserialize_row(row)

    def update(self, table: str, world_id: str, entity_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not payload:
            return self.get(table, world_id, entity_id)

        serialized = self._serialize_payload(payload)
        assignments = ", ".join(f"{key} = ?" for key in serialized)

        with self._store.connection() as conn:
            cursor = conn.execute(
                f"UPDATE {table} SET {assignments}, updated_at = datetime('now') WHERE world_id = ? AND id = ?",
                [*serialized.values(), world_id, entity_id],
            )
            if cursor.rowcount == 0:
                return None
            row = conn.execute(f"SELECT * FROM {table} WHERE world_id = ? AND id = ?", (world_id, entity_id)).fetchone()

        return self._deserialize_row(row)

    def delete(self, table: str, world_id: str, entity_id: int) -> bool:
        with self._store.connection() as conn:
            cursor = conn.execute(
                f"DELETE FROM {table} WHERE world_id = ? AND id = ?",
                (world_id, entity_id),
            )
            return cursor.rowcount > 0

    @staticmethod
    def _serialize_payload(payload: dict[str, Any]) -> dict[str, Any]:
        serialized = payload.copy()
        if "tags" in serialized:
            serialized["tags"] = json.dumps(serialized["tags"])
        return serialized

    @staticmethod
    def _deserialize_row(row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        if "tags" in payload and payload["tags"]:
            payload["tags"] = json.loads(payload["tags"])
        return payload

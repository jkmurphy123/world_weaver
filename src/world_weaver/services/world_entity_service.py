from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from world_weaver.storage.sqlite_world_store import WorldEntityRepository


@dataclass(frozen=True)
class EntityConfig:
    table: str
    unique_label: str


class WorldEntityService:
    def __init__(self, repository: WorldEntityRepository) -> None:
        self._repository = repository

    def list(self, config: EntityConfig, world_id: str) -> list[dict[str, Any]]:
        return self._repository.list(config.table, world_id)

    def get(self, config: EntityConfig, world_id: str, entity_id: int) -> dict[str, Any]:
        entity = self._repository.get(config.table, world_id, entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        return entity

    def create(self, config: EntityConfig, world_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._repository.create(config.table, world_id, payload)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                status_code=409,
                detail=f"{config.unique_label} already exists in this world",
            ) from exc

    def update(self, config: EntityConfig, world_id: str, entity_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            entity = self._repository.update(config.table, world_id, entity_id, payload)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                status_code=409,
                detail=f"{config.unique_label} already exists in this world",
            ) from exc
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        return entity

    def delete(self, config: EntityConfig, world_id: str, entity_id: int) -> None:
        deleted = self._repository.delete(config.table, world_id, entity_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Entity not found")

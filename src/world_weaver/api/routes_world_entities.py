from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI, Request, Response, status

from world_weaver.api.auth import require_api_token
from world_weaver.services.world_entity_service import EntityConfig, WorldEntityService
from world_weaver.world_entities import (
    CharacterCreate,
    CharacterRecord,
    CharacterUpdate,
    FactionCreate,
    FactionRecord,
    FactionUpdate,
    LocationCreate,
    LocationRecord,
    LocationUpdate,
    LoreEntryCreate,
    LoreEntryRecord,
    LoreEntryUpdate,
)

router = APIRouter(prefix="/api/world", tags=["world"], dependencies=[Depends(require_api_token)])

FACTION_CONFIG = EntityConfig(table="factions", unique_label="Faction")
LOCATION_CONFIG = EntityConfig(table="locations", unique_label="Location")
CHARACTER_CONFIG = EntityConfig(table="characters", unique_label="Character")
LORE_CONFIG = EntityConfig(table="lore_entries", unique_label="Lore entry")


def get_world_entity_service(request: Request) -> WorldEntityService:
    return request.app.state.world_entity_service


@router.get("/{world_id}/factions", response_model=list[FactionRecord])
def list_factions(world_id: str, service: WorldEntityService = Depends(get_world_entity_service)) -> list[FactionRecord]:
    return [FactionRecord.model_validate(item) for item in service.list(FACTION_CONFIG, world_id)]


@router.post("/{world_id}/factions", response_model=FactionRecord, status_code=status.HTTP_201_CREATED)
def create_faction(
    world_id: str,
    payload: FactionCreate,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> FactionRecord:
    return FactionRecord.model_validate(service.create(FACTION_CONFIG, world_id, payload.model_dump()))


@router.get("/{world_id}/factions/{entity_id}", response_model=FactionRecord)
def get_faction(
    world_id: str,
    entity_id: int,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> FactionRecord:
    return FactionRecord.model_validate(service.get(FACTION_CONFIG, world_id, entity_id))


@router.patch("/{world_id}/factions/{entity_id}", response_model=FactionRecord)
def update_faction(
    world_id: str,
    entity_id: int,
    payload: FactionUpdate,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> FactionRecord:
    return FactionRecord.model_validate(service.update(FACTION_CONFIG, world_id, entity_id, payload.model_dump(exclude_none=True)))


@router.delete("/{world_id}/factions/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faction(
    world_id: str,
    entity_id: int,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> Response:
    service.delete(FACTION_CONFIG, world_id, entity_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{world_id}/locations", response_model=list[LocationRecord])
def list_locations(world_id: str, service: WorldEntityService = Depends(get_world_entity_service)) -> list[LocationRecord]:
    return [LocationRecord.model_validate(item) for item in service.list(LOCATION_CONFIG, world_id)]


@router.post("/{world_id}/locations", response_model=LocationRecord, status_code=status.HTTP_201_CREATED)
def create_location(
    world_id: str,
    payload: LocationCreate,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> LocationRecord:
    return LocationRecord.model_validate(service.create(LOCATION_CONFIG, world_id, payload.model_dump()))


@router.get("/{world_id}/locations/{entity_id}", response_model=LocationRecord)
def get_location(
    world_id: str,
    entity_id: int,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> LocationRecord:
    return LocationRecord.model_validate(service.get(LOCATION_CONFIG, world_id, entity_id))


@router.patch("/{world_id}/locations/{entity_id}", response_model=LocationRecord)
def update_location(
    world_id: str,
    entity_id: int,
    payload: LocationUpdate,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> LocationRecord:
    return LocationRecord.model_validate(
        service.update(LOCATION_CONFIG, world_id, entity_id, payload.model_dump(exclude_none=True))
    )


@router.delete("/{world_id}/locations/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(
    world_id: str,
    entity_id: int,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> Response:
    service.delete(LOCATION_CONFIG, world_id, entity_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{world_id}/characters", response_model=list[CharacterRecord])
def list_characters(world_id: str, service: WorldEntityService = Depends(get_world_entity_service)) -> list[CharacterRecord]:
    return [CharacterRecord.model_validate(item) for item in service.list(CHARACTER_CONFIG, world_id)]


@router.post("/{world_id}/characters", response_model=CharacterRecord, status_code=status.HTTP_201_CREATED)
def create_character(
    world_id: str,
    payload: CharacterCreate,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> CharacterRecord:
    return CharacterRecord.model_validate(service.create(CHARACTER_CONFIG, world_id, payload.model_dump()))


@router.get("/{world_id}/characters/{entity_id}", response_model=CharacterRecord)
def get_character(
    world_id: str,
    entity_id: int,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> CharacterRecord:
    return CharacterRecord.model_validate(service.get(CHARACTER_CONFIG, world_id, entity_id))


@router.patch("/{world_id}/characters/{entity_id}", response_model=CharacterRecord)
def update_character(
    world_id: str,
    entity_id: int,
    payload: CharacterUpdate,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> CharacterRecord:
    return CharacterRecord.model_validate(
        service.update(CHARACTER_CONFIG, world_id, entity_id, payload.model_dump(exclude_none=True))
    )


@router.delete("/{world_id}/characters/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_character(
    world_id: str,
    entity_id: int,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> Response:
    service.delete(CHARACTER_CONFIG, world_id, entity_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{world_id}/lore", response_model=list[LoreEntryRecord])
def list_lore(world_id: str, service: WorldEntityService = Depends(get_world_entity_service)) -> list[LoreEntryRecord]:
    return [LoreEntryRecord.model_validate(item) for item in service.list(LORE_CONFIG, world_id)]


@router.post("/{world_id}/lore", response_model=LoreEntryRecord, status_code=status.HTTP_201_CREATED)
def create_lore(
    world_id: str,
    payload: LoreEntryCreate,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> LoreEntryRecord:
    return LoreEntryRecord.model_validate(service.create(LORE_CONFIG, world_id, payload.model_dump()))


@router.get("/{world_id}/lore/{entity_id}", response_model=LoreEntryRecord)
def get_lore(
    world_id: str,
    entity_id: int,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> LoreEntryRecord:
    return LoreEntryRecord.model_validate(service.get(LORE_CONFIG, world_id, entity_id))


@router.patch("/{world_id}/lore/{entity_id}", response_model=LoreEntryRecord)
def update_lore(
    world_id: str,
    entity_id: int,
    payload: LoreEntryUpdate,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> LoreEntryRecord:
    return LoreEntryRecord.model_validate(service.update(LORE_CONFIG, world_id, entity_id, payload.model_dump(exclude_none=True)))


@router.delete("/{world_id}/lore/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lore(
    world_id: str,
    entity_id: int,
    service: WorldEntityService = Depends(get_world_entity_service),
) -> Response:
    service.delete(LORE_CONFIG, world_id, entity_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def include_world_entity_routes(app: FastAPI) -> None:
    app.include_router(router)

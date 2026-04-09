from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ConfidenceTier = Literal["core_canon", "established", "rumored", "deprecated"]


class FactionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    ideology: str = Field(min_length=1, max_length=500)
    influence: int = Field(ge=0, le=100)
    confidence_tier: ConfidenceTier = "established"


class FactionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    ideology: str | None = Field(default=None, min_length=1, max_length=500)
    influence: int | None = Field(default=None, ge=0, le=100)
    confidence_tier: ConfidenceTier | None = None


class FactionRecord(FactionCreate):
    id: int
    world_id: str
    created_at: datetime
    updated_at: datetime


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    region: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    confidence_tier: ConfidenceTier = "established"


class LocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    region: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    confidence_tier: ConfidenceTier | None = None


class LocationRecord(LocationCreate):
    id: int
    world_id: str
    created_at: datetime
    updated_at: datetime


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=200)
    affiliation: str = Field(min_length=1, max_length=200)
    status: str = Field(min_length=1, max_length=100)
    confidence_tier: ConfidenceTier = "established"


class CharacterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    role: str | None = Field(default=None, min_length=1, max_length=200)
    affiliation: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = Field(default=None, min_length=1, max_length=100)
    confidence_tier: ConfidenceTier | None = None


class CharacterRecord(CharacterCreate):
    id: int
    world_id: str
    created_at: datetime
    updated_at: datetime


class LoreEntryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    tags: list[str] = Field(default_factory=list)
    confidence_tier: ConfidenceTier = "established"


class LoreEntryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1, max_length=5000)
    tags: list[str] | None = None
    confidence_tier: ConfidenceTier | None = None


class LoreEntryRecord(LoreEntryCreate):
    id: int
    world_id: str
    created_at: datetime
    updated_at: datetime

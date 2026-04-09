from datetime import date, datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app: str


class WorldMetadata(BaseModel):
    name: str
    genre: str
    tone: str
    seed: int
    generated_at: datetime


class Region(BaseModel):
    name: str
    climate: str
    landmarks: list[str] = Field(min_length=1)


class Faction(BaseModel):
    name: str
    ideology: str
    influence: int = Field(ge=1, le=100)


class WorldBible(BaseModel):
    metadata: WorldMetadata
    premise: str
    regions: list[Region] = Field(min_length=1)
    factions: list[Faction] = Field(min_length=1)
    story_hooks: list[str] = Field(min_length=1)


class StoryMetadata(BaseModel):
    story_id: str
    published_at: datetime
    target_date: date
    world_id: str


class Story(BaseModel):
    headline: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    body: str = Field(min_length=1)
    category: str = Field(min_length=1)
    metadata: StoryMetadata


class StoryBatch(BaseModel):
    date: date
    stories: list[Story] = Field(min_length=1)

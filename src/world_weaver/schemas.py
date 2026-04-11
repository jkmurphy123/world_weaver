from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

ConfidenceTier = Literal["core_canon", "established", "rumored", "deprecated"]


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


class WorldInfo(BaseModel):
    id: str
    name: str
    genre: str
    tone: str
    premise: str
    calendar_mode: str = "real_time_daily"


class StyleGuide(BaseModel):
    news_voice: str
    allowed_story_types: list[str] = Field(default_factory=list)
    taboos: list[str] = Field(default_factory=list)


class Continuity(BaseModel):
    current_date: date
    major_facts: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)


class CanonLocation(BaseModel):
    id: str
    name: str
    description: str
    confidence_tier: ConfidenceTier = "established"


class CanonOrganization(BaseModel):
    id: str
    name: str
    description: str
    confidence_tier: ConfidenceTier = "established"


class CanonPerson(BaseModel):
    id: str
    name: str
    role: str
    affiliation: str
    status: str
    confidence_tier: ConfidenceTier = "established"


class TimelineEvent(BaseModel):
    id: str
    date: date
    title: str
    summary: str
    confidence_tier: ConfidenceTier = "established"


class WorldBible(BaseModel):
    metadata: WorldMetadata
    premise: str
    regions: list[Region] = Field(min_length=1)
    factions: list[Faction] = Field(min_length=1)
    story_hooks: list[str] = Field(min_length=1)

    world: WorldInfo | None = None
    style_guide: StyleGuide | None = None
    continuity: Continuity | None = None
    locations: list[CanonLocation] = Field(default_factory=list)
    organizations: list[CanonOrganization] = Field(default_factory=list)
    people: list[CanonPerson] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)


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

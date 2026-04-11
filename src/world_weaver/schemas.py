import zlib
from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

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


class ContinuityFact(BaseModel):
    id: str | None = None
    text: str
    tier: ConfidenceTier = "established"


class Continuity(BaseModel):
    current_date: date
    major_facts: list[str | ContinuityFact] = Field(default_factory=list)
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
    affiliation: str = "Independent"
    status: str
    confidence_tier: ConfidenceTier = "established"

    @model_validator(mode="before")
    @classmethod
    def _normalize_affiliation(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        if payload.get("affiliation"):
            return payload

        affiliations = payload.get("affiliations")
        if isinstance(affiliations, list) and affiliations:
            payload["affiliation"] = str(affiliations[0])
        else:
            payload["affiliation"] = "Independent"
        return payload


class TimelineEvent(BaseModel):
    id: str
    date: date
    title: str
    summary: str
    confidence_tier: ConfidenceTier = "established"

    @model_validator(mode="before")
    @classmethod
    def _normalize_title(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        if payload.get("title"):
            return payload

        summary = payload.get("summary")
        if isinstance(summary, str) and summary.strip():
            payload["title"] = summary[:80].rstrip(".")
        else:
            payload["title"] = payload.get("id") or "Untitled Event"
        return payload


class WorldBible(BaseModel):
    metadata: WorldMetadata | None = None
    premise: str | None = None
    regions: list[Region] = Field(default_factory=list)
    factions: list[Faction] = Field(default_factory=list)
    story_hooks: list[str] = Field(default_factory=list)

    world: WorldInfo | None = None
    style_guide: StyleGuide | None = None
    continuity: Continuity | None = None
    locations: list[CanonLocation] = Field(default_factory=list)
    organizations: list[CanonOrganization] = Field(default_factory=list)
    people: list[CanonPerson] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _hydrate_legacy_fields_from_canonical_payload(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        payload = dict(value)
        world = payload.get("world") if isinstance(payload.get("world"), dict) else {}
        continuity = payload.get("continuity") if isinstance(payload.get("continuity"), dict) else {}
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        locations = payload.get("locations") if isinstance(payload.get("locations"), list) else []
        organizations = payload.get("organizations") if isinstance(payload.get("organizations"), list) else []
        corporations = payload.get("corporations") if isinstance(payload.get("corporations"), list) else []
        governments = payload.get("governments") if isinstance(payload.get("governments"), list) else []
        open_threads = payload.get("open_threads") if isinstance(payload.get("open_threads"), list) else []

        if world or metadata:
            seed_basis = (
                metadata.get("seed")
                if isinstance(metadata.get("seed"), int)
                else world.get("id") or world.get("name") or payload.get("premise") or "world-main"
            )
            payload["metadata"] = {
                "name": metadata.get("name") or world.get("name") or "Untitled World",
                "genre": metadata.get("genre") or world.get("genre") or "unknown",
                "tone": metadata.get("tone") or world.get("tone") or "neutral",
                "seed": seed_basis if isinstance(seed_basis, int) else zlib.crc32(str(seed_basis).encode("utf-8")),
                "generated_at": (
                    metadata.get("generated_at")
                    or cls._derive_generated_at(continuity=continuity, timeline=payload.get("timeline"))
                ),
            }

        if not payload.get("premise"):
            payload["premise"] = world.get("premise") or cls._derive_premise(continuity=continuity)

        if not payload.get("regions"):
            payload["regions"] = cls._derive_regions(locations)

        if not payload.get("factions"):
            payload["factions"] = cls._derive_factions(
                organizations=organizations,
                corporations=corporations,
                governments=governments,
            )

        if not payload.get("story_hooks"):
            payload["story_hooks"] = cls._derive_story_hooks(
                continuity=continuity,
                open_threads=open_threads,
                premise=payload.get("premise"),
            )

        return payload

    @model_validator(mode="after")
    def _validate_story_generation_basics(self) -> "WorldBible":
        if self.metadata is None:
            raise ValueError("World bible requires metadata")
        if not self.premise:
            raise ValueError("World bible requires premise")
        if not self.regions:
            raise ValueError("World bible requires at least one region")
        if not self.factions:
            raise ValueError("World bible requires at least one faction")
        if not self.story_hooks:
            raise ValueError("World bible requires at least one story hook")
        return self

    @staticmethod
    def _derive_generated_at(*, continuity: dict[str, Any], timeline: Any) -> str:
        current_date = continuity.get("current_date")
        if isinstance(current_date, str):
            return f"{current_date}T00:00:00+00:00"

        if isinstance(timeline, list):
            for event in timeline:
                if isinstance(event, dict) and isinstance(event.get("date"), str):
                    return f"{event['date']}T00:00:00+00:00"

        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _derive_premise(*, continuity: dict[str, Any]) -> str | None:
        major_facts = continuity.get("major_facts")
        if not isinstance(major_facts, list) or not major_facts:
            return None

        first_fact = major_facts[0]
        if isinstance(first_fact, str):
            return first_fact
        if isinstance(first_fact, dict):
            text = first_fact.get("text")
            return text if isinstance(text, str) and text.strip() else None
        return None

    @staticmethod
    def _derive_regions(locations: list[Any]) -> list[dict[str, Any]]:
        for location in locations:
            if not isinstance(location, dict):
                continue
            name = location.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            climate = location.get("type") or "unknown"
            return [
                {
                    "name": name,
                    "climate": str(climate).replace("_", " "),
                    "landmarks": [name],
                }
            ]
        return []

    @staticmethod
    def _derive_factions(
        *,
        organizations: list[Any],
        corporations: list[Any],
        governments: list[Any],
    ) -> list[dict[str, Any]]:
        candidates = [*organizations, *corporations, *governments]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            name = candidate.get("name")
            if not isinstance(name, str) or not name.strip():
                continue

            ideology_parts = candidate.get("industry") or candidate.get("type") or candidate.get("scope")
            if isinstance(ideology_parts, list):
                ideology = ", ".join(str(part) for part in ideology_parts if part)
            elif ideology_parts:
                ideology = str(ideology_parts).replace("_", " ")
            else:
                ideology = "institutional influence"

            confidence = candidate.get("confidence_tier")
            influence = 90 if confidence == "core_canon" else 70 if confidence == "established" else 50

            return [
                {
                    "name": name,
                    "ideology": ideology,
                    "influence": influence,
                }
            ]
        return []

    @staticmethod
    def _derive_story_hooks(
        *,
        continuity: dict[str, Any],
        open_threads: list[Any],
        premise: str | None,
    ) -> list[str]:
        for thread in open_threads:
            if not isinstance(thread, dict):
                continue
            title = thread.get("title")
            description = thread.get("description")
            if isinstance(title, str) and title.strip():
                if isinstance(description, str) and description.strip():
                    return [f"{title}: {description}"]
                return [title]

        major_facts = continuity.get("major_facts")
        if isinstance(major_facts, list):
            for fact in major_facts:
                if isinstance(fact, str) and fact.strip():
                    return [fact]
                if isinstance(fact, dict):
                    text = fact.get("text")
                    if isinstance(text, str) and text.strip():
                        return [text]

        if premise and premise.strip():
            return [premise]

        return []


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

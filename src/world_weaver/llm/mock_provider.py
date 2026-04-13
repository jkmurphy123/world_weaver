from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from world_weaver.llm.base import LLMProvider, PromptRequest


@dataclass(slots=True, frozen=True)
class ConnectionStatus:
    provider: str
    model: str
    message: str


class MockLLMProvider(LLMProvider):
    """Local deterministic provider for tests and development."""

    def generate_json(self, request: PromptRequest) -> str:
        normalized_prompt = request.system_prompt.lower()
        if "operator-provided canon note" in normalized_prompt:
            return self._generate_manual_canon_patch(request)
        if "canon update patch" in normalized_prompt:
            return self._generate_canon_patch(request)
        if "News Reporter" in request.system_prompt:
            return self._generate_story_batch(request)

        seed_prompt = request.user_prompt.strip() or "A synthetic coastal city balances power between guilds."
        world_name = _title_from_prompt(seed_prompt)
        slug = re.sub(r"[^a-z0-9]+", "-", world_name.lower()).strip("-") or "world-main"

        payload = {
            "world": {
                "id": slug,
                "name": world_name,
                "genre": "science fiction",
                "tone": "investigative",
                "premise": seed_prompt,
                "calendar_mode": "real_time_daily",
            },
            "style_guide": {
                "news_voice": "direct, factual, and city-beat focused",
                "allowed_story_types": ["politics", "business", "science", "culture"],
                "taboos": ["out-of-world references"],
            },
            "continuity": {
                "current_date": "2026-04-11",
                "major_facts": [
                    "A consortium of corporate blocs governs the city.",
                    "Class divisions are tied to physical district elevation.",
                ],
                "rules": ["No supernatural events.", "Technological change has social consequences."],
            },
            "locations": [
                {
                    "id": f"loc-{slug}-central",
                    "name": "Meridian Central",
                    "description": "Administrative and corporate district.",
                    "confidence_tier": "core_canon",
                },
                {
                    "id": f"loc-{slug}-stack",
                    "name": "The Stack",
                    "description": "Dense worker district with informal markets.",
                    "confidence_tier": "established",
                },
            ],
            "organizations": [
                {
                    "id": f"org-{slug}-council",
                    "name": "Meridian Council",
                    "description": "Consortium that sets policy and resource access.",
                    "confidence_tier": "core_canon",
                }
            ],
            "people": [
                {
                    "id": f"person-{slug}-editor",
                    "name": "Elara Quinn",
                    "role": "Investigative editor",
                    "affiliation": "Meridian Council Press Desk",
                    "status": "active",
                    "confidence_tier": "established",
                }
            ],
            "timeline": [
                {
                    "id": f"event-{slug}-founding",
                    "date": "2074-01-12",
                    "title": "Council charter ratified",
                    "summary": "The council formally consolidated administrative control.",
                    "confidence_tier": "core_canon",
                }
            ],
            "metadata": {
                "name": world_name,
                "genre": "science fiction",
                "tone": "investigative",
                "seed": 42,
                "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            },
            "premise": seed_prompt,
            "regions": [
                {"name": "Central Arcology", "climate": "humid tropical", "landmarks": ["Council Apex"]}
            ],
            "factions": [
                {
                    "name": "Meridian Council",
                    "ideology": "stability through managed information",
                    "influence": 84,
                }
            ],
            "story_hooks": [
                "Council reforms trigger unrest as independent reporters expose corruption."
            ],
        }

        return json.dumps(payload)

    def check_connection(self, model: str) -> ConnectionStatus:
        return ConnectionStatus(
            provider="mock",
            model=model,
            message="Mock provider is available locally",
        )

    def _generate_story_batch(self, request: PromptRequest) -> str:
        now = datetime.now(tz=timezone.utc)
        categories = ["politics", "business", "science", "culture", "world"]

        try:
            input_payload = json.loads(request.user_prompt)
        except json.JSONDecodeError:
            input_payload = {}

        target_date = str(input_payload.get("target_date", now.date().isoformat()))
        story_count = int(input_payload.get("story_count", 4))
        world_bible = input_payload.get("world_bible", {})
        world_id = world_bible.get("world", {}).get("id", "world-main")
        organizations = world_bible.get("organizations", [])
        locations = world_bible.get("locations", [])
        story_hooks = world_bible.get("story_hooks", [])

        org_name = organizations[0]["name"] if organizations else "Civic Council"
        location_name = locations[0]["name"] if locations else "Central District"
        hook = story_hooks[0] if story_hooks else "A policy shift exposes new fault lines."

        stories = []
        for index in range(1, story_count + 1):
            category = categories[(index - 1) % len(categories)]
            story_id = f"story-{target_date}-{index:03d}"
            stories.append(
                {
                    "headline": f"{org_name} announces changes across {location_name}",
                    "summary": f"Officials and residents in {location_name} react to new directives.",
                    "body": (
                        f"{hook} Field reporting indicates unfolding consequences tied to "
                        f"decision cycle {index}."
                    ),
                    "category": category,
                    "referenced_entities": [org_name, location_name],
                    "continuity_effects": [
                        f"{org_name} introduced a durable policy change affecting {location_name}.",
                        f"Public reaction in {location_name} suggests the fallout may drive more coverage.",
                    ],
                    "metadata": {
                        "story_id": story_id,
                        "published_at": now.isoformat(),
                        "target_date": target_date,
                        "world_id": world_id,
                    },
                }
            )

        return json.dumps({"date": target_date, "stories": stories})

    def _generate_canon_patch(self, request: PromptRequest) -> str:
        now = datetime.now(tz=timezone.utc)

        try:
            input_payload = json.loads(request.user_prompt)
        except json.JSONDecodeError:
            input_payload = {}

        target_date = str(input_payload.get("target_date", now.date().isoformat()))
        story_batch = input_payload.get("story_batch", {})
        stories = story_batch.get("stories", []) if isinstance(story_batch, dict) else []
        world_bible = input_payload.get("world_bible", {}) if isinstance(input_payload, dict) else {}
        open_threads = world_bible.get("open_threads", []) if isinstance(world_bible, dict) else []

        first_story = stories[0] if stories else {}
        headline = str(first_story.get("headline", "City desk tracks a developing shift"))
        summary = str(first_story.get("summary", "A consequential development is unfolding."))
        continuity_effects = first_story.get("continuity_effects", [])
        first_effect = (
            str(continuity_effects[0])
            if isinstance(continuity_effects, list) and continuity_effects and isinstance(continuity_effects[0], str)
            else summary
        )

        patch_payload = {
            "date": target_date,
            "new_people": [],
            "updated_people": [],
            "new_organizations": [],
            "updated_organizations": [],
            "new_locations": [],
            "updated_locations": [],
            "timeline_events": [
                {
                    "id": f"event-{target_date}-001",
                    "date": target_date,
                    "title": headline,
                    "summary": summary,
                    "confidence_tier": "established",
                }
            ],
            "open_threads_added": [
                {
                    "id": f"thread-{target_date}-001",
                    "title": f"Follow-up: {headline[:60]}",
                    "description": first_effect,
                    "status": "open",
                    "confidence_tier": "established",
                }
            ],
            "open_threads_resolved": [
                thread.get("id")
                for thread in open_threads
                if isinstance(thread, dict) and thread.get("status") == "resolved"
            ],
            "major_facts_added": [],
            "continuity_warnings": [],
        }

        return json.dumps(patch_payload)

    def _generate_manual_canon_patch(self, request: PromptRequest) -> str:
        now = datetime.now(tz=timezone.utc)

        try:
            input_payload = json.loads(request.user_prompt)
        except json.JSONDecodeError:
            input_payload = {}

        target_date = str(input_payload.get("target_date", now.date().isoformat()))
        source_text = str(input_payload.get("source_text", "")).strip()

        org_name = _extract_named_phrase(source_text, pattern=r"(?:called|named)\s+([A-Z][A-Za-z0-9]+(?: [A-Z][A-Za-z0-9]+){0,4})")
        if org_name is None and any(keyword in source_text.lower() for keyword in ("corporation", "company", "consortium")):
            org_name = _extract_named_phrase(source_text, pattern=r"([A-Z][A-Za-z0-9]+(?: [A-Z][A-Za-z0-9]+){0,4})")

        location_name = _extract_named_phrase(
            source_text,
            pattern=r"(?:in|at|from|based in|headquartered in)\s+([A-Z][A-Za-z0-9]+(?: [A-Z][A-Za-z0-9]+){0,4})",
        )
        person_name = _extract_named_phrase(
            source_text,
            pattern=r"(?:led by|run by|headed by)\s+([A-Z][a-z]+(?: [A-Z][a-z]+)+)",
        )

        title = source_text.split(".")[0].strip() if source_text else "Manual canon note ingested"
        title = title[:80] if title else "Manual canon note ingested"

        patch_payload = {
            "date": target_date,
            "new_people": [],
            "updated_people": [],
            "new_organizations": [],
            "updated_organizations": [],
            "new_locations": [],
            "updated_locations": [],
            "timeline_events": [
                {
                    "id": f"event-manual-{target_date}-001",
                    "date": target_date,
                    "title": title,
                    "summary": source_text or "Operator note added to canon.",
                    "confidence_tier": "established",
                }
            ],
            "open_threads_added": [],
            "open_threads_resolved": [],
            "major_facts_added": [
                {
                    "id": f"fact-manual-{target_date}-001",
                    "text": source_text or "Operator note added to canon.",
                    "tier": "established",
                }
            ],
            "continuity_warnings": [],
        }

        if org_name:
            patch_payload["new_organizations"].append(
                {
                    "id": f"org-{_slugify(org_name)}",
                    "name": org_name,
                    "description": source_text or f"{org_name} is now part of canon.",
                    "confidence_tier": "established",
                }
            )
        if location_name:
            patch_payload["new_locations"].append(
                {
                    "id": f"loc-{_slugify(location_name)}",
                    "name": location_name,
                    "description": f"Location referenced in operator note: {source_text}",
                    "confidence_tier": "established",
                }
            )
        if person_name:
            patch_payload["new_people"].append(
                {
                    "id": f"person-{_slugify(person_name)}",
                    "name": person_name,
                    "role": "canon contributor note subject",
                    "affiliation": org_name or "Independent",
                    "status": "active",
                    "confidence_tier": "established",
                }
            )

        if not source_text:
            patch_payload["timeline_events"] = []
            patch_payload["major_facts_added"] = []

        return json.dumps(patch_payload)


def _title_from_prompt(seed_prompt: str) -> str:
    words = [word for word in re.findall(r"[A-Za-z0-9']+", seed_prompt) if word]
    if not words:
        return "New Meridian"
    return " ".join(words[:3]).title() + " World"


def _extract_named_phrase(source_text: str, *, pattern: str) -> str | None:
    match = re.search(pattern, source_text)
    if not match:
        return None
    candidate = match.group(1).strip(" ,.;:")
    return candidate or None


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"

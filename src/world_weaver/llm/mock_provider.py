from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from world_weaver.llm.base import LLMProvider, PromptRequest


class MockLLMProvider(LLMProvider):
    """Local deterministic provider for tests and development."""

    def generate_json(self, request: PromptRequest) -> str:
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
                    "metadata": {
                        "story_id": story_id,
                        "published_at": now.isoformat(),
                        "target_date": target_date,
                        "world_id": world_id,
                    },
                }
            )

        return json.dumps({"date": target_date, "stories": stories})


def _title_from_prompt(seed_prompt: str) -> str:
    words = [word for word in re.findall(r"[A-Za-z0-9']+", seed_prompt) if word]
    if not words:
        return "New Meridian"
    return " ".join(words[:3]).title() + " World"

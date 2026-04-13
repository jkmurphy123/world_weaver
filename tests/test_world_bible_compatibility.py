from world_weaver.schemas import WorldBible


def test_world_bible_accepts_legacy_open_threads_without_description() -> None:
    payload = {
        "world": {
            "id": "world-new-meridian",
            "name": "New Meridian",
            "genre": "cyberpunk",
            "tone": "investigative",
            "premise": "Corporate blocs govern a vertical city-state.",
            "calendar_mode": "real_time_daily",
        },
        "style_guide": {
            "news_voice": "factual and skeptical",
            "allowed_story_types": ["politics", "business", "culture"],
            "taboos": ["out-of-world references"],
        },
        "continuity": {
            "current_date": "2074-04-11",
            "major_facts": [
                {
                    "id": "fact-1",
                    "text": "The Meridian Council controls trade and media licenses.",
                    "tier": "core_canon",
                }
            ],
            "rules": ["No supernatural powers."],
        },
        "locations": [
            {
                "id": "loc-1",
                "name": "Meridian Central",
                "description": "Corporate core district.",
                "confidence_tier": "core_canon",
            }
        ],
        "organizations": [
            {
                "id": "org-1",
                "name": "Meridian Council",
                "description": "Ruling consortium.",
                "confidence_tier": "core_canon",
            }
        ],
        "people": [
            {
                "id": "person-1",
                "name": "Vex",
                "role": "Hacker icon",
                "affiliation": "Free Circuit",
                "status": "missing",
                "confidence_tier": "established",
            }
        ],
        "open_threads": [
            {
                "id": "thread-vex-missing",
                "title": "Where is Vex?",
                "confidence_tier": "rumored",
            },
            {
                "id": "thread-oracle-pause",
                "summary": "The city AI paused several routines without explanation.",
                "confidence_tier": "established",
            },
        ],
        "timeline": [
            {
                "id": "event-1",
                "date": "2074-01-01",
                "title": "Founding event",
                "summary": "The world bible baseline is established.",
                "confidence_tier": "core_canon",
            }
        ],
    }

    world = WorldBible.model_validate(payload)

    assert world.open_threads[0].title == "Where is Vex?"
    assert world.open_threads[0].description == "Where is Vex?"
    assert world.open_threads[1].title == "The city AI paused several routines without explanation."
    assert world.open_threads[1].description == "The city AI paused several routines without explanation."

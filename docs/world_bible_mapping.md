# Milestone 2 World Bible Baseline and Mapping Notes

This document defines the canonical baseline structure for `world_bible.json`, maps source markdown content into structured fields, and records assumptions/gaps for implementation handoff.

## 1. Canonical Baseline Structure

Top-level shape for `world_bible.json`:

```json
{
  "world": {},
  "style_guide": {},
  "continuity": {},
  "locations": [],
  "organizations": [],
  "governments": [],
  "corporations": [],
  "people": [],
  "technologies": [],
  "conflicts": [],
  "open_threads": [],
  "timeline": []
}
```

Required minimum for Milestone 2 seeding:

- `world`, `style_guide`, `continuity` fully populated.
- At least one item each in `people`, `organizations`, `locations`, `timeline`.
- Stable string IDs for every entity (`person-*`, `corp-*`, `loc-*`, `event-*`, etc.).
- Every uncertain claim tagged with `confidence_tier: rumored` (or equivalent fact-tier field).

Seed artifact produced from this mapping:

- `data/worlds/world_bible.seed.v1.json`

## 2. Field-Level Mapping From Source Markdown

Source file: `data/world-bible.md`.

| Canon field | Source section(s) | Mapping rule |
| --- | --- | --- |
| `world.name` | Title + "The Setting" | Use city/world name "New Meridian"; keep full legal name as alias in location entry. |
| `world.genre` | Entire document tone | Infer "Cyberpunk corporate dystopia" from corporate rule + surveillance + augment economy. |
| `world.tone` | News angle bullets + archetypes | Set editorial tone for downstream reporter style. |
| `world.premise` | "The Setting" paragraph | Condense into one canonical premise sentence. |
| `world.calendar_mode` | AGENTS.md contract | Hard-code `real_time_daily` for daily-run pipeline semantics. |
| `style_guide.news_voice` | Document framing and story categories | Encode newsroom voice constraints as text. |
| `style_guide.allowed_story_types` | "Story Template Categories" | Convert G1/G2 and L1-L8 into normalized slugs. |
| `continuity.current_date` | Year marker (2074) | Set deterministic baseline date (`2074-01-01`) for first structured snapshot. |
| `continuity.major_facts` | "The Setting" + corp summaries + AI status | Keep only high-stability facts as canon anchors. |
| `locations[]` | Setting and HQ references | Create normalized location entities for districts, macro-zone, and key micro-site (K-7). |
| `corporations[]` | "Megacorporations (5)" | One entity per corp with IDs, industries, HQ, leader reference, known-for bullets. |
| `people[]` | "Celebrity Figures (5)" + CEO names in corp section | Include both celebrities and named corporate leaders; dedupe Priya as one person entity. |
| `organizations[]` | "Hacker Collectives (3)" + implied groups | Store non-corporate groups (Meridian Council, Drift Council, Circuit Monks, gangs, hacker cells). |
| `governments[]` | "No government" + Council governance statement | Model governance as de facto corporate consortium object. |
| `technologies[]` | Corp known-for + Local AIs section | Promote key systems/protocols (ORACLE, MCS, NeuLink, Upgrade, The Weave, MIRA). |
| `conflicts[]` | News angles + archetypes + known tensions | Seed baseline persistent conflicts for continuity checks and story grounding. |
| `open_threads[]` | Missing persons, rumors, anomalies | Capture unresolved narrative hooks separately from hard facts. |
| `timeline[]` | Dated events in narrative (2067/2071/2072/2073/2074) | Normalize to dated events; use estimated day/month where not provided. |

## 3. Engineering Assumptions and Gaps

Assumptions applied for seed conversion:

- Exact day/month values are absent for most historical events; placeholders use `YYYY-01-01` except Vex disappearance (`2073-06-01`) to preserve ordering semantics.
- `Red Lotus Syndicate` appears in archetypes but lacks profile details; seeded as `rumored` organization.
- Several entities are inferred from context (`Drift Council`, `Circuit Monks`) because they are operationally referenced in the source text.
- AIs are represented under `technologies` for Milestone 2 simplicity; later milestones can split into dedicated `ai_entities` if needed.

Known gaps for Milestone 2 implementation:

- No formal JSON Schema/Pydantic model exists yet for the full canonical structure (current codebase still uses the simpler `metadata/regions/factions` model).
- Relationship fields are intentionally lightweight and may need normalized foreign-key tables in later SQLite migration(s).
- Confidence-tier typing should be centralized as an enum in schema code before merge/continuity logic lands.

## 4. Handoff Guidance for Engineering

Use the seed JSON as the fixture source for Milestone 2 world-generation tests and parser validation.

Recommended order for implementation handoff:

1. Define Pydantic models mirroring this top-level structure.
2. Add strict enum validation for confidence tiers (`core_canon`, `established`, `rumored`, `deprecated`).
3. Add loader/saver service for `data/worlds/world_bible.json`.
4. Add deterministic ID helpers and uniqueness checks.
5. Add migration path from current `WorldBible` model to new canonical shape.

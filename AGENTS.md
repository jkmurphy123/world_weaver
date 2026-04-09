# AGENTS.md

## Project: Fictional News Feed World Simulator

Build a Python application that generates a **fictional daily news feed** for a synthetic world and exposes it as a standard RSS/Atom feed that can be consumed by common feed readers.

The system revolves around two AI roles:

1. **World Architect**

   * Creates and maintains the canonical world model, called the **world bible**.
   * Incorporates lasting changes from generated stories back into the canon.

2. **News Reporter**

   * Reads the current world bible.
   * Produces a daily batch of news stories set in that world.

The key loop is:

1. User provides initial world seed ideas.
2. World Architect generates the initial world bible.
3. News Reporter generates today’s fictional news stories.
4. World Architect reads those stories and produces structured updates to the world bible.
5. Feed publisher emits the current stories as RSS/Atom.
6. The loop repeats daily, allowing the world to evolve over time.

The design goal is to keep the system modular, testable, deterministic where practical, and easy to extend.

---

## High-Level Product Goal

Create a local-first application that:

* generates an initial fictional world from user prompts
* generates daily fictional news articles from that world
* updates the world over time based on those stories
* publishes the stories as a standard feed URL
* supports later extension to multiple worlds, editorial styles, review workflows, and alternate LLM providers

This is **not** a generic news reader. It is a **fictional newsroom simulation engine** with feed output.

---

## Core Design Principles

1. **Structured canon first**

   * The world bible must be stored as structured JSON.
   * A markdown summary may be generated for humans, but JSON is the source of truth.

2. **Patch-based updates**

   * The World Architect must not rewrite the whole world bible every day.
   * It should instead produce structured update patches that are merged into the canon.

3. **Reporter cannot directly edit canon**

   * The News Reporter generates stories only.
   * Only the World Architect plus merge logic can update canon.

4. **Deterministic storage and IDs**

   * Stories, entities, and snapshots should use stable IDs where possible.
   * Daily runs should be archived for debugging and rollback.

5. **Validation everywhere**

   * LLM outputs must be validated against schemas.
   * Invalid outputs should be retried or rejected with clear logs.

6. **Minimal but expandable MVP**

   * The first version should prove the full daily loop with as little UI and infrastructure as possible.

---

## Recommended Tech Stack

Use Python unless there is a very strong reason otherwise.

### Required

* Python 3.11+
* FastAPI for HTTP endpoints
* Pydantic for schemas and validation
* SQLite for persistence in early milestones
* A small LLM provider abstraction layer
* RSS and Atom feed generation
* Pytest for tests

### Suggested

* SQLModel or SQLAlchemy for persistence layer
* APScheduler for scheduled jobs
* Jinja2 or a simple XML builder for feed rendering
* Typer for CLI commands
* structlog or standard logging with JSON-friendly log format

---

## Repository Goals

Codex should create a repository that is:

* easy to run locally
* testable milestone by milestone
* modular enough to support future alternate UIs
* able to swap LLM backends later
* clear enough that a human can inspect and debug outputs

---

## Functional Requirements

### The system must support:

* creating a new world from a user seed prompt
* storing the world as a structured world bible
* generating a daily batch of fictional stories
* storing stories by date
* exposing current stories via RSS and Atom
* generating a structured canon update patch from a story batch
* merging the update patch into the world bible
* archiving snapshots of stories and canon
* validating continuity and logging conflicts

### The system should support later:

* admin review UI
* multi-world support
* configurable story counts and category weights
* configurable editorial tone
* manual approval before publishing
* local LLM and cloud LLM provider options

---

## Non-Functional Requirements

* The codebase should prioritize readability and modularity over cleverness.
* Each milestone should be independently runnable and testable.
* All file formats should be explicit and documented.
* LLM prompts should be stored in dedicated prompt files or prompt modules, not buried in business logic.
* Storage should be simple enough to inspect by hand.
* The app should be able to run entirely on one machine.

---

## Canonical Domain Model

The application revolves around these conceptual objects.

### 1. World Bible

The canonical structured representation of the fictional world.

Suggested fields:

```json
{
  "world": {
    "id": "world-main",
    "name": "string",
    "genre": "string",
    "tone": "string",
    "premise": "string",
    "calendar_mode": "real_time_daily"
  },
  "style_guide": {
    "news_voice": "string",
    "allowed_story_types": [],
    "taboos": []
  },
  "continuity": {
    "current_date": "YYYY-MM-DD",
    "major_facts": [],
    "rules": []
  },
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

### 2. Story

A single news item for a publication day.

Suggested fields:

```json
{
  "id": "story-2026-04-09-001",
  "date": "2026-04-09",
  "headline": "string",
  "summary": "string",
  "body": "string",
  "category": "politics",
  "byline": "string",
  "dateline": "string",
  "tags": [],
  "importance": 3,
  "referenced_entities": [],
  "continuity_effects": []
}
```

### 3. Story Batch

A collection of stories for a single day.

Suggested fields:

```json
{
  "date": "2026-04-09",
  "edition": "morning",
  "stories": []
}
```

### 4. Canon Update Patch

A structured set of changes inferred from a story batch.

Suggested fields:

```json
{
  "date": "2026-04-09",
  "new_people": [],
  "updated_people": [],
  "new_organizations": [],
  "updated_organizations": [],
  "new_locations": [],
  "updated_locations": [],
  "timeline_events": [],
  "new_conflicts": [],
  "updated_conflicts": [],
  "open_threads_added": [],
  "open_threads_resolved": [],
  "continuity_warnings": []
}
```

### 5. Snapshot

An archived record of a generation cycle.

Suggested fields:

* world snapshot path
* story batch path
* update patch path
* feed generation status
* validation results
* timestamp

---

## Required Project Structure

Codex should create a structure close to this:

```text
fictional_newsroom/
  AGENTS.md
  README.md
  pyproject.toml
  .env.example
  app/
    __init__.py
    config.py
    main.py
    logging.py
    schemas/
      world.py
      story.py
      patch.py
      feed.py
    prompts/
      world_architect_initial.md
      reporter_daily.md
      world_architect_patch.md
    llm/
      base.py
      openai_provider.py
      ollama_provider.py
      factory.py
    services/
      world_service.py
      story_service.py
      patch_service.py
      merge_service.py
      continuity_service.py
      feed_service.py
      scheduler_service.py
    storage/
      file_store.py
      sqlite_store.py
    api/
      routes_health.py
      routes_feed.py
      routes_story.py
      routes_world.py
    cli/
      __init__.py
      app.py
    utils/
      ids.py
      dates.py
      xml.py
  data/
    worlds/
    stories/
    feeds/
    snapshots/
    logs/
  tests/
    test_schemas.py
    test_world_generation.py
    test_story_generation.py
    test_patch_merge.py
    test_feed_output.py
    test_continuity.py
```

Exact naming can vary slightly, but separation of concerns should stay intact.

---

## Main Runtime Flows

### Flow A: Create Initial World

1. User provides seed prompt and optional settings.
2. System calls World Architect prompt.
3. Output is validated against world bible schema.
4. Valid world bible is saved.
5. Human-readable markdown summary is optionally generated.

### Flow B: Generate Daily Edition

1. Load current world bible.
2. Determine target publication date.
3. Call News Reporter prompt.
4. Validate story batch.
5. Save story batch.
6. Publish feed output.

### Flow C: Update Canon From Stories

1. Load current world bible.
2. Load story batch for target date.
3. Call World Architect patch prompt.
4. Validate patch.
5. Run continuity checks.
6. Merge patch into world bible.
7. Save updated world bible.
8. Archive snapshot.

### Flow D: Scheduled Daily Run

1. Generate daily stories.
2. Publish feed.
3. Generate canon patch.
4. Validate and merge.
5. Save snapshot and logs.

---

## LLM Role Definitions

### World Architect

Responsibilities:

* create initial world bible from seed ideas
* derive structured updates from stories
* preserve internal consistency
* classify uncertain items as rumors or open threads when needed

Rules:

* must return schema-conforming JSON only
* must not generate prose outside the response schema
* must not rewrite unrelated sections of canon during patch generation
* should prefer updating existing entities when the match is strong
* should emit warnings rather than forcing ambiguous merges

### News Reporter

Responsibilities:

* generate interesting daily news stories grounded in the world bible
* vary categories and story types
* reference existing canon when possible
* introduce new entities only when narratively justified

Rules:

* must return schema-conforming JSON only
* must not directly modify canon
* should include referenced entity IDs or names when known
* should balance major events with smaller human-interest or background stories
* should avoid collapsing the world into only crisis content unless configured to do so

---

## Editorial and Continuity Rules

Implement these guardrails early.

### Story Mix Rules

Default daily edition should aim for:

* 1 major story
* 2 medium stories
* 1 smaller color story or human-interest item
* optional rumor, culture, science, or business story depending on settings

### Continuity Rules

The continuity service should flag issues such as:

* dead or retired figures acting contrary to canon without explanation
* organizations changing name or status without transition
* duplicate entities with near-identical names
* timeline events that appear to go backward
* world rules being violated
* new story claims that conflict with major canon facts

### Canon Confidence Tiers

Allow facts or entities to be categorized as:

* core_canon
* established
* rumored
* deprecated

This lets the world evolve without requiring every detail to be maximally fixed.

---

## Feed Requirements

The application must expose at least:

* `GET /health`
* `GET /feed/rss.xml`
* `GET /feed/atom.xml`
* `GET /stories/today`
* `GET /world/summary`

### Feed behavior

* The RSS and Atom feeds should publish the latest available daily story batch.
* Each story item should have a stable GUID or ID.
* Publication dates must be valid and consistently formatted.
* Feed output should validate in common feed readers.

---

## CLI Requirements

Use Typer or similar to provide a simple command-line interface.

Suggested commands:

```text
newsroom init-world
newsroom generate-news --date YYYY-MM-DD
newsroom update-world --date YYYY-MM-DD
newsroom publish-feed
newsroom run-daily --date YYYY-MM-DD
newsroom serve
```

Optional later commands:

```text
newsroom validate-world
newsroom show-story --date YYYY-MM-DD --id STORY_ID
newsroom export-world-md
newsroom list-snapshots
```

---

## Persistence Strategy

### Early milestones

Use file-based JSON storage plus optional SQLite metadata.

Suggested files:

```text
data/worlds/world_bible.json
data/worlds/world_bible.md
data/stories/2026-04-09.json
data/feeds/rss.xml
data/feeds/atom.xml
data/snapshots/2026-04-09/
  world_before.json
  stories.json
  patch.json
  world_after.json
  validation_report.json
```

### Design expectation

Abstract storage behind service interfaces so the project can later move to a database-backed approach without rewriting business logic.

---

## Configuration Requirements

Create a central config model that supports:

* app host/port
* default world ID
* default publication time
* story count per day
* story category weights
* editorial tone
* LLM provider selection
* model name
* API base URL and keys as needed
* file storage paths
* scheduler enable/disable

Example env variables:

```text
APP_HOST=127.0.0.1
APP_PORT=8000
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1
OPENAI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_STORY_COUNT=4
DEFAULT_WORLD_ID=world-main
```

---

## Testing Requirements

Codex must create tests from the beginning.

### Required test categories

#### Schema tests

* validate good sample payloads
* reject malformed payloads

#### World generation tests

* verify the initial world creation pipeline saves valid output
* verify markdown summary generation works if included

#### Story generation tests

* verify a daily story batch is created and validated
* verify stories contain required feed fields

#### Patch and merge tests

* verify patch generation output shape
* verify merge logic updates canon correctly
* verify unchanged data is preserved

#### Feed tests

* verify RSS renders valid XML
* verify Atom renders valid XML
* verify story items appear correctly in feed output

#### Continuity tests

* verify duplicate entity detection
* verify contradiction detection for simple cases

#### CLI/API smoke tests

* verify basic commands run
* verify `/health` works
* verify feed endpoints return XML

Use mocked LLM outputs for most tests. Avoid hitting real providers in default test runs.

---

## Logging and Debugging Requirements

The application must log:

* prompt invocation start and finish
* validation successes/failures
* file save paths
* merge results
* continuity warnings
* feed generation events
* scheduler events

Prompt and response capture should be configurable because it may be verbose.

Suggested debug features:

* save raw LLM responses when validation fails
* save retry count
* save the patch merge report

---

## Milestone Plan

Codex should implement the project in small, testable milestones.

# Milestone 1: Project Skeleton

## Goal

Create a clean runnable scaffold with schemas, config, CLI shell, FastAPI shell, and storage directories.

## Build

* pyproject and package layout
* config loading
* logging setup
* base Pydantic schemas
* FastAPI app with `/health`
* CLI entrypoint
* local data directory bootstrap

## Acceptance Criteria

* app starts with `newsroom serve`
* `/health` returns OK JSON
* CLI help works
* tests run successfully

# Milestone 2: Initial World Creation

## Goal

Generate the initial world bible from a user seed prompt.

## Build

* world architect prompt
* LLM provider interface
* world generation service
* save `world_bible.json`
* optional `world_bible.md`

## Acceptance Criteria

* `newsroom init-world` accepts a prompt or prompt file
* valid world bible is created
* output includes at least a baseline set of people, organizations, locations, and timeline facts
* tests mock the LLM and validate output persistence

# Milestone 3: Daily Story Generation

## Goal

Generate a daily edition from the world bible.

## Build

* reporter prompt
* story generation service
* story batch persistence by date
* story validation

## Acceptance Criteria

* `newsroom generate-news --date YYYY-MM-DD` produces a valid story batch file
* each story includes headline, summary, body, category, and metadata
* story batch can be loaded by the API

# Milestone 4: Feed Publishing

## Goal

Expose generated stories as RSS and Atom.

## Build

* feed rendering service
* RSS endpoint
* Atom endpoint
* latest stories endpoint

## Acceptance Criteria

* generated story batch appears at `/feed/rss.xml`
* generated story batch appears at `/feed/atom.xml`
* feed XML is well-formed
* feed tests pass

# Milestone 5: Canon Update Patch

## Goal

Create structured world updates from the day’s stories.

## Build

* patch prompt for the World Architect
* patch schema
* patch persistence
* patch validation

## Acceptance Criteria

* `newsroom update-world --date YYYY-MM-DD` creates a patch file
* patch includes timeline events and entity updates where applicable
* invalid patch output is rejected or retried

# Milestone 6: Merge Engine

## Goal

Apply a patch to the world bible safely.

## Build

* merge service
* entity matching logic
* append/update rules
* snapshot archiving

## Acceptance Criteria

* patch can be merged into canon
* updated world bible is saved
* unchanged sections are preserved
* snapshot folder contains before/after state and patch

# Milestone 7: Continuity Validator

## Goal

Detect simple canon contradictions and duplicate entities.

## Build

* continuity service
* warning report generation
* duplicate name heuristics
* contradiction checks for basic states

## Acceptance Criteria

* contradictions generate warnings
* duplicate entities are detected in simple cases
* merge pipeline logs issues clearly

# Milestone 8: Daily Run Pipeline

## Goal

Create a one-command end-to-end daily loop.

## Build

* orchestration command
* daily run report
* idempotency safeguards
* failure handling

## Acceptance Criteria

* `newsroom run-daily --date YYYY-MM-DD` performs generation, feed publishing, patch generation, validation, and merge
* output is archived and logged
* rerun behavior is defined and tested

# Milestone 9: Scheduler

## Goal

Allow automated daily runs.

## Build

* scheduler service
* enable/disable config
* scheduled publication time

## Acceptance Criteria

* app can run scheduled jobs when enabled
* scheduled run triggers the daily pipeline
* scheduler logs are visible

# Milestone 10: Editorial Controls

## Goal

Allow tuning of tone, categories, and output shape.

## Build

* config for editorial tone
* category weights
* story count
* optional world-specific settings

## Acceptance Criteria

* changing config measurably changes the generated edition style
* defaults remain stable

# Milestone 11: Admin Inspection Endpoints

## Goal

Provide simple inspection and debugging endpoints.

## Build

* endpoint for current world summary
* endpoint for current stories
* endpoint for recent snapshots
* endpoint for validation reports

## Acceptance Criteria

* operator can inspect generated state without reading raw files manually

# Milestone 12: Multi-World Readiness

## Goal

Prepare the architecture to support multiple worlds later.

## Build

* world ID abstractions
* namespaced storage paths
* world-aware services

## Acceptance Criteria

* code no longer assumes exactly one world even if only one is used by default

---

## MVP Definition

A valid MVP includes only:

* initial world generation
* daily story generation
* RSS and Atom publishing
* patch generation
* patch merge into canon
* snapshot storage

No admin UI is required for MVP.

---

## Stretch Goals

Do not implement these until the core loop is stable.

* web admin UI
* manual story approval workflow
* multiple editions per day
* character relationship graph
* rich entity pages
* image generation for stories
* audio newscast output
* multiple newspapers with different editorial biases in the same world

---

## Prompting Expectations

Prompts should be written so that the model:

* returns JSON only
* is reminded of schema constraints
* avoids extra commentary
* distinguishes canon facts from rumors
* uses existing entities when possible
* introduces new entities carefully

Prompt files should be easy to tweak without rewriting application code.

---

## Implementation Notes for Codex

* Prefer explicit code over meta-framework complexity.
* Keep service boundaries clean.
* Keep tests close to each milestone.
* Avoid premature optimization.
* Build the merge engine conservatively.
* Use sample fixtures for world, stories, and patches.
* Make it easy for a human to inspect raw outputs.
* Treat malformed LLM output as normal and design retry/validation flows accordingly.

---

## Definition of Done

The project is considered complete for the first major version when:

* a user can seed a fictional world
* the application can generate daily news stories for that world
* the stories appear in a standard feed reader through RSS or Atom
* the world bible updates over time from those stories
* the system archives and validates each generation cycle
* the codebase is modular enough for future UI and provider expansion

---

## First Recommended Build Order

If Codex needs the simplest execution order, follow this exact sequence:

1. scaffold repo and schemas
2. add config, logging, CLI, FastAPI shell
3. implement initial world generation
4. implement daily story generation
5. implement RSS/Atom feed publishing
6. implement canon patch generation
7. implement patch merge
8. implement continuity checks
9. implement end-to-end daily runner
10. add scheduler and inspection endpoints

This order is preferred because it proves the full creative loop early while keeping the system debuggable.


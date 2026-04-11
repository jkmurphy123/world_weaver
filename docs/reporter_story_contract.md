# Reporter Story Output Contract (Milestone 3)

This document defines the concrete contract for News Reporter outputs so engineering can use deterministic fixtures and strict schema validation.

## Schema Contract

Top-level object: `StoryBatch`

- `date` (ISO date): publication date for this edition.
- `stories` (array, min 1): ordered set of story items.

Each story object:

- `headline` (non-empty string): specific event framing.
- `summary` (non-empty string): concise standalone synopsis.
- `body` (non-empty string): full report with consequences.
- `category` (non-empty string): newsroom section label.
- `metadata`:
  - `story_id` (string): stable ID in `story-YYYY-MM-DD-XXX` form.
  - `published_at` (ISO datetime with timezone): generation/publication timestamp.
  - `target_date` (ISO date): must match batch date.
  - `world_id` (string): canonical world identifier.

## Entity Reference Guidance

Current schema does not include a dedicated `referenced_entities` field. Until Milestone 5 patch extraction introduces richer structure, reporter prose should:

- Reuse canonical names from world bible entities when possible.
- Include canonical IDs inline in body text when available and useful, e.g. `Council Hall (loc-chronicle-sphere-42-central)`.
- Avoid introducing near-duplicate names for existing entities.

## Default Editorial Mix

For a standard 4-story daily batch:

- 1 major story (institutional, policy, or geopolitical impact).
- 2 medium stories (business/science/culture developments).
- 1 color or human-interest story with lower systemic stakes.

Category variety target: at least 3 distinct categories in a 4-story batch.

## Continuity Guardrails

- Preserve existing canon facts; reporter does not edit canon.
- Contradictions should be written as disputed claims, not silent retcons.
- Major status changes (leadership shift, organizational collapse, war escalation) must include an observable trigger in the body.
- Unverified claims should be framed as rumor/allegation language to support downstream confidence-tier handling.

## Deterministic Test Fixture

Engineering fixture for mocks and parser tests:

- `tests/fixtures/story_batch_example.json`

This fixture is expected to parse as `StoryBatch` without additional transformations.

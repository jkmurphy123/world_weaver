# WorldCodex Integration Plan

Date: 2026-04-30

## Goal

Adapt WorldWeaver into a focused fictional newsroom application that depends on WorldCodex for all canonical world-building work.

WorldWeaver should:

- Generate fictional news stories from a WorldCodex-provided world context.
- Preserve story batches, feeds, and newsroom API behavior.
- Propose canonical updates from published stories as `worldcodex.patch.v1` payloads.
- Send validated patches back to WorldCodex for preview and application.

WorldWeaver should no longer:

- Generate or own initial worlds.
- Store `world_bible.json` as the runtime source of truth.
- Merge canon updates locally.
- Maintain its own SQLite world entity projection unless it is explicitly a read-only cache of WorldCodex data.
- Expose editable world-building APIs that bypass WorldCodex.

## Current Ownership Problems

WorldWeaver currently mixes two responsibilities:

1. Newsroom behavior: story generation, story archives, RSS/Atom feeds, and a simple API.
2. World-building behavior: initial world generation, world bible schemas, local canon patch generation, local patch merging, SQLite world entity storage, and editable world entity APIs.

That second responsibility now belongs in WorldCodex. Keeping it in WorldWeaver would create two competing canon models and make later story, news, and image tools harder to coordinate.

## Target Architecture

WorldCodex is the canonical world service and file format owner.

WorldWeaver is a client application:

```text
WorldCodex world
  -> world export <world> news-context
  -> WorldWeaver generates daily stories
  -> WorldWeaver proposes worldcodex.patch.v1 changes from stories
  -> world patch validate/preview/apply
  -> WorldCodex updates atoms, relationships, timeline, and canon state
```

Recommended initial integration style: a small `WorldCodexClient` wrapper that shells out to the WorldCodex CLI. This keeps the integration explicit and avoids packaging coupling while both projects are still evolving. A direct Python package integration can come later behind the same client interface.

Useful WorldCodex commands from the current milestone work:

```bash
world export <world> news-context
world export <world> story-context
world export <world> world-bible
world patch validate <world> <patch.json>
world patch preview <world> <patch.json>
world patch apply <world> <patch.json>
```

Expected patch format: `worldcodex.patch.v1`.

Patch operations WorldWeaver should generate include:

- `add_atom`
- `update_atom`
- `deprecate_atom`
- `add_relationship`
- `update_relationship`
- `add_timeline_event`
- `resolve_conflict`

## Code Change Inventory

### Keep and Adapt

- `src/world_weaver/services/story_service.py`
  - Keep story persistence and `StoryBatch` validation.
  - Change generation input from `WorldBible` to a WorldCodex `news-context` export.
  - Remove `load_world_bible`.

- `src/world_weaver/prompts/reporter_daily.md`
  - Change prompt contract from `world_bible` to `news_context`.
  - Tell the reporter to preserve WorldCodex atom IDs in `referenced_entities` where possible.
  - Tell the reporter to surface meaningful continuity effects for later patch proposal.

- `src/world_weaver/services/patch_service.py`
  - Refactor into a patch proposal service.
  - Replace `CanonUpdatePatch` output with `worldcodex.patch.v1`.
  - Use a renamed prompt such as `worldcodex_patch_proposal.md`.

- `src/world_weaver/cli.py`
  - `generate-news` should call WorldCodex for `news-context`, then generate and save stories.
  - `update-world` should generate a WorldCodex patch, validate/preview/apply it through WorldCodex, and archive the run artifacts.
  - `serve`, `set-llm-provider`, `test-llm-connection`, story retrieval, and feed behavior should remain.

- `src/world_weaver/llm/mock_provider.py`
  - Keep deterministic story output for tests.
  - Remove mock world generation behavior.
  - Add deterministic `worldcodex.patch.v1` output for patch proposal tests.

- `src/world_weaver/app.py`
  - Keep health, stories, and feed routes.
  - Remove automatic SQLite world store initialization unless a read-only cache remains.
  - Optionally add a read-only `/world/context` proxy later.

- `README.md` and `AGENTS.md`
  - Reframe WorldWeaver as a newsroom client of WorldCodex.
  - Remove the local “World Architect” ownership model.

### Replace or Remove

- `src/world_weaver/schemas.py`
  - Keep `HealthResponse`, `StoryMetadata`, `Story`, and `StoryBatch`.
  - Remove or isolate local world bible schemas:
    - `WorldBible`
    - `WorldInfo`
    - `StyleGuide`
    - `Continuity`
    - `CanonLocation`
    - `CanonOrganization`
    - `CanonPerson`
    - `TimelineEvent`
    - `OpenThread`
    - `CanonUpdatePatch`
  - Add minimal DTOs for WorldCodex context and patch validation only if useful. Prefer accepting dict payloads at the adapter boundary until the WorldCodex schema stabilizes.

- `src/world_weaver/services/merge_service.py`
  - Remove from the active update path.
  - WorldCodex owns merge, conflict handling, snapshots, and canon mutation.

- `src/world_weaver/services/init_world_service.py`
  - Remove or deprecate.
  - WorldWeaver should not create initial worlds.

- `src/world_weaver/services/world_generation.py`
  - Remove or deprecate.
  - Deterministic world creation belongs in WorldCodex if still needed.

- `src/world_weaver/services/world_bible_ingest_service.py`
  - Remove or replace with documentation that migration happens through WorldCodex.

- `src/world_weaver/services/world_db_sync_service.py`
  - Remove unless retained as an explicitly read-only cache sourced from WorldCodex exports.

- `src/world_weaver/storage/sqlite_world_store.py`
  - Remove if no read-only cache remains.

- `src/world_weaver/api/routes_world_entities.py`
  - Remove editable world entity APIs.
  - If a world API remains, make it a read-only WorldCodex proxy.

- `src/world_weaver/world_entities.py`
  - Remove unless the API keeps a read-only proxy or cache.

- `src/world_weaver/prompts/world_architect_initial.md`
  - Remove or archive.

- `src/world_weaver/prompts/world_architect_patch.md`
  - Replace with a WorldCodex patch proposal prompt.

- `src/world_weaver/prompts/world_architect_manual_update.md`
  - Remove or move to WorldCodex.

### Commands to Deprecate or Redefine

- `newsroom init-world`
  - Deprecate in WorldWeaver.
  - Possible replacement: print WorldCodex bootstrap instructions or call WorldCodex if explicitly requested.

- `newsroom ingest-world-bible`
  - Deprecate in WorldWeaver.
  - Migration should happen through WorldCodex tooling.

- `newsroom add-canon`
  - Redefine as a WorldCodex patch proposal/apply workflow, or remove to avoid making WorldWeaver a manual canon editor.

- `newsroom world-summary`
  - Redefine as a read-only WorldCodex export summary, or remove in favor of `world export`.

## Milestone 1: Add the WorldCodex Boundary

Create the integration boundary without changing user-facing behavior yet.

Code changes:

- Add WorldCodex settings in `src/world_weaver/config.py`:
  - `NEWSROOM_WORLDCODEX_WORLD`
  - `NEWSROOM_WORLDCODEX_CLI`
  - Optional `NEWSROOM_WORLDCODEX_TIMEOUT_SECONDS`
- Add `src/world_weaver/worldcodex_client.py`.
- Implement client methods:
  - `export_context(context_type: str) -> dict`
  - `validate_patch(patch_path: Path) -> CommandResult`
  - `preview_patch(patch_path: Path) -> CommandResult`
  - `apply_patch(patch_path: Path) -> CommandResult`
- Add tests with a fake command runner so no real WorldCodex process is required.

Acceptance tests:

- Client builds the expected CLI commands.
- Client parses JSON exports.
- Client surfaces non-zero command failures with useful error messages.
- Existing tests still pass.

## Milestone 2: Generate News from WorldCodex Context

Move story generation off `data/worlds/world_bible.json`.

Code changes:

- Update `StoryService.generate_reported_batch` to accept `news_context: dict`.
- Remove runtime use of `StoryService.load_world_bible`.
- Update `newsroom generate-news`:
  - Fetch `world export <world> news-context`.
  - Pass that context to the reporter.
  - Save `StoryBatch` as before.
- Update `reporter_daily.md` to use `news_context`.
- Update `mock_provider.py` to produce stories from the new context shape.

Acceptance tests:

- `generate-news` calls the WorldCodex client.
- The saved story batch still validates against `StoryBatch`.
- Reporter output includes referenced WorldCodex atom IDs when present.
- No `world_bible.json` read is required for story generation.

## Milestone 3: Propose WorldCodex Patches

Replace local canon patch generation with WorldCodex patch proposal generation.

Code changes:

- Rename or refactor `PatchService` into `WorldCodexPatchProposalService`.
- Add a new prompt, `worldcodex_patch_proposal.md`.
- Generate `worldcodex.patch.v1` payloads from:
  - WorldCodex `news-context` or `world-bible` export.
  - The saved `StoryBatch`.
  - Target date and run metadata.
- Save proposed patches under `data/patches/`.
- Validate patch structure before sending to WorldCodex.

Acceptance tests:

- Patch proposal output has `schema_version: worldcodex.patch.v1`.
- Story-driven changes become WorldCodex operations, especially `add_timeline_event`, `add_atom`, and `add_relationship`.
- Invalid patch output fails before apply.
- The old `CanonUpdatePatch` model is no longer used in the active path.

## Milestone 4: Hand Canon Application to WorldCodex

Remove local merge behavior from `update-world`.

Code changes:

- Update `newsroom update-world`:
  - Load the story batch for the target date.
  - Fetch the relevant WorldCodex context.
  - Generate a `worldcodex.patch.v1` proposal.
  - Save the proposal.
  - Run `world patch validate`.
  - Run `world patch preview`.
  - Apply only when requested or when the command default is confirmed.
- Add a `--dry-run` option if not already present.
- Archive run artifacts:
  - Story batch.
  - Proposed patch.
  - Validate output.
  - Preview output.
  - Apply output when applied.
- Remove `MergeService` and `WorldDbSyncService` from the active command path.

Acceptance tests:

- `update-world --dry-run` never mutates WorldCodex.
- `update-world --apply` calls validate, preview, then apply.
- A missing story batch produces a clear CLI error.
- No local `world_bible.json` is written by `update-world`.

## Milestone 5: Remove Local World-Building Surface Area

Clean up commands, services, API routes, tests, and documentation so the ownership split is clear.

Code changes:

- Deprecate or remove:
  - `init-world`
  - `ingest-world-bible`
  - local `add-canon`
  - local `world-summary`
- Remove local world-building services once callers are gone.
- Remove editable world entity API routes.
- Stop initializing SQLite world storage in `create_app`.
- Update `README.md`, `AGENTS.md`, and docs under `docs/`.
- Mark `data/worlds/world_bible.json` as legacy sample data or remove it from runtime docs.

Acceptance tests:

- API still serves:
  - `/health`
  - `/stories/today`
  - `/stories/latest`
  - `/stories/{YYYY-MM-DD}`
  - `/feed/rss.xml`
  - `/feed/atom.xml`
- Editable local world entity routes are removed or explicitly read-only proxies.
- Removed commands have either disappeared from `newsroom --help` or print clear deprecation guidance.
- Full test suite passes.

## Test Plan by Area

CLI tests:

- Mock WorldCodex client calls.
- Confirm no local world bible file is read or written in `generate-news` and `update-world`.
- Confirm patch validation and apply order.

Service tests:

- Story generation accepts WorldCodex context.
- Patch proposal emits `worldcodex.patch.v1`.
- Mock LLM outputs remain deterministic.

API tests:

- Existing story and feed endpoints continue to pass.
- World entity endpoints are removed or rewritten as read-only WorldCodex proxies.

Integration smoke test:

```bash
export NEWSROOM_WORLDCODEX_WORLD=titan-osa
newsroom generate-news --date 2026-04-30
newsroom update-world --date 2026-04-30 --dry-run
newsroom update-world --date 2026-04-30 --apply
```

Expected result:

- Stories are saved in `data/stories/`.
- A proposed `worldcodex.patch.v1` is saved in `data/patches/`.
- Dry run shows WorldCodex validate and preview output.
- Apply updates WorldCodex, not a local WorldWeaver world bible.

## Migration Notes

Existing `data/worlds/world_bible.json` should not remain the runtime canon source.

Migration options:

1. Convert the existing world bible into WorldCodex atoms, relationships, timeline events, and canon state.
2. Keep it as fixture/sample data for tests only.
3. Remove it after test coverage no longer depends on it.

The cleanest long-term direction is option 1 if the world content is valuable, followed by option 2 only for legacy compatibility tests.

## Recommended Order

Do the milestones in order. Each one gives a testable checkpoint and avoids a large rewrite:

1. Create the WorldCodex client boundary.
2. Move news generation to WorldCodex context.
3. Produce WorldCodex patch proposals.
4. Apply canon through WorldCodex.
5. Remove local world-building commands, storage, and APIs.


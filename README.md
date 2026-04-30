# world_weaver

Local-first fictional newsroom simulator with a CLI and FastAPI API.

WorldWeaver is a WorldCodex client. WorldCodex owns world creation, canon storage, world summaries,
atoms, relationships, timeline, and patch application. WorldWeaver owns story generation, story
archives, RSS/Atom feeds, and patch proposals derived from published stories.

## Setup

```bash
cd /home/ubuntu/ai_projects/world_weaver
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

newsroom set-llm-provider --provider openai --model gpt-4.1
newsroom test-llm-connection
```

## Current CLI Commands

Use `newsroom --help` for full option details.

```bash
# Run API server (default 127.0.0.1:8000)
newsroom serve
newsroom serve --host 0.0.0.0 --port 8010

# Generate one daily story batch from a WorldCodex news-context export
newsroom generate-news --date 2026-04-13

# Propose WorldCodex canon updates from a saved story batch
newsroom propose-world-patch --date 2026-04-13

# Validate and preview a WorldCodex patch from a saved story batch
newsroom update-world --date 2026-04-13

# Apply the validated patch to WorldCodex
newsroom update-world --date 2026-04-13 --apply

# Persist the selected LLM provider/model for this repo
newsroom set-llm-provider --provider mock
newsroom set-llm-provider --provider openai --model gpt-4.1

# Verify the selected provider/model before generation
newsroom test-llm-connection

# Deprecated local world-building commands now print WorldCodex migration guidance
newsroom init-world
newsroom ingest-world-bible
newsroom add-canon
newsroom world-summary
```

## Environment Variables

All settings use the `NEWSROOM_` prefix.

```bash
NEWSROOM_HOST=127.0.0.1
NEWSROOM_PORT=8000
NEWSROOM_DATA_DIR=data
NEWSROOM_API_TOKEN=newsroom-dev-token
NEWSROOM_DEFAULT_STORY_COUNT=4
NEWSROOM_DEFAULT_STORY_BODY_WORDS=500
NEWSROOM_WORLDCODEX_WORLD=world-main
NEWSROOM_WORLDCODEX_CLI=world
NEWSROOM_WORLDCODEX_TIMEOUT_SECONDS=60
NEWSROOM_LLM_PROVIDER=mock
NEWSROOM_LLM_MODEL=mock-world-architect-v1
NEWSROOM_OPENAI_TIMEOUT_SECONDS=120
NEWSROOM_OPENAI_API_KEY=
OPENAI_API_KEY=
```

`set-llm-provider` writes `NEWSROOM_LLM_PROVIDER` and `NEWSROOM_LLM_MODEL` into a local `.env` file. Process environment variables still override `.env` values when present.

If OpenAI story generation times out on longer prompts or longer article bodies, raise `NEWSROOM_OPENAI_TIMEOUT_SECONDS`, for example `NEWSROOM_OPENAI_TIMEOUT_SECONDS=300`.
## API Endpoints (Current)

No auth required:

- `GET /health`
- `GET /stories/today`
- `GET /stories/latest`
- `GET /stories/{YYYY-MM-DD}`
- `GET /feed/rss.xml` (alias: `GET /feeds/rss.xml`)
- `GET /feed/atom.xml` (alias: `GET /feeds/atom.xml`)

World-building APIs are not mounted in WorldWeaver. Use WorldCodex for editable world and canon
operations.

## Manual Smoke Test

```bash
source .venv/bin/activate
newsroom generate-news --date 2026-04-11
newsroom update-world --date 2026-04-11
newsroom update-world --date 2026-04-11 --apply
newsroom serve
```

Then verify:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/stories/latest`
- `http://127.0.0.1:8000/feed/rss.xml`
- `http://127.0.0.1:8000/feed/atom.xml`

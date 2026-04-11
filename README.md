# world_weaver

Local-first fictional newsroom simulator with a CLI and FastAPI API.

## Setup

```bash
cd /home/ubuntu/ai_projects/world_weaver
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Current CLI Commands

Use `newsroom --help` for full option details.

```bash
# Run API server (default 127.0.0.1:8000)
newsroom serve
newsroom serve --host 0.0.0.0 --port 8010

# Create initial world bible
newsroom init-world --prompt "A synthetic island city ruled by corporate blocs."
newsroom init-world --prompt-file ./seed_prompt.txt

# Generate one daily story batch
newsroom generate-news --date 2026-04-11

# Persist the selected LLM provider/model for this repo
newsroom set-llm-provider --provider mock
newsroom set-llm-provider --provider openai --model gpt-4.1

# Verify the selected provider/model before generation
newsroom test-llm-connection

# Ingest markdown + seed json into canonical files and SQLite entities
newsroom ingest-world-bible
newsroom ingest-world-bible \
  --source-markdown data/world-bible.md \
  --seed-json data/worlds/world_bible.seed.v1.json \
  --world-id world-main

# Summarize world state for debugging
newsroom world-summary
newsroom world-summary --output json
newsroom world-summary --world-id world-new-meridian
```

## Environment Variables

All settings use the `NEWSROOM_` prefix.

```bash
NEWSROOM_HOST=127.0.0.1
NEWSROOM_PORT=8000
NEWSROOM_DATA_DIR=data
NEWSROOM_API_TOKEN=newsroom-dev-token
NEWSROOM_DEFAULT_STORY_COUNT=4
NEWSROOM_LLM_PROVIDER=mock
NEWSROOM_LLM_MODEL=mock-world-architect-v1
NEWSROOM_OPENAI_API_KEY=
OPENAI_API_KEY=
```

`set-llm-provider` writes `NEWSROOM_LLM_PROVIDER` and `NEWSROOM_LLM_MODEL` into a local `.env` file. Process environment variables still override `.env` values when present.

## API Endpoints (Current)

No auth required:

- `GET /health`
- `GET /stories/today`
- `GET /stories/latest`
- `GET /stories/{YYYY-MM-DD}`
- `GET /feed/rss.xml` (alias: `GET /feeds/rss.xml`)
- `GET /feed/atom.xml` (alias: `GET /feeds/atom.xml`)

Requires bearer token (`Authorization: Bearer $NEWSROOM_API_TOKEN`):

- `GET|POST /api/world/{world_id}/factions`
- `GET|PATCH|DELETE /api/world/{world_id}/factions/{entity_id}`
- `GET|POST /api/world/{world_id}/locations`
- `GET|PATCH|DELETE /api/world/{world_id}/locations/{entity_id}`
- `GET|POST /api/world/{world_id}/characters`
- `GET|PATCH|DELETE /api/world/{world_id}/characters/{entity_id}`
- `GET|POST /api/world/{world_id}/lore`
- `GET|PATCH|DELETE /api/world/{world_id}/lore/{entity_id}`

## Manual Smoke Test

```bash
source .venv/bin/activate
newsroom init-world --prompt "A dense floating city ruled by data cartels."
newsroom generate-news --date 2026-04-11
newsroom serve
```

Then verify:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/stories/latest`
- `http://127.0.0.1:8000/feed/rss.xml`
- `http://127.0.0.1:8000/feed/atom.xml`

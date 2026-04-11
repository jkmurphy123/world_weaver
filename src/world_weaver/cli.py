from datetime import date
import json
from pathlib import Path
from typing import Any, Literal

import typer
import uvicorn

from world_weaver.app import create_app
from world_weaver.config import get_settings
from world_weaver.llm.factory import build_provider
from world_weaver.services.init_world_service import InitWorldService
from world_weaver.services.story_service import StoryService
from world_weaver.services.world_bible_ingest_service import WorldBibleIngestService
from world_weaver.storage.sqlite_world_store import SqliteWorldStore, WorldEntityRepository

app = typer.Typer(help="World Weaver newsroom CLI")


@app.command()
def serve(host: str | None = None, port: int | None = None) -> None:
    """Run the newsroom API server."""
    settings = get_settings()
    uvicorn.run(
        create_app(),
        host=host or settings.host,
        port=port or settings.port,
    )


@app.command("generate-news")
def generate_news(target_date: str = typer.Option(..., "--date", help="Date in YYYY-MM-DD format")) -> None:
    """Generate and persist a daily story batch."""
    settings = get_settings()
    parsed_date = date.fromisoformat(target_date)

    world_path = settings.data_dir / "worlds" / "world_bible.json"
    provider = build_provider(settings)
    story_service = StoryService(
        settings.data_dir / "stories",
        provider=provider,
        prompts_dir=Path(__file__).resolve().parent / "prompts",
    )
    world = story_service.load_world_bible(world_path)
    batch = story_service.generate_reported_batch(
        target_date=parsed_date,
        world_bible=world,
        model=settings.llm_model,
        count=settings.default_story_count,
    )
    output_path = story_service.save_batch(batch)
    typer.echo(f"Generated {len(batch.stories)} stories for {parsed_date.isoformat()} at {output_path}")


@app.command("init-world")
def init_world(
    prompt: str | None = typer.Option(None, "--prompt", help="Seed prompt text"),
    prompt_file: Path | None = typer.Option(None, "--prompt-file", help="Path to file with seed prompt"),
) -> None:
    """Generate and persist the initial world bible from a seed prompt."""
    if bool(prompt) == bool(prompt_file):
        raise typer.BadParameter("Provide exactly one of --prompt or --prompt-file")

    settings = get_settings()
    provider = build_provider(settings)
    seed_prompt = prompt if prompt is not None else prompt_file.read_text(encoding="utf-8")

    service = InitWorldService(
        provider=provider,
        prompts_dir=Path(__file__).resolve().parent / "prompts",
        worlds_dir=settings.data_dir / "worlds",
    )
    world, json_path, markdown_path = service.generate_and_save(seed_prompt=seed_prompt, model=settings.llm_model)
    typer.echo(
        "Initialized world "
        f"'{world.metadata.name}' with {len(world.people)} people, "
        f"{len(world.organizations)} organizations, and {len(world.locations)} locations."
    )
    typer.echo(f"Saved JSON: {json_path}")
    typer.echo(f"Saved markdown: {markdown_path}")


@app.command("ingest-world-bible")
def ingest_world_bible(
    source_markdown: Path = typer.Option(
        Path("data/world-bible.md"),
        "--source-markdown",
        help="Path to source world bible markdown",
    ),
    seed_json: Path = typer.Option(
        Path("data/worlds/world_bible.seed.v1.json"),
        "--seed-json",
        help="Path to mapped world bible seed JSON",
    ),
    world_id: str | None = typer.Option(
        None,
        "--world-id",
        help="Optional world ID override for database ingestion",
    ),
) -> None:
    """Ingest an existing world bible markdown into canonical files and SQLite entities."""
    settings = get_settings()
    store = SqliteWorldStore(
        db_path=settings.data_dir / settings.world_db_filename,
        migrations_dir=Path(__file__).resolve().parent / "storage" / "migrations",
    )
    service = WorldBibleIngestService(
        markdown_path=source_markdown,
        seed_json_path=seed_json,
        worlds_dir=settings.data_dir / "worlds",
        world_store=store,
    )
    report = service.ingest(world_id_override=world_id)
    typer.echo(f"Ingested world bible for world_id={report.world_id}")
    typer.echo(f"Saved JSON: {report.world_bible_path}")
    typer.echo(f"Saved markdown: {report.world_markdown_path}")
    typer.echo(
        "Upserted "
        f"{report.factions_upserted} factions, "
        f"{report.locations_upserted} locations, "
        f"{report.characters_upserted} characters, "
        f"{report.lore_upserted} lore entries."
    )


@app.command("world-summary")
def world_summary(
    world_path: Path | None = typer.Option(
        None,
        "--world-path",
        help="Path to canonical world JSON. Defaults to data/worlds/world_bible.json",
    ),
    world_id: str | None = typer.Option(
        None,
        "--world-id",
        help="Optional world ID override for SQLite entity counts",
    ),
    output: Literal["text", "json"] = typer.Option(
        "text",
        "--output",
        help="Output format",
    ),
) -> None:
    """Summarize current world state for debugging."""
    settings = get_settings()
    resolved_world_path = world_path or (settings.data_dir / "worlds" / "world_bible.json")
    if not resolved_world_path.exists():
        raise typer.BadParameter(f"World bible not found at {resolved_world_path}")

    payload = json.loads(resolved_world_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise typer.BadParameter(f"World bible payload must be an object at {resolved_world_path}")

    world_info = payload.get("world", {}) if isinstance(payload.get("world"), dict) else {}
    continuity = payload.get("continuity", {}) if isinstance(payload.get("continuity"), dict) else {}
    style_guide = payload.get("style_guide", {}) if isinstance(payload.get("style_guide"), dict) else {}

    resolved_world_id = world_id or str(world_info.get("id") or settings.default_world_id)
    canon_sections = [
        "locations",
        "organizations",
        "governments",
        "corporations",
        "people",
        "technologies",
        "conflicts",
        "open_threads",
        "timeline",
    ]
    canon_counts = {
        section: len(payload.get(section, [])) if isinstance(payload.get(section), list) else 0
        for section in canon_sections
    }

    story_service = StoryService(settings.data_dir / "stories")
    latest_stories: dict[str, Any] | None = None
    try:
        latest_batch = story_service.load_latest_batch()
        if latest_batch is not None:
            category_counts: dict[str, int] = {}
            for story in latest_batch.stories:
                category_counts[story.category] = category_counts.get(story.category, 0) + 1
            latest_stories = {
                "date": latest_batch.date.isoformat(),
                "count": len(latest_batch.stories),
                "categories": dict(sorted(category_counts.items())),
            }
    except Exception as exc:
        latest_stories = {"error": str(exc)}

    store = SqliteWorldStore(
        db_path=settings.data_dir / settings.world_db_filename,
        migrations_dir=Path(__file__).resolve().parent / "storage" / "migrations",
    )
    store.run_migrations()
    repo = WorldEntityRepository(store)
    sqlite_counts = {
        "factions": len(repo.list("factions", resolved_world_id)),
        "locations": len(repo.list("locations", resolved_world_id)),
        "characters": len(repo.list("characters", resolved_world_id)),
        "lore_entries": len(repo.list("lore_entries", resolved_world_id)),
    }

    allowed_story_types = style_guide.get("allowed_story_types", [])
    taboos = style_guide.get("taboos", [])
    summary = {
        "world_file": str(resolved_world_path),
        "world": {
            "id": resolved_world_id,
            "name": world_info.get("name"),
            "genre": world_info.get("genre"),
            "tone": world_info.get("tone"),
            "calendar_mode": world_info.get("calendar_mode"),
            "current_date": continuity.get("current_date"),
        },
        "canon_counts": canon_counts,
        "style_guide": {
            "story_type_count": len(allowed_story_types) if isinstance(allowed_story_types, list) else 0,
            "taboo_count": len(taboos) if isinstance(taboos, list) else 0,
        },
        "latest_stories": latest_stories,
        "sqlite_entity_counts": sqlite_counts,
    }

    if output == "json":
        typer.echo(json.dumps(summary, indent=2, sort_keys=True))
        return

    typer.echo(f"World summary for {resolved_world_id}")
    typer.echo(f"World file: {resolved_world_path}")
    typer.echo(
        "Core: "
        f"name={summary['world']['name'] or '-'} "
        f"genre={summary['world']['genre'] or '-'} "
        f"tone={summary['world']['tone'] or '-'} "
        f"calendar_mode={summary['world']['calendar_mode'] or '-'} "
        f"current_date={summary['world']['current_date'] or '-'}"
    )
    typer.echo("Canon counts: " + ", ".join(f"{key}={value}" for key, value in canon_counts.items()))
    typer.echo(
        "Style guide: "
        f"story_types={summary['style_guide']['story_type_count']}, "
        f"taboos={summary['style_guide']['taboo_count']}"
    )
    if latest_stories is None:
        typer.echo("Stories: none published yet")
    elif "error" in latest_stories:
        typer.echo(f"Stories: unable to load latest batch ({latest_stories['error']})")
    else:
        categories = ", ".join(
            f"{category}:{count}" for category, count in latest_stories["categories"].items()
        )
        typer.echo(
            f"Stories: latest_date={latest_stories['date']} "
            f"count={latest_stories['count']} categories={categories or '-'}"
        )
    typer.echo(
        "SQLite entities: "
        + ", ".join(f"{key}={value}" for key, value in sqlite_counts.items())
    )


if __name__ == "__main__":
    app()

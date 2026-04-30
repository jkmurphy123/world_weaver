from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Literal

import typer
import uvicorn

from world_weaver.app import create_app
from world_weaver.config import get_settings, update_settings_file
from world_weaver.llm.factory import build_provider
from world_weaver.services.init_world_service import InitWorldService
from world_weaver.services.merge_service import MergeService
from world_weaver.services.patch_service import PatchService
from world_weaver.services.story_service import StoryService
from world_weaver.services.world_db_sync_service import WorldDbSyncService
from world_weaver.services.world_bible_ingest_service import WorldBibleIngestService
from world_weaver.storage.sqlite_world_store import SqliteWorldStore, WorldEntityRepository
from world_weaver.worldcodex_client import WorldCodexClientError, build_worldcodex_client

app = typer.Typer(help="World Weaver newsroom CLI")


def _default_model_for_provider(provider: str) -> str:
    if provider == "openai":
        return "gpt-4.1"
    return "mock-world-architect-v1"


def _build_world_store(*, data_dir: Path, world_db_filename: str) -> SqliteWorldStore:
    return SqliteWorldStore(
        db_path=data_dir / world_db_filename,
        migrations_dir=Path(__file__).resolve().parent / "storage" / "migrations",
    )


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "note"


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

    provider = build_provider(settings)
    story_service = StoryService(
        settings.data_dir / "stories",
        provider=provider,
        prompts_dir=Path(__file__).resolve().parent / "prompts",
    )
    worldcodex = build_worldcodex_client(
        world_id=settings.worldcodex_world,
        cli=settings.worldcodex_cli,
        timeout_seconds=settings.worldcodex_timeout_seconds,
    )
    try:
        news_context = worldcodex.export_context("news-context")
    except WorldCodexClientError as exc:
        typer.echo(f"Unable to load WorldCodex news context: {exc}")
        raise typer.Exit(code=1) from exc

    batch = story_service.generate_reported_batch(
        target_date=parsed_date,
        news_context=news_context,
        model=settings.llm_model,
        count=settings.default_story_count,
    )
    output_path = story_service.save_batch(batch)
    typer.echo(f"Generated {len(batch.stories)} stories for {parsed_date.isoformat()} at {output_path}")


@app.command("update-world")
def update_world(target_date: str = typer.Option(..., "--date", help="Date in YYYY-MM-DD format")) -> None:
    """Generate a world-canon patch from a story batch and merge it into the world bible."""
    settings = get_settings()
    parsed_date = date.fromisoformat(target_date)
    world_path = settings.data_dir / "worlds" / "world_bible.json"

    provider = build_provider(settings)
    story_service = StoryService(
        settings.data_dir / "stories",
        provider=provider,
        prompts_dir=Path(__file__).resolve().parent / "prompts",
    )
    world_before = story_service.load_world_bible(world_path)
    batch = story_service.load_batch(parsed_date)
    if batch is None:
        raise typer.BadParameter(f"Story batch not found for {parsed_date.isoformat()}")

    patch_service = PatchService(
        provider=provider,
        prompts_dir=Path(__file__).resolve().parent / "prompts",
        patches_dir=settings.data_dir / "patches",
    )
    patch = patch_service.generate_patch(
        target_date=parsed_date.isoformat(),
        world_bible=world_before,
        story_batch=batch,
        model=settings.llm_model,
    )
    patch_path = patch_service.save_patch(patch)

    merge_service = MergeService(
        worlds_dir=settings.data_dir / "worlds",
        snapshots_dir=settings.data_dir / "snapshots",
    )
    world_after, report = merge_service.apply_patch(world_bible=world_before, patch=patch)
    json_path, _ = merge_service.save_world(world_after)
    WorldDbSyncService(
        world_store=_build_world_store(data_dir=settings.data_dir, world_db_filename=settings.world_db_filename)
    ).refresh_from_world_bible(world_after)
    snapshot_path = merge_service.archive_run(
        target_date=parsed_date.isoformat(),
        world_before=world_before,
        story_batch_payload=batch.model_dump(mode="json"),
        patch=patch,
        world_after=world_after,
        merge_report=report,
    )

    typer.echo(
        "Updated world canon "
        f"for {parsed_date.isoformat()} at {json_path} "
        f"(patch: {patch_path}, snapshot: {snapshot_path})"
    )
    typer.echo(
        "Merge summary: "
        f"timeline+={report.timeline_events_added}, "
        f"threads+={report.open_threads_added}, "
        f"threads_resolved={report.open_threads_resolved}, "
        f"people+={report.people_added}/{report.people_updated} updated, "
        f"orgs+={report.organizations_added}/{report.organizations_updated} updated, "
        f"locations+={report.locations_added}/{report.locations_updated} updated."
    )
    if report.warnings:
        typer.echo(f"Continuity warnings: {len(report.warnings)}")


@app.command("add-canon")
def add_canon(
    text: str | None = typer.Option(None, "--text", help="Canon note text to merge into the world"),
    text_file: Path | None = typer.Option(None, "--file", help="Path to a text file containing a canon note"),
    target_date: str | None = typer.Option(None, "--date", help="Optional effective date in YYYY-MM-DD format"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Generate and show the patch without mutating canon or SQLite"),
) -> None:
    """Merge an operator-provided canon note into the world bible."""
    if bool(text) == bool(text_file):
        raise typer.BadParameter("Provide exactly one of --text or --file")

    settings = get_settings()
    provider = build_provider(settings)
    world_path = settings.data_dir / "worlds" / "world_bible.json"
    story_service = StoryService(
        settings.data_dir / "stories",
        provider=provider,
        prompts_dir=Path(__file__).resolve().parent / "prompts",
    )
    world_before = story_service.load_world_bible(world_path)
    resolved_text = text if text is not None else text_file.read_text(encoding="utf-8")
    if not resolved_text.strip():
        raise typer.BadParameter("Canon note must not be empty")

    effective_date = (
        date.fromisoformat(target_date)
        if target_date is not None
        else (world_before.continuity.current_date if world_before.continuity is not None else datetime.now(timezone.utc).date())
    )

    patch_service = PatchService(
        provider=provider,
        prompts_dir=Path(__file__).resolve().parent / "prompts",
        patches_dir=settings.data_dir / "patches",
    )
    patch = patch_service.generate_patch_from_note(
        target_date=effective_date.isoformat(),
        world_bible=world_before,
        source_text=resolved_text,
        model=settings.llm_model,
    )

    if dry_run:
        typer.echo(json.dumps(patch.model_dump(mode="json"), indent=2))
        return

    note_slug = _slugify(resolved_text[:60])
    patch_stem = f"manual-{effective_date.isoformat()}-{note_slug}"
    patch_path = patch_service.save_patch(patch, filename_stem=patch_stem)

    merge_service = MergeService(
        worlds_dir=settings.data_dir / "worlds",
        snapshots_dir=settings.data_dir / "snapshots",
    )
    world_after, report = merge_service.apply_patch(world_bible=world_before, patch=patch)
    json_path, _ = merge_service.save_world(world_after)
    WorldDbSyncService(
        world_store=_build_world_store(data_dir=settings.data_dir, world_db_filename=settings.world_db_filename)
    ).refresh_from_world_bible(world_after)
    snapshot_path = merge_service.archive_run(
        target_date=patch_stem,
        world_before=world_before,
        story_batch_payload={
            "source": "manual_canon_note",
            "date": effective_date.isoformat(),
            "text": resolved_text,
        },
        patch=patch,
        world_after=world_after,
        merge_report=report,
    )

    typer.echo(
        "Added canon note "
        f"for {effective_date.isoformat()} at {json_path} "
        f"(patch: {patch_path}, snapshot: {snapshot_path})"
    )
    typer.echo(
        "Merge summary: "
        f"timeline+={report.timeline_events_added}, "
        f"threads+={report.open_threads_added}, "
        f"people+={report.people_added}/{report.people_updated} updated, "
        f"orgs+={report.organizations_added}/{report.organizations_updated} updated, "
        f"locations+={report.locations_added}/{report.locations_updated} updated."
    )
    if report.warnings:
        typer.echo(f"Continuity warnings: {len(report.warnings)}")


@app.command("set-llm-provider")
def set_llm_provider(
    provider: str = typer.Option(..., "--provider", help="Provider to use: mock or openai"),
    model: str | None = typer.Option(None, "--model", help="Optional model override"),
) -> None:
    """Persist the selected LLM provider and model in the local .env file."""
    normalized = provider.strip().lower()
    if normalized not in {"mock", "openai"}:
        raise typer.BadParameter("Provider must be one of: mock, openai")

    settings = get_settings()
    selected_model = model or (
        settings.llm_model if settings.llm_provider == normalized and settings.llm_model else _default_model_for_provider(normalized)
    )
    settings_path = update_settings_file(
        {
            "NEWSROOM_LLM_PROVIDER": normalized,
            "NEWSROOM_LLM_MODEL": selected_model,
        }
    )

    typer.echo(f"Saved provider={normalized} model={selected_model} to {settings_path}")
    if normalized == "openai" and not settings.openai_api_key:
        typer.echo("OpenAI API key not found in NEWSROOM_OPENAI_API_KEY or OPENAI_API_KEY.")
    typer.echo("Run `newsroom test-llm-connection` before generating stories.")


@app.command("test-llm-connection")
def test_llm_connection(model: str | None = typer.Option(None, "--model", help="Optional model override")) -> None:
    """Test connectivity for the currently selected LLM provider."""
    settings = get_settings()
    selected_model = model or settings.llm_model

    try:
        provider = build_provider(settings)
        status = provider.check_connection(selected_model)
    except Exception as exc:
        typer.echo(f"LLM connection test failed: {exc}")
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"LLM connection OK: provider={status.provider} model={status.model} message={status.message}"
    )


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
    WorldDbSyncService(
        world_store=_build_world_store(data_dir=settings.data_dir, world_db_filename=settings.world_db_filename)
    ).refresh_from_world_bible(world)
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
    store = _build_world_store(
        data_dir=settings.data_dir,
        world_db_filename=settings.world_db_filename,
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

    store = _build_world_store(
        data_dir=settings.data_dir,
        world_db_filename=settings.world_db_filename,
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

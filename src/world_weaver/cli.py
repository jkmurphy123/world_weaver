from datetime import date
from pathlib import Path

import typer
import uvicorn

from world_weaver.app import create_app
from world_weaver.config import get_settings
from world_weaver.llm.factory import build_provider
from world_weaver.services.init_world_service import InitWorldService
from world_weaver.services.story_service import StoryService
from world_weaver.services.world_bible_ingest_service import WorldBibleIngestService
from world_weaver.services.world_generation import WorldGenerationService
from world_weaver.storage.sqlite_world_store import SqliteWorldStore

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

    world_service = WorldGenerationService()
    story_service = StoryService(settings.data_dir / "stories")

    world = world_service.generate_world_bible(
        name="Chronicle Sphere",
        genre="science fantasy",
        tone="investigative",
        premise="A hidden archive leaks state secrets to ordinary citizens.",
        seed=42,
    )
    batch = story_service.generate_daily_batch(target_date=parsed_date, world_bible=world)
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


if __name__ == "__main__":
    app()

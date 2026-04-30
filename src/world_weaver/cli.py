from datetime import date
import json
from pathlib import Path
from typing import Any

import typer
import uvicorn

from world_weaver.app import create_app
from world_weaver.config import get_settings, update_settings_file
from world_weaver.llm.factory import build_provider
from world_weaver.services.patch_service import WorldCodexPatchProposalService
from world_weaver.services.story_service import StoryService
from world_weaver.worldcodex_client import WorldCodexClientError, build_worldcodex_client

app = typer.Typer(help="World Weaver newsroom CLI")


def _default_model_for_provider(provider: str) -> str:
    if provider == "openai":
        return "gpt-4.1"
    return "mock-world-architect-v1"


def _worldcodex_guidance(command_name: str) -> None:
    settings = get_settings()
    typer.echo(
        f"`newsroom {command_name}` is deprecated because WorldCodex now owns world-building and canon storage."
    )
    typer.echo(f"Use WorldCodex directly for world operations, then set NEWSROOM_WORLDCODEX_WORLD={settings.worldcodex_world}.")
    typer.echo("WorldWeaver remains responsible for `generate-news`, `propose-world-patch`, feeds, and story APIs.")


def _archive_worldcodex_patch_run(
    *,
    snapshots_dir: Path,
    target_date: str,
    story_batch_payload: dict[str, Any],
    patch: dict[str, Any],
    validate_output: str,
    preview_output: str,
    apply_output: str | None,
) -> Path:
    snapshot_dir = snapshots_dir / target_date
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "story_batch.json": story_batch_payload,
        "worldcodex_patch.json": patch,
        "worldcodex_validate.txt": validate_output,
        "worldcodex_preview.txt": preview_output,
    }
    if apply_output is not None:
        artifacts["worldcodex_apply.txt"] = apply_output

    for filename, payload in artifacts.items():
        path = snapshot_dir / filename
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return snapshot_dir


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
def generate_news(
    target_date: str = typer.Option(..., "--date", help="Date in YYYY-MM-DD format"),
    body_words: int | None = typer.Option(None, "--body-words", help="Approximate target words per story body"),
) -> None:
    """Generate and persist a daily story batch."""
    settings = get_settings()
    parsed_date = date.fromisoformat(target_date)
    target_body_words = body_words or settings.default_story_body_words

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
        target_body_words=target_body_words,
    )
    output_path = story_service.save_batch(batch)
    typer.echo(f"Generated {len(batch.stories)} stories for {parsed_date.isoformat()} at {output_path}")


@app.command("update-world")
def update_world(
    target_date: str = typer.Option(..., "--date", help="Date in YYYY-MM-DD format"),
    apply: bool = typer.Option(False, "--apply", help="Apply the validated patch to WorldCodex after preview"),
) -> None:
    """Generate, validate, and preview or apply a WorldCodex patch from a story batch."""
    settings = get_settings()
    parsed_date = date.fromisoformat(target_date)

    provider = build_provider(settings)
    story_service = StoryService(
        settings.data_dir / "stories",
        provider=provider,
        prompts_dir=Path(__file__).resolve().parent / "prompts",
    )
    batch = story_service.load_batch(parsed_date)
    if batch is None:
        raise typer.BadParameter(f"Story batch not found for {parsed_date.isoformat()}")

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

    proposal_service = WorldCodexPatchProposalService(
        provider=provider,
        prompts_dir=Path(__file__).resolve().parent / "prompts",
        patches_dir=settings.data_dir / "patches",
    )
    patch = proposal_service.generate_patch(
        target_date=parsed_date.isoformat(),
        news_context=news_context,
        story_batch=batch,
        model=settings.llm_model,
    )
    patch_path = proposal_service.save_patch(patch, filename_stem=parsed_date.isoformat())

    try:
        validate_result = worldcodex.validate_patch(patch_path)
        preview_result = worldcodex.preview_patch(patch_path)
        apply_result = worldcodex.apply_patch(patch_path) if apply else None
    except WorldCodexClientError as exc:
        typer.echo(f"WorldCodex patch command failed: {exc}")
        raise typer.Exit(code=1) from exc

    snapshot_path = _archive_worldcodex_patch_run(
        snapshots_dir=settings.data_dir / "snapshots",
        target_date=parsed_date.isoformat(),
        story_batch_payload=batch.model_dump(mode="json"),
        patch=patch,
        validate_output=validate_result.stdout,
        preview_output=preview_result.stdout,
        apply_output=apply_result.stdout if apply_result is not None else None,
    )

    mode = "applied" if apply else "previewed"
    typer.echo(
        f"WorldCodex patch {mode} for {parsed_date.isoformat()} "
        f"(patch: {patch_path}, snapshot: {snapshot_path}, operations: {len(patch['operations'])})"
    )
    if not apply:
        typer.echo("No canon changes applied. Re-run with --apply to update WorldCodex.")


@app.command("propose-world-patch")
def propose_world_patch(target_date: str = typer.Option(..., "--date", help="Date in YYYY-MM-DD format")) -> None:
    """Generate and save a WorldCodex patch proposal from a story batch."""
    settings = get_settings()
    parsed_date = date.fromisoformat(target_date)

    provider = build_provider(settings)
    story_service = StoryService(
        settings.data_dir / "stories",
        provider=provider,
        prompts_dir=Path(__file__).resolve().parent / "prompts",
    )
    batch = story_service.load_batch(parsed_date)
    if batch is None:
        raise typer.BadParameter(f"Story batch not found for {parsed_date.isoformat()}")

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

    proposal_service = WorldCodexPatchProposalService(
        provider=provider,
        prompts_dir=Path(__file__).resolve().parent / "prompts",
        patches_dir=settings.data_dir / "patches",
    )
    patch = proposal_service.generate_patch(
        target_date=parsed_date.isoformat(),
        news_context=news_context,
        story_batch=batch,
        model=settings.llm_model,
    )
    patch_path = proposal_service.save_patch(patch, filename_stem=parsed_date.isoformat())

    typer.echo(
        "Generated WorldCodex patch proposal "
        f"for {parsed_date.isoformat()} at {patch_path} "
        f"({len(patch['operations'])} operations)"
    )


@app.command("add-canon")
def add_canon(
    text: str | None = typer.Option(None, "--text", help="Canon note text to merge into the world"),
    text_file: Path | None = typer.Option(None, "--file", help="Path to a text file containing a canon note"),
    target_date: str | None = typer.Option(None, "--date", help="Optional effective date in YYYY-MM-DD format"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Generate and show the patch without mutating canon or SQLite"),
) -> None:
    """Deprecated: manual canon edits belong in WorldCodex."""
    _worldcodex_guidance("add-canon")
    typer.echo("Create or apply a WorldCodex patch instead, for example `world patch validate|preview|apply <world> <patch.json>`.")
    raise typer.Exit(code=2)


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
    """Deprecated: initial world creation belongs in WorldCodex."""
    _worldcodex_guidance("init-world")
    typer.echo("Create the world in WorldCodex, then run `newsroom generate-news --date YYYY-MM-DD`.")
    raise typer.Exit(code=2)


@app.command("ingest-world-bible")
def ingest_world_bible(
    source_markdown: Path = typer.Option(
        Path("data/world-bible.md"),
        "--source-markdown",
        help="Deprecated legacy source markdown path",
    ),
    seed_json: Path = typer.Option(
        Path("data/worlds/world_bible.seed.v1.json"),
        "--seed-json",
        help="Deprecated legacy seed JSON path",
    ),
    world_id: str | None = typer.Option(
        None,
        "--world-id",
        help="Optional world ID override for database ingestion",
    ),
) -> None:
    """Deprecated: world bible ingestion belongs in WorldCodex."""
    _worldcodex_guidance("ingest-world-bible")
    typer.echo("Migrate legacy world bible data into WorldCodex atoms, relationships, timeline, and canon state.")
    raise typer.Exit(code=2)


@app.command("world-summary")
def world_summary(
    world_path: Path | None = typer.Option(
        None,
        "--world-path",
        help="Deprecated legacy world JSON path",
    ),
    world_id: str | None = typer.Option(
        None,
        "--world-id",
        help="Optional world ID override for SQLite entity counts",
    ),
    output: str = typer.Option(
        "text",
        "--output",
        help="Output format",
    ),
) -> None:
    """Deprecated: world summaries belong in WorldCodex exports."""
    _worldcodex_guidance("world-summary")
    typer.echo("Use `world export <world> world-bible` or `world export <world> news-context`.")
    raise typer.Exit(code=2)


if __name__ == "__main__":
    app()

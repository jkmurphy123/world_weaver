from datetime import date

import typer
import uvicorn

from world_weaver.app import create_app
from world_weaver.config import get_settings
from world_weaver.services.story_service import StoryService
from world_weaver.services.world_generation import WorldGenerationService

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


if __name__ == "__main__":
    app()

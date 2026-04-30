from datetime import date, datetime, timezone

from fastapi import FastAPI, HTTPException, Response

from world_weaver.bootstrap import ensure_data_dirs
from world_weaver.config import get_settings
from world_weaver.logging_setup import configure_logging
from world_weaver.schemas import HealthResponse, StoryBatch
from world_weaver.services.feed_service import FeedService
from world_weaver.services.story_service import StoryService


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    ensure_data_dirs(settings.data_dir)

    app = FastAPI(title="World Weaver")
    app.state.settings = settings

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", app=settings.app_name)

    @app.get("/stories/today", response_model=StoryBatch)
    def get_stories_today() -> StoryBatch:
        service = StoryService(settings.data_dir / "stories")
        today = datetime.now(timezone.utc).date()
        batch = service.load_batch(today)
        if batch is None:
            raise HTTPException(status_code=404, detail="Story batch not found for date")
        return batch

    @app.get("/stories/latest", response_model=StoryBatch)
    def get_latest_stories() -> StoryBatch:
        service = StoryService(settings.data_dir / "stories")
        batch = service.load_latest_batch()
        if batch is None:
            raise HTTPException(status_code=404, detail="No story batches have been published")
        return batch

    @app.get("/stories/{target_date}", response_model=StoryBatch)
    def get_stories_by_date(target_date: date) -> StoryBatch:
        service = StoryService(settings.data_dir / "stories")
        batch = service.load_batch(target_date)
        if batch is None:
            raise HTTPException(status_code=404, detail="Story batch not found for date")
        return batch

    @app.get("/feed/rss.xml")
    @app.get("/feeds/rss.xml")
    def get_rss_feed() -> Response:
        feed_service = FeedService(settings.data_dir / "stories", app_name=settings.app_name)
        stories = feed_service.load_published_stories()
        return Response(content=feed_service.build_rss(stories), media_type="application/rss+xml")

    @app.get("/feed/atom.xml")
    @app.get("/feeds/atom.xml")
    def get_atom_feed() -> Response:
        feed_service = FeedService(settings.data_dir / "stories", app_name=settings.app_name)
        stories = feed_service.load_published_stories()
        return Response(content=feed_service.build_atom(stories), media_type="application/atom+xml")

    return app


app = create_app()

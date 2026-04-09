from __future__ import annotations

import json
from datetime import UTC, datetime
from email.utils import format_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from world_weaver.schemas import Story, StoryBatch


class FeedService:
    """Build RSS and Atom feeds from persisted story batches."""

    def __init__(self, stories_dir: Path, *, app_name: str, base_url: str = "http://localhost:8000") -> None:
        self._stories_dir = stories_dir
        self._app_name = app_name
        self._base_url = base_url.rstrip("/")

    def load_published_stories(self, *, limit: int = 50) -> list[Story]:
        stories: list[Story] = []
        if not self._stories_dir.exists():
            return stories

        for path in sorted(self._stories_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            batch = StoryBatch.model_validate(payload)
            stories.extend(batch.stories)

        stories.sort(key=lambda story: (story.metadata.published_at, story.metadata.story_id), reverse=True)
        return stories[:limit]

    def build_rss(self, stories: list[Story]) -> str:
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")
        ET.SubElement(channel, "title").text = f"{self._app_name} stories"
        ET.SubElement(channel, "link").text = f"{self._base_url}/stories/today"
        ET.SubElement(channel, "description").text = "Latest published World Weaver stories."
        ET.SubElement(channel, "lastBuildDate").text = format_datetime(self._rss_timestamp(stories))

        for story in stories:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = story.headline
            ET.SubElement(item, "description").text = story.summary
            ET.SubElement(item, "link").text = self._story_link(story)
            ET.SubElement(item, "guid").text = story.metadata.story_id
            ET.SubElement(item, "pubDate").text = format_datetime(story.metadata.published_at.astimezone(UTC))
            ET.SubElement(item, "category").text = story.category
            ET.SubElement(item, "storyId").text = story.metadata.story_id
            ET.SubElement(item, "targetDate").text = story.metadata.target_date.isoformat()
            ET.SubElement(item, "worldId").text = story.metadata.world_id

        return ET.tostring(rss, encoding="unicode", xml_declaration=True)

    def build_atom(self, stories: list[Story]) -> str:
        feed = ET.Element("feed", xmlns="http://www.w3.org/2005/Atom")
        ET.SubElement(feed, "title").text = f"{self._app_name} stories"
        ET.SubElement(feed, "id").text = f"{self._base_url}/feeds/atom.xml"
        ET.SubElement(feed, "updated").text = self._atom_timestamp(stories)
        ET.SubElement(feed, "link", href=f"{self._base_url}/feeds/atom.xml", rel="self")

        for story in stories:
            entry = ET.SubElement(feed, "entry")
            ET.SubElement(entry, "title").text = story.headline
            ET.SubElement(entry, "id").text = f"urn:story:{story.metadata.story_id}"
            ET.SubElement(entry, "updated").text = story.metadata.published_at.astimezone(UTC).isoformat()
            ET.SubElement(entry, "published").text = story.metadata.published_at.astimezone(UTC).isoformat()
            ET.SubElement(entry, "summary").text = story.summary
            ET.SubElement(entry, "content", type="text").text = story.body
            ET.SubElement(entry, "category", term=story.category)
            ET.SubElement(entry, "link", href=self._story_link(story), rel="alternate")
            ET.SubElement(entry, "storyId").text = story.metadata.story_id
            ET.SubElement(entry, "targetDate").text = story.metadata.target_date.isoformat()
            ET.SubElement(entry, "worldId").text = story.metadata.world_id

        return ET.tostring(feed, encoding="unicode", xml_declaration=True)

    def _story_link(self, story: Story) -> str:
        return f"{self._base_url}/stories/{story.metadata.target_date.isoformat()}#{story.metadata.story_id}"

    def _rss_timestamp(self, stories: list[Story]):
        if stories:
            return stories[0].metadata.published_at.astimezone(UTC)
        return datetime.now(tz=UTC)

    def _atom_timestamp(self, stories: list[Story]) -> str:
        if stories:
            return stories[0].metadata.published_at.astimezone(UTC).isoformat()
        return datetime.now(tz=UTC).isoformat()

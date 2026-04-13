from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from world_weaver.schemas import CanonLocation, CanonOrganization, CanonPerson, CanonUpdatePatch, ContinuityFact, OpenThread, TimelineEvent, WorldBible
from world_weaver.services.init_world_service import InitWorldService

TCanon = TypeVar("TCanon", CanonPerson, CanonOrganization, CanonLocation, OpenThread, TimelineEvent)


@dataclass(slots=True, frozen=True)
class MergeReport:
    people_added: int
    people_updated: int
    organizations_added: int
    organizations_updated: int
    locations_added: int
    locations_updated: int
    timeline_events_added: int
    open_threads_added: int
    open_threads_resolved: int
    major_facts_added: int
    warnings: list[str]


class MergeService:
    """Apply a structured patch to the canonical world bible and archive the run."""

    def __init__(self, *, worlds_dir: Path, snapshots_dir: Path) -> None:
        self._worlds_dir = worlds_dir
        self._snapshots_dir = snapshots_dir

    def apply_patch(self, *, world_bible: WorldBible, patch: CanonUpdatePatch) -> tuple[WorldBible, MergeReport]:
        merged_world = world_bible.model_copy(deep=True)

        people_added, people_updated = self._merge_entities(
            merged_world.people,
            patch.new_people,
            patch.updated_people,
        )
        organizations_added, organizations_updated = self._merge_entities(
            merged_world.organizations,
            patch.new_organizations,
            patch.updated_organizations,
        )
        locations_added, locations_updated = self._merge_entities(
            merged_world.locations,
            patch.new_locations,
            patch.updated_locations,
        )
        timeline_events_added = self._merge_timeline(merged_world.timeline, patch.timeline_events)
        open_threads_added, open_threads_resolved = self._merge_open_threads(
            merged_world.open_threads,
            patch.open_threads_added,
            patch.open_threads_resolved,
        )
        major_facts_added = self._merge_major_facts(merged_world, patch.major_facts_added)

        if merged_world.continuity is not None:
            merged_world.continuity.current_date = patch.date

        report = MergeReport(
            people_added=people_added,
            people_updated=people_updated,
            organizations_added=organizations_added,
            organizations_updated=organizations_updated,
            locations_added=locations_added,
            locations_updated=locations_updated,
            timeline_events_added=timeline_events_added,
            open_threads_added=open_threads_added,
            open_threads_resolved=open_threads_resolved,
            major_facts_added=major_facts_added,
            warnings=list(patch.continuity_warnings),
        )
        return merged_world, report

    def save_world(self, world_bible: WorldBible) -> tuple[Path, Path]:
        self._worlds_dir.mkdir(parents=True, exist_ok=True)
        json_path = self._worlds_dir / "world_bible.json"
        markdown_path = self._worlds_dir / "world_bible.md"
        json_path.write_text(json.dumps(world_bible.model_dump(mode="json"), indent=2), encoding="utf-8")
        markdown_path.write_text(InitWorldService._to_markdown_summary(world_bible), encoding="utf-8")
        return json_path, markdown_path

    def archive_run(
        self,
        *,
        target_date: str,
        world_before: WorldBible,
        story_batch_payload: dict,
        patch: CanonUpdatePatch,
        world_after: WorldBible,
        merge_report: MergeReport,
    ) -> Path:
        snapshot_dir = self._snapshots_dir / target_date
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        (snapshot_dir / "world_before.json").write_text(
            json.dumps(world_before.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        (snapshot_dir / "stories.json").write_text(json.dumps(story_batch_payload, indent=2), encoding="utf-8")
        (snapshot_dir / "patch.json").write_text(
            json.dumps(patch.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        (snapshot_dir / "world_after.json").write_text(
            json.dumps(world_after.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        (snapshot_dir / "merge_report.json").write_text(
            json.dumps(
                {
                    "people_added": merge_report.people_added,
                    "people_updated": merge_report.people_updated,
                    "organizations_added": merge_report.organizations_added,
                    "organizations_updated": merge_report.organizations_updated,
                    "locations_added": merge_report.locations_added,
                    "locations_updated": merge_report.locations_updated,
                    "timeline_events_added": merge_report.timeline_events_added,
                    "open_threads_added": merge_report.open_threads_added,
                    "open_threads_resolved": merge_report.open_threads_resolved,
                    "major_facts_added": merge_report.major_facts_added,
                    "warnings": merge_report.warnings,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return snapshot_dir

    def _merge_entities(
        self,
        current: list[TCanon],
        new_items: list[TCanon],
        updated_items: list[TCanon],
    ) -> tuple[int, int]:
        added = 0
        updated = 0

        for item in updated_items:
            index = self._find_match_index(current, item)
            if index is None:
                current.append(item)
                added += 1
                continue
            current[index] = item
            updated += 1

        for item in new_items:
            index = self._find_match_index(current, item)
            if index is None:
                current.append(item)
                added += 1
                continue
            current[index] = item
            updated += 1

        return added, updated

    @staticmethod
    def _merge_timeline(current: list[TimelineEvent], patch_events: list[TimelineEvent]) -> int:
        added = 0
        existing_keys = {(event.id, event.date.isoformat(), event.title.strip().lower()) for event in current}
        for event in patch_events:
            key = (event.id, event.date.isoformat(), event.title.strip().lower())
            if key in existing_keys:
                continue
            current.append(event)
            existing_keys.add(key)
            added += 1
        current.sort(key=lambda event: (event.date, event.id))
        return added

    @staticmethod
    def _merge_open_threads(
        current: list[OpenThread],
        added_threads: list[OpenThread],
        resolved_threads: list[str],
    ) -> tuple[int, int]:
        added = 0
        resolved = 0
        existing_keys = {(thread.id, thread.title.strip().lower()) for thread in current}
        for thread in added_threads:
            key = (thread.id, thread.title.strip().lower())
            if key in existing_keys:
                continue
            current.append(thread)
            existing_keys.add(key)
            added += 1

        if not resolved_threads:
            return added, resolved

        for thread in current:
            if thread.id in resolved_threads or thread.title in resolved_threads:
                if thread.status != "resolved":
                    thread.status = "resolved"
                    resolved += 1
        return added, resolved

    @staticmethod
    def _merge_major_facts(world_bible: WorldBible, major_facts: list[ContinuityFact]) -> int:
        if world_bible.continuity is None:
            return 0

        existing_texts = {
            fact.text.strip().lower()
            for fact in world_bible.continuity.major_facts
            if isinstance(fact, ContinuityFact) and fact.text.strip()
        }
        added = 0
        for fact in major_facts:
            normalized = fact.text.strip().lower()
            if not normalized or normalized in existing_texts:
                continue
            world_bible.continuity.major_facts.append(fact)
            existing_texts.add(normalized)
            added += 1
        return added

    @staticmethod
    def _find_match_index(current: list[TCanon], candidate: TCanon) -> int | None:
        candidate_name = getattr(candidate, "name", "").strip().lower()
        candidate_id = getattr(candidate, "id", None)
        for index, existing in enumerate(current):
            existing_id = getattr(existing, "id", None)
            existing_name = getattr(existing, "name", "").strip().lower()
            if candidate_id and existing_id == candidate_id:
                return index
            if candidate_name and existing_name == candidate_name:
                return index
        return None

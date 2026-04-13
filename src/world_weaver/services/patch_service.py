from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from world_weaver.llm.base import LLMProvider, PromptRequest
from world_weaver.schemas import CanonUpdatePatch, StoryBatch, WorldBible


class PatchService:
    """Generate and persist canon update patches from a story batch."""

    def __init__(
        self,
        *,
        provider: LLMProvider,
        prompts_dir: Path,
        patches_dir: Path,
    ) -> None:
        self._provider = provider
        self._prompts_dir = prompts_dir
        self._patches_dir = patches_dir

    def generate_patch(
        self,
        *,
        target_date: str,
        world_bible: WorldBible,
        story_batch: StoryBatch,
        model: str,
    ) -> CanonUpdatePatch:
        request = PromptRequest(
            system_prompt=self._load_prompt_template("world_architect_patch.md"),
            user_prompt=json.dumps(
                {
                    "target_date": target_date,
                    "world_bible": world_bible.model_dump(mode="json"),
                    "story_batch": story_batch.model_dump(mode="json"),
                },
                separators=(",", ":"),
            ),
            model=model,
        )
        patch = self._generate_patch_from_request(request)

        if patch.date.isoformat() != target_date:
            raise ValueError("World architect patch date did not match requested target date")

        return patch

    def generate_patch_from_note(
        self,
        *,
        target_date: str,
        world_bible: WorldBible,
        source_text: str,
        model: str,
    ) -> CanonUpdatePatch:
        request = PromptRequest(
            system_prompt=self._load_prompt_template("world_architect_manual_update.md"),
            user_prompt=json.dumps(
                {
                    "target_date": target_date,
                    "world_bible": world_bible.model_dump(mode="json"),
                    "source_text": source_text.strip(),
                },
                separators=(",", ":"),
            ),
            model=model,
        )
        patch = self._generate_patch_from_request(request)

        if patch.date.isoformat() != target_date:
            raise ValueError("World architect patch date did not match requested target date")

        return patch

    def save_patch(self, patch: CanonUpdatePatch, *, filename_stem: str | None = None) -> Path:
        self._patches_dir.mkdir(parents=True, exist_ok=True)
        stem = filename_stem or patch.date.isoformat()
        output_path = self._patches_dir / f"{stem}.json"
        output_path.write_text(json.dumps(patch.model_dump(mode="json"), indent=2), encoding="utf-8")
        return output_path

    def load_patch(self, target_date: str) -> CanonUpdatePatch | None:
        path = self._patches_dir / f"{target_date}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return CanonUpdatePatch.model_validate(payload)

    def _generate_patch_from_request(self, request: PromptRequest) -> CanonUpdatePatch:
        raw_response = self._provider.generate_json(request)

        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise ValueError("World architect returned invalid patch JSON") from exc

        try:
            patch = CanonUpdatePatch.model_validate(payload)
        except ValidationError as exc:
            raise ValueError("World architect patch did not match CanonUpdatePatch schema") from exc
        return patch

    def _load_prompt_template(self, filename: str) -> str:
        return (self._prompts_dir / filename).read_text(encoding="utf-8")

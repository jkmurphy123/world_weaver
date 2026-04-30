from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from world_weaver.llm.base import LLMProvider, PromptRequest
from world_weaver.schemas import CanonUpdatePatch, StoryBatch, WorldBible

WORLDCODEX_PATCH_SCHEMA_VERSION = "worldcodex.patch.v1"
SUPPORTED_WORLDCODEX_PATCH_OPS = {
    "add_atom",
    "update_atom",
    "deprecate_atom",
    "add_relationship",
    "update_relationship",
    "add_timeline_event",
    "resolve_conflict",
}


def validate_worldcodex_patch_payload(patch: dict[str, Any]) -> None:
    """Validate the portable shape WorldWeaver expects before WorldCodex sees it."""

    if patch.get("schema_version") != WORLDCODEX_PATCH_SCHEMA_VERSION:
        raise ValueError(f"WorldCodex patch schema_version must be {WORLDCODEX_PATCH_SCHEMA_VERSION!r}")

    operations = patch.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError("WorldCodex patch must contain a non-empty operations list")

    for index, operation in enumerate(operations, start=1):
        if not isinstance(operation, dict):
            raise ValueError(f"WorldCodex patch operations[{index}] must be an object")

        op = operation.get("op")
        if op not in SUPPORTED_WORLDCODEX_PATCH_OPS:
            supported = ", ".join(sorted(SUPPORTED_WORLDCODEX_PATCH_OPS))
            raise ValueError(f"WorldCodex patch operations[{index}].op must be one of: {supported}")

        if op in {"add_atom", "add_timeline_event"}:
            atom = operation.get("atom")
            if not isinstance(atom, dict):
                raise ValueError(f"WorldCodex patch operations[{index}].atom must be an object")
            if not isinstance(atom.get("id"), str) or not atom["id"].strip():
                raise ValueError(f"WorldCodex patch operations[{index}].atom.id must be a non-empty string")
            if not isinstance(atom.get("type"), str) or not atom["type"].strip():
                raise ValueError(f"WorldCodex patch operations[{index}].atom.type must be a non-empty string")
            if op == "add_timeline_event" and atom.get("type") != "event":
                raise ValueError(f"WorldCodex patch operations[{index}].atom.type must be 'event'")

        if op in {"update_atom", "deprecate_atom", "resolve_conflict"}:
            if not isinstance(operation.get("atom_id"), str) or not operation["atom_id"].strip():
                raise ValueError(f"WorldCodex patch operations[{index}].atom_id must be a non-empty string")

        if op in {"add_relationship", "update_relationship"}:
            if not isinstance(operation.get("subject"), str) or not operation["subject"].strip():
                raise ValueError(f"WorldCodex patch operations[{index}].subject must be a non-empty string")
            if op == "add_relationship" and (
                not isinstance(operation.get("object"), str) or not operation["object"].strip()
            ):
                raise ValueError(f"WorldCodex patch operations[{index}].object must be a non-empty string")
            if not isinstance(operation.get("predicate"), str) or not operation["predicate"].strip():
                raise ValueError(f"WorldCodex patch operations[{index}].predicate must be a non-empty string")


class WorldCodexPatchProposalService:
    """Generate and persist WorldCodex patch proposals from newsroom stories."""

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
        news_context: dict[str, Any],
        story_batch: StoryBatch,
        model: str,
    ) -> dict[str, Any]:
        request = PromptRequest(
            system_prompt=self._load_prompt_template("worldcodex_patch_proposal.md"),
            user_prompt=json.dumps(
                {
                    "target_date": target_date,
                    "news_context": news_context,
                    "story_batch": story_batch.model_dump(mode="json"),
                },
                separators=(",", ":"),
            ),
            model=model,
        )
        patch = self._generate_patch_from_request(request)
        validate_worldcodex_patch_payload(patch)
        return patch

    def save_patch(self, patch: dict[str, Any], *, filename_stem: str | None = None) -> Path:
        validate_worldcodex_patch_payload(patch)
        self._patches_dir.mkdir(parents=True, exist_ok=True)
        stem = filename_stem or str(patch.get("id") or "worldcodex-patch")
        output_path = self._patches_dir / f"{stem}.json"
        output_path.write_text(json.dumps(patch, indent=2), encoding="utf-8")
        return output_path

    def load_patch(self, filename_stem: str) -> dict[str, Any] | None:
        path = self._patches_dir / f"{filename_stem}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("WorldCodex patch file must contain a JSON object")
        validate_worldcodex_patch_payload(payload)
        return payload

    def _generate_patch_from_request(self, request: PromptRequest) -> dict[str, Any]:
        raw_response = self._provider.generate_json(request)

        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise ValueError("WorldCodex patch proposer returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise ValueError("WorldCodex patch proposer must return a JSON object")
        return payload

    def _load_prompt_template(self, filename: str) -> str:
        return (self._prompts_dir / filename).read_text(encoding="utf-8")


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

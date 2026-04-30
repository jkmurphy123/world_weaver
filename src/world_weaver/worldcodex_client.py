from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CommandResult:
    """Result returned by a WorldCodex CLI command."""

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class WorldCodexClientError(RuntimeError):
    """Raised when a WorldCodex command fails or returns invalid output."""


CommandRunner = Callable[[Sequence[str], int], CommandResult]


def _default_runner(args: Sequence[str], timeout_seconds: int) -> CommandResult:
    completed = subprocess.run(
        list(args),
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout_seconds,
    )
    return CommandResult(
        args=tuple(args),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


class WorldCodexClient:
    """Small CLI-backed adapter for WorldCodex.

    The client is intentionally narrow so WorldWeaver can later swap the
    subprocess implementation for a Python package without changing services.
    """

    def __init__(
        self,
        *,
        world_id: str,
        cli: str = "world",
        timeout_seconds: int = 60,
        runner: CommandRunner | None = None,
    ) -> None:
        self._world_id = world_id
        self._cli = cli
        self._timeout_seconds = timeout_seconds
        self._runner = runner or _default_runner

    @property
    def world_id(self) -> str:
        return self._world_id

    def export_context(self, context_type: str) -> dict[str, Any]:
        result = self._run([self._cli, "export", self._world_id, context_type])
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise WorldCodexClientError(
                f"WorldCodex export returned invalid JSON for context '{context_type}'"
            ) from exc

        if not isinstance(payload, dict):
            raise WorldCodexClientError(
                f"WorldCodex export for context '{context_type}' must return a JSON object"
            )
        return payload

    def validate_patch(self, patch_path: Path) -> CommandResult:
        return self._run_patch_command("validate", patch_path)

    def preview_patch(self, patch_path: Path) -> CommandResult:
        return self._run_patch_command("preview", patch_path)

    def apply_patch(self, patch_path: Path) -> CommandResult:
        return self._run_patch_command("apply", patch_path)

    def _run_patch_command(self, action: str, patch_path: Path) -> CommandResult:
        return self._run([self._cli, "patch", action, self._world_id, str(patch_path)])

    def _run(self, args: Sequence[str]) -> CommandResult:
        try:
            result = self._runner(args, self._timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            raise WorldCodexClientError(
                f"WorldCodex command timed out after {self._timeout_seconds}s: {' '.join(args)}"
            ) from exc
        except OSError as exc:
            raise WorldCodexClientError(f"Unable to run WorldCodex command: {' '.join(args)}") from exc

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "no output"
            raise WorldCodexClientError(
                f"WorldCodex command failed with exit code {result.returncode}: {' '.join(args)}\n{detail}"
            )
        return result


def build_worldcodex_client(
    *,
    world_id: str,
    cli: str = "world",
    timeout_seconds: int = 60,
) -> WorldCodexClient:
    return WorldCodexClient(
        world_id=world_id,
        cli=cli,
        timeout_seconds=timeout_seconds,
    )

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence

import pytest

from world_weaver.worldcodex_client import CommandResult, WorldCodexClient, WorldCodexClientError


class FakeRunner:
    def __init__(self, results: list[CommandResult]) -> None:
        self.results = results
        self.calls: list[tuple[tuple[str, ...], int]] = []

    def __call__(self, args: Sequence[str], timeout_seconds: int) -> CommandResult:
        self.calls.append((tuple(args), timeout_seconds))
        if not self.results:
            raise AssertionError(f"Unexpected command: {args}")
        return self.results.pop(0)


def test_export_context_builds_worldcodex_command_and_parses_json() -> None:
    runner = FakeRunner(
        [
            CommandResult(
                args=("world", "export", "titan-osa", "news-context"),
                returncode=0,
                stdout='{"schema_version":"worldcodex.context.news.v1","world":{"id":"titan-osa"}}',
                stderr="",
            )
        ]
    )
    client = WorldCodexClient(world_id="titan-osa", timeout_seconds=12, runner=runner)

    payload = client.export_context("news-context")

    assert payload["world"]["id"] == "titan-osa"
    assert runner.calls == [(("world", "export", "titan-osa", "news-context"), 12)]


def test_export_context_rejects_invalid_json() -> None:
    runner = FakeRunner(
        [
            CommandResult(
                args=("world", "export", "titan-osa", "news-context"),
                returncode=0,
                stdout="not json",
                stderr="",
            )
        ]
    )
    client = WorldCodexClient(world_id="titan-osa", runner=runner)

    with pytest.raises(WorldCodexClientError, match="invalid JSON"):
        client.export_context("news-context")


def test_export_context_requires_json_object() -> None:
    runner = FakeRunner(
        [
            CommandResult(
                args=("world", "export", "titan-osa", "news-context"),
                returncode=0,
                stdout='["not", "an", "object"]',
                stderr="",
            )
        ]
    )
    client = WorldCodexClient(world_id="titan-osa", runner=runner)

    with pytest.raises(WorldCodexClientError, match="must return a JSON object"):
        client.export_context("news-context")


def test_patch_commands_build_expected_arguments() -> None:
    runner = FakeRunner(
        [
            CommandResult(args=(), returncode=0, stdout="valid", stderr=""),
            CommandResult(args=(), returncode=0, stdout="preview", stderr=""),
            CommandResult(args=(), returncode=0, stdout="applied", stderr=""),
        ]
    )
    client = WorldCodexClient(
        world_id="titan-osa",
        cli="/opt/worldcodex/bin/world",
        timeout_seconds=30,
        runner=runner,
    )
    patch_path = Path("/tmp/patch.json")

    assert client.validate_patch(patch_path).stdout == "valid"
    assert client.preview_patch(patch_path).stdout == "preview"
    assert client.apply_patch(patch_path).stdout == "applied"

    assert runner.calls == [
        (("/opt/worldcodex/bin/world", "patch", "validate", "titan-osa", "/tmp/patch.json"), 30),
        (("/opt/worldcodex/bin/world", "patch", "preview", "titan-osa", "/tmp/patch.json"), 30),
        (("/opt/worldcodex/bin/world", "patch", "apply", "titan-osa", "/tmp/patch.json"), 30),
    ]


def test_nonzero_command_raises_useful_error() -> None:
    runner = FakeRunner(
        [
            CommandResult(
                args=("world", "patch", "validate", "titan-osa", "/tmp/patch.json"),
                returncode=2,
                stdout="",
                stderr="schema mismatch",
            )
        ]
    )
    client = WorldCodexClient(world_id="titan-osa", runner=runner)

    with pytest.raises(WorldCodexClientError, match="schema mismatch"):
        client.validate_patch(Path("/tmp/patch.json"))


def test_timeout_is_reported_as_client_error() -> None:
    def runner(args: Sequence[str], timeout_seconds: int) -> CommandResult:
        raise subprocess.TimeoutExpired(args, timeout_seconds)

    client = WorldCodexClient(world_id="titan-osa", timeout_seconds=1, runner=runner)

    with pytest.raises(WorldCodexClientError, match="timed out"):
        client.export_context("news-context")

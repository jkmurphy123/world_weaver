from typer.testing import CliRunner

from world_weaver.cli import app


runner = CliRunner()


def test_cli_help_works() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.stdout


def test_serve_help_works() -> None:
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "Run the newsroom API server." in result.stdout


def test_generate_news_command_persists_batch_by_date(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))

    result = runner.invoke(app, ["generate-news", "--date", "2026-04-09"])

    assert result.exit_code == 0
    assert "Generated 4 stories for 2026-04-09" in result.stdout
    assert (tmp_path / "stories" / "2026-04-09.json").exists()


def test_init_world_command_accepts_prompt_text(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_LLM_PROVIDER", "mock")

    result = runner.invoke(app, ["init-world", "--prompt", "A dense floating city ruled by data cartels."])

    assert result.exit_code == 0
    assert "Initialized world" in result.stdout
    assert (tmp_path / "worlds" / "world_bible.json").exists()
    assert (tmp_path / "worlds" / "world_bible.md").exists()


def test_init_world_command_accepts_prompt_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEWSROOM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NEWSROOM_LLM_PROVIDER", "mock")
    prompt_file = tmp_path / "seed.txt"
    prompt_file.write_text("Megacorps rule a stacked harbor metropolis.", encoding="utf-8")

    result = runner.invoke(app, ["init-world", "--prompt-file", str(prompt_file)])

    assert result.exit_code == 0
    assert (tmp_path / "worlds" / "world_bible.json").exists()


def test_init_world_requires_exactly_one_prompt_input() -> None:
    result = runner.invoke(app, ["init-world"])
    assert result.exit_code != 0
    combined_output = f"{result.stdout}\n{result.stderr}"
    assert "Provide exactly one of --prompt or --prompt-file" in combined_output

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

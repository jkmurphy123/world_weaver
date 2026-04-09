from pathlib import Path

BOOTSTRAP_DIRS = (
    "worlds",
    "stories",
    "snapshots",
    "logs",
)


def ensure_data_dirs(base_dir: Path) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    for dirname in BOOTSTRAP_DIRS:
        (base_dir / dirname).mkdir(parents=True, exist_ok=True)

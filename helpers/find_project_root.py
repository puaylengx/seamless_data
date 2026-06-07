from pathlib import Path


def find_project_root(start: Path) -> Path:
    for p in [start] + list(start.parents):
        if (p / "requirements.txt").exists() or (p / ".git").exists():
            return p
    return start.parents[0]

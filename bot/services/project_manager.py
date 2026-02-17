import logging
from pathlib import Path

from bot.config import CLAUDE_PROJECTS_DIR, STANDALONE_PROJECTS

logger = logging.getLogger(__name__)


def _detect_project_type(path: Path) -> str:
    if (path / "package.json").exists():
        if (path / "next.config.js").exists() or (path / "next.config.mjs").exists() or (path / "next.config.ts").exists():
            return "next.js"
        return "node"
    if (path / "pyproject.toml").exists() or (path / "setup.py").exists() or (path / "requirements.txt").exists():
        return "python"
    if any(path.glob("*.uproject")):
        return "unreal"
    if (path / "Cargo.toml").exists():
        return "rust"
    if (path / "go.mod").exists():
        return "go"
    return "unknown"


def list_projects() -> list[dict]:
    """Devuelve lista de proyectos disponibles con nombre, ruta y tipo."""
    projects = []

    if CLAUDE_PROJECTS_DIR.exists():
        for child in sorted(CLAUDE_PROJECTS_DIR.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                projects.append({
                    "name": child.name,
                    "path": str(child),
                    "type": _detect_project_type(child),
                })

    for name, path_str in STANDALONE_PROJECTS.items():
        p = Path(path_str)
        if p.exists():
            projects.append({
                "name": name,
                "path": path_str,
                "type": _detect_project_type(p),
            })

    return projects


def find_project(name: str) -> dict | None:
    """Busca un proyecto por nombre (case-insensitive)."""
    for proj in list_projects():
        if proj["name"].lower() == name.lower():
            return proj
    return None

import json
import logging
from pathlib import Path

from bot.config import SESSIONS_DIR

logger = logging.getLogger(__name__)

STATE_FILE = SESSIONS_DIR / "user_state.json"

# Caché en memoria — se carga una sola vez
_cache: dict | None = None


def _load_state() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    if STATE_FILE.exists():
        try:
            _cache = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return _cache
        except (json.JSONDecodeError, OSError):
            logger.warning("Estado corrupto, reiniciando")
    _cache = {"active_project": None, "sessions": {}}
    return _cache


def _save_state(state: dict) -> None:
    global _cache
    _cache = state
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def get_active_project() -> str | None:
    return _load_state().get("active_project")


def set_active_project(project_name: str) -> None:
    state = _load_state()
    state["active_project"] = project_name
    _save_state(state)


def get_session_id(project_name: str) -> str | None:
    state = _load_state()
    return state.get("sessions", {}).get(project_name, {}).get("session_id")


def save_session_id(project_name: str, session_id: str) -> None:
    state = _load_state()
    if "sessions" not in state:
        state["sessions"] = {}
    if project_name not in state["sessions"]:
        state["sessions"][project_name] = {}
    state["sessions"][project_name]["session_id"] = session_id
    _save_state(state)


def clear_session(project_name: str) -> None:
    state = _load_state()
    if project_name in state.get("sessions", {}):
        del state["sessions"][project_name]
    _save_state(state)


def get_session_info(project_name: str) -> dict:
    state = _load_state()
    return {
        "active_project": state.get("active_project"),
        "session_id": state.get("sessions", {}).get(project_name, {}).get("session_id"),
    }

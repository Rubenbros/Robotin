"""Gestión del pool de tokens de Telegram para worker bots."""

import json
import logging
import os
import urllib.request

from bot.config import TOKEN_POOL_FILE

logger = logging.getLogger(__name__)

_cache: dict | None = None


def _load_pool() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    if TOKEN_POOL_FILE.exists():
        try:
            _cache = json.loads(TOKEN_POOL_FILE.read_text(encoding="utf-8"))
            return _cache
        except (json.JSONDecodeError, OSError):
            logger.warning("token_pool.json corrupto, reiniciando")
    _cache = {"tokens": []}
    return _cache


def _save_pool(pool: dict) -> None:
    global _cache
    _cache = pool
    TOKEN_POOL_FILE.write_text(json.dumps(pool, indent=2, ensure_ascii=False), encoding="utf-8")


def list_tokens() -> list[dict]:
    """Retorna todos los tokens del pool."""
    return _load_pool().get("tokens", [])


def get_available_tokens() -> list[dict]:
    """Retorna los tokens disponibles (no en uso)."""
    return [t for t in list_tokens() if t.get("status") == "available"]


def acquire_token(project: str, role: str, pid: int) -> dict | None:
    """Reserva un token libre para un worker. Retorna el token o None."""
    pool = _load_pool()
    for token in pool["tokens"]:
        if token["status"] == "available":
            token["status"] = "in_use"
            token["assigned_project"] = project
            token["assigned_role"] = role
            token["pid"] = pid
            _save_pool(pool)
            return token
    return None


def release_token(token_id: str) -> bool:
    """Libera un token (lo marca como disponible). Retorna True si lo encontró."""
    pool = _load_pool()
    for token in pool["tokens"]:
        if token["id"] == token_id:
            token["status"] = "available"
            token["assigned_project"] = None
            token["assigned_role"] = None
            token["pid"] = None
            _save_pool(pool)
            return True
    return False


def update_pid(token_id: str, pid: int) -> None:
    """Actualiza el PID asociado a un token."""
    pool = _load_pool()
    for token in pool["tokens"]:
        if token["id"] == token_id:
            token["pid"] = pid
            _save_pool(pool)
            return


def _is_pid_alive(pid: int) -> bool:
    """Comprueba si un proceso sigue vivo."""
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def release_stale_tokens() -> list[str]:
    """Libera tokens cuyo proceso ya no existe. Retorna IDs liberados."""
    pool = _load_pool()
    released = []
    for token in pool["tokens"]:
        if token["status"] == "in_use" and not _is_pid_alive(token.get("pid", 0)):
            logger.warning(f"Token {token['id']} huerfano (PID {token.get('pid')} muerto), liberando")
            token["status"] = "available"
            token["assigned_project"] = None
            token["assigned_role"] = None
            token["pid"] = None
            released.append(token["id"])
    if released:
        _save_pool(pool)
    return released


def validate_token(bot_token: str) -> dict | None:
    """Valida un token contra la API de Telegram. Retorna info del bot o None."""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = urllib.request.urlopen(url, timeout=10)
        data = json.loads(response.read())
        if data.get("ok"):
            return data["result"]
    except Exception as e:
        logger.warning(f"Token inválido: {e}")
    return None


def add_token(bot_token: str, bot_username: str) -> dict:
    """Añade un nuevo token al pool. Retorna la entrada creada."""
    pool = _load_pool()

    # Generar ID único
    existing_ids = {t["id"] for t in pool["tokens"]}
    i = 1
    while f"bot{i}" in existing_ids:
        i += 1
    token_id = f"bot{i}"

    entry = {
        "id": token_id,
        "bot_token": bot_token,
        "bot_username": bot_username,
        "status": "available",
        "assigned_project": None,
        "assigned_role": None,
        "pid": None,
    }
    pool["tokens"].append(entry)
    _save_pool(pool)
    return entry


def remove_token(token_id: str) -> dict | None:
    """Elimina un token del pool. Solo si está disponible. Retorna la entrada o None."""
    pool = _load_pool()
    for i, token in enumerate(pool["tokens"]):
        if token["id"] == token_id:
            if token["status"] == "in_use":
                return None  # No se puede eliminar un token en uso
            removed = pool["tokens"].pop(i)
            _save_pool(pool)
            return removed
    return None


def find_token_by_username(username: str) -> dict | None:
    """Busca un token por el username del bot (case-insensitive, sin @)."""
    username = username.lstrip("@").lower()
    for token in list_tokens():
        if token.get("bot_username", "").lower() == username:
            return token
    return None

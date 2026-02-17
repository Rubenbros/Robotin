"""Registro y gestión de worker bots (spawn, kill, monitoreo)."""

import json
import logging
import os
import subprocess
import sys
import urllib.request
import urllib.parse
from datetime import datetime

from bot.config import WORKERS_STATE_FILE, BASE_DIR, AUTHORIZED_USER_ID
from bot.services import token_pool

logger = logging.getLogger(__name__)

_cache: dict | None = None


def _load_state() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    if WORKERS_STATE_FILE.exists():
        try:
            _cache = json.loads(WORKERS_STATE_FILE.read_text(encoding="utf-8"))
            return _cache
        except (json.JSONDecodeError, OSError):
            logger.warning("workers_state.json corrupto, reiniciando")
    _cache = {"workers": {}}
    return _cache


def _save_state(state: dict) -> None:
    global _cache
    _cache = state
    WORKERS_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def list_active_workers() -> list[dict]:
    """Retorna lista de workers activos."""
    state = _load_state()
    return list(state.get("workers", {}).values())


def get_worker(token_id: str) -> dict | None:
    """Obtiene info de un worker por token_id."""
    state = _load_state()
    return state.get("workers", {}).get(token_id)


def find_worker_by_name(name: str) -> dict | None:
    """Busca un worker por bot_username (case-insensitive, sin @)."""
    name = name.lstrip("@").lower()
    for w in list_active_workers():
        if w.get("bot_username", "").lower() == name:
            return w
    return None


def register_worker(token_id: str, bot_username: str, project_name: str,
                    project_path: str, role: str, pid: int) -> None:
    """Registra un worker activo."""
    state = _load_state()
    state["workers"][token_id] = {
        "token_id": token_id,
        "bot_username": bot_username,
        "project_name": project_name,
        "project_path": project_path,
        "role": role,
        "pid": pid,
        "started_at": datetime.now().isoformat(),
    }
    _save_state(state)


def unregister_worker(token_id: str) -> dict | None:
    """Elimina un worker del registro. Retorna su info o None."""
    state = _load_state()
    worker = state.get("workers", {}).pop(token_id, None)
    if worker:
        _save_state(state)
    return worker


def spawn_worker(token_id: str, bot_token: str, bot_username: str,
                 project_name: str, project_path: str, role: str) -> int:
    """Lanza un worker como subproceso. Retorna el PID."""
    python_exe = sys.executable

    cmd = [
        python_exe, "-m", "bot.worker_main",
        "--token", bot_token,
        "--token-id", token_id,
        "--bot-username", bot_username,
        "--project-name", project_name,
        "--project-path", project_path,
        "--role", role,
        "--authorized-user-id", str(AUTHORIZED_USER_ID),
    ]

    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

    process = subprocess.Popen(
        cmd,
        cwd=str(BASE_DIR),
        creationflags=creation_flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    pid = process.pid
    logger.info(f"Worker spawned: {bot_username} (PID {pid}) → {project_name} / {role}")
    return pid


def kill_worker(token_id: str) -> dict | None:
    """Mata un worker, libera su token, lo desregistra. Retorna su info o None."""
    worker = get_worker(token_id)
    if not worker:
        return None

    pid = worker.get("pid", 0)

    # Matar el proceso
    if pid > 0:
        try:
            if sys.platform == "win32":
                os.system(f"taskkill /PID {pid} /F >nul 2>&1")
            else:
                os.kill(pid, 15)  # SIGTERM
        except (ProcessLookupError, OSError):
            pass

    # Liberar token y desregistrar
    token_pool.release_token(token_id)
    unregister_worker(token_id)

    # Enviar notificación de apagado como fallback
    token_entry = token_pool.find_token_by_username(worker.get("bot_username", ""))
    # Usar el token del worker para enviar el mensaje de apagado
    _send_shutdown_fallback(worker)

    logger.info(f"Worker killed: {worker['bot_username']} (PID {pid})")
    return worker


def _send_shutdown_fallback(worker: dict) -> None:
    """Envía mensaje de apagado en nombre del worker (fallback si atexit no se ejecutó)."""
    # Buscar el token original para enviar el mensaje
    pool_tokens = token_pool.list_tokens()
    bot_token = None
    for t in pool_tokens:
        if t["id"] == worker["token_id"]:
            bot_token = t["bot_token"]
            break
    if not bot_token:
        return

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        label = f"@{worker['bot_username']} [{worker['project_name']} / {worker['role']}]"
        data = urllib.parse.urlencode({
            "chat_id": AUTHORIZED_USER_ID,
            "text": f"🔴 Worker apagado: {label}",
        }).encode()
        urllib.request.urlopen(url, data, timeout=5)
    except Exception:
        pass


def kill_all_workers() -> int:
    """Mata todos los workers activos. Retorna el número de workers matados."""
    workers = list_active_workers()
    count = 0
    for w in workers:
        kill_worker(w["token_id"])
        count += 1
    return count


def _is_pid_alive(pid: int) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def cleanup_dead_workers() -> list[str]:
    """Limpia workers muertos del registro y libera sus tokens. Retorna IDs limpiados."""
    state = _load_state()
    dead = []
    for token_id, worker in list(state.get("workers", {}).items()):
        if not _is_pid_alive(worker.get("pid", 0)):
            dead.append(token_id)
            token_pool.release_token(token_id)
            del state["workers"][token_id]
            logger.warning(f"Worker muerto limpiado: {worker.get('bot_username')} (PID {worker.get('pid')})")
    if dead:
        _save_state(state)
    return dead

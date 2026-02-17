"""Utilidades comunes para los handlers del bot."""

import asyncio
import logging

from telegram import Message

from bot.config import BASE_DIR
from bot.services import session_manager, project_manager
from bot.services.claude_service import run_claude
from bot.services.message_formatter import send_long_message

logger = logging.getLogger(__name__)


def resolve_context() -> dict:
    """Resuelve proyecto activo, cwd y session_key."""
    active = session_manager.get_active_project()

    if active == "__devbot__":
        return {"cwd": str(BASE_DIR), "session_key": "__devbot__", "active": active}
    elif active:
        proj = project_manager.find_project(active)
        if not proj:
            return {"cwd": None, "session_key": None, "active": active, "error": f"Proyecto `{active}` no encontrado."}
        return {"cwd": proj["path"], "session_key": active, "active": active}
    else:
        return {"cwd": None, "session_key": "__chat__", "active": None}


async def run_with_feedback(
    prompt: str,
    reply_to: Message,
    send_to,
    cwd: str | None,
    session_key: str,
    thinking_text: str = "Procesando...",
    response_header: str = "",
) -> None:
    """
    Ejecuta Claude con feedback visual: mensaje de progreso, notificaciones
    intermedias, cancelación, y envío de respuesta.

    Args:
        prompt: Texto a enviar a Claude.
        reply_to: Mensaje de Telegram al que responder con el thinking_msg.
        send_to: Update o Chat donde enviar la respuesta final.
        cwd: Directorio de trabajo.
        session_key: Clave de sesión para persistencia.
        thinking_text: Texto inicial del mensaje de progreso.
        response_header: Texto a prepender a la respuesta (ej: transcripción).
    """
    session_id = session_manager.get_session_id(session_key)
    thinking_msg = await reply_to.reply_text(thinking_text)

    async def _notify(msg: str):
        try:
            await thinking_msg.edit_text(msg)
        except Exception:
            pass

    try:
        result = await run_claude(
            prompt=prompt,
            cwd=cwd,
            session_id=session_id,
            on_notification=_notify,
        )
    except asyncio.CancelledError:
        try:
            await thinking_msg.edit_text("Ejecucion detenida.")
        except Exception:
            pass
        return

    try:
        await thinking_msg.delete()
    except Exception:
        pass

    if result.get("session_id") and result["session_id"] != session_id:
        session_manager.save_session_id(session_key, result["session_id"])

    response = result.get("response", "Sin respuesta.")
    await send_long_message(send_to, response_header + response)

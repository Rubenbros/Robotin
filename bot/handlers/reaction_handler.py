"""Handler de reacciones de Telegram. Corazon = 'si, adelante'."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.security import authorized_only
from bot.handlers.utils import resolve_context, run_with_feedback

logger = logging.getLogger(__name__)

CONFIRM_EMOJI = "\u2764"  # ❤


@authorized_only
async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reaction = update.message_reaction
    if not reaction:
        return

    # Solo reaccionar a corazon nuevo
    new_emojis = [
        r.emoji for r in (reaction.new_reaction or [])
        if hasattr(r, "emoji")
    ]
    if CONFIRM_EMOJI not in new_emojis:
        return

    ctx = resolve_context()
    if "error" in ctx:
        return

    chat = update.effective_chat

    # Enviar "si, adelante" como prompt usando mensaje dummy
    # No podemos hacer reply_to al mensaje original (la API no lo permite
    # desde message_reaction), asi que enviamos directo al chat
    thinking_msg = await chat.send_message("Procesando...")

    from bot.services import session_manager
    from bot.services.claude_service import run_claude
    from bot.services.message_formatter import send_long_message
    import asyncio

    session_id = session_manager.get_session_id(ctx["session_key"])

    async def _notify(msg: str):
        try:
            await thinking_msg.edit_text(msg)
        except Exception:
            pass

    try:
        result = await run_claude(
            prompt="sí, adelante",
            cwd=ctx["cwd"],
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
        session_manager.save_session_id(ctx["session_key"], result["session_id"])

    response = result.get("response", "Sin respuesta.")
    await send_long_message(chat, response)

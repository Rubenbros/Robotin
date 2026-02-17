import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import BASE_DIR
from bot.security import authorized_only
from bot.services import session_manager, project_manager
from bot.services.claude_service import run_claude
from bot.services.message_formatter import send_long_message

logger = logging.getLogger(__name__)


@authorized_only
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if not text or text.startswith("/"):
        return

    active = session_manager.get_active_project()

    # Determinar cwd y session según proyecto activo o chat libre
    if active == "__devbot__":
        cwd = str(BASE_DIR)
        session_key = "__devbot__"
    elif active:
        proj = project_manager.find_project(active)
        if not proj:
            await update.message.reply_text(f"Proyecto `{active}` no encontrado.", parse_mode="Markdown")
            return
        cwd = proj["path"]
        session_key = active
    else:
        cwd = None
        session_key = "__chat__"

    session_id = session_manager.get_session_id(session_key)

    thinking_msg = await update.message.reply_text("Procesando...")

    async def _notify(msg: str):
        try:
            await thinking_msg.edit_text(msg)
        except Exception:
            pass

    result = await run_claude(
        prompt=text,
        cwd=cwd,
        session_id=session_id,
        on_notification=_notify,
    )

    await thinking_msg.delete()

    if result.get("session_id") and result["session_id"] != session_id:
        session_manager.save_session_id(session_key, result["session_id"])

    response = result.get("response", "Sin respuesta.")
    await send_long_message(update, response)

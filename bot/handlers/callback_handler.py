import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.security import authorized_only
from bot.services import session_manager, project_manager
from bot.services.claude_service import run_claude
from bot.services.message_formatter import send_long_message

logger = logging.getLogger(__name__)


@authorized_only
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data:
        return

    # Selección de proyecto
    if data.startswith("select:"):
        project_name = data[len("select:"):]
        proj = project_manager.find_project(project_name)

        if not proj:
            await query.edit_message_text(f"Proyecto `{project_name}` no encontrado.", parse_mode="Markdown")
            return

        session_manager.set_active_project(proj["name"])
        session_id = session_manager.get_session_id(proj["name"])

        status = "sesion existente" if session_id else "nueva sesion"
        await query.edit_message_text(
            f"Proyecto activo: *{proj['name']}* [{proj['type']}]\n"
            f"`{proj['path']}`\n\n"
            f"Estado: {status}",
            parse_mode="Markdown",
        )
        return

    # Respuesta interactiva → enviar a Claude
    if data.startswith("reply:"):
        reply_text = data[len("reply:"):]

        # Marcar el botón pulsado en el mensaje original
        await query.edit_message_text(
            query.message.text + f"\n\n_Seleccionado: {reply_text}_",
            parse_mode="Markdown",
        )

        active = session_manager.get_active_project()
        if active:
            proj = project_manager.find_project(active)
            cwd = proj["path"] if proj else None
            session_key = active
        else:
            cwd = None
            session_key = "__chat__"

        session_id = session_manager.get_session_id(session_key)

        thinking_msg = await query.message.reply_text("Procesando...")

        result = await run_claude(
            prompt=reply_text,
            cwd=cwd,
            session_id=session_id,
        )

        await thinking_msg.delete()

        if result.get("session_id") and result["session_id"] != session_id:
            session_manager.save_session_id(session_key, result["session_id"])

        response = result.get("response", "Sin respuesta.")
        await send_long_message(query.message, response)

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.security import authorized_only
from bot.services import session_manager, project_manager
from bot.handlers.utils import resolve_context, run_with_feedback

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
        logger.info(f"Callback reply: {reply_text}")

        # Marcar el botón pulsado en el mensaje original
        try:
            await query.edit_message_text(
                query.message.text + f"\n\nSeleccionado: {reply_text}",
            )
        except Exception as e:
            logger.warning(f"No se pudo editar mensaje original: {e}")

        ctx = resolve_context()
        if "error" in ctx:
            await query.message.reply_text(ctx["error"], parse_mode="Markdown")
            return

        await run_with_feedback(
            prompt=reply_text,
            reply_to=query.message,
            send_to=query.message.chat,
            cwd=ctx["cwd"],
            session_key=ctx["session_key"],
        )

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import AUTHORIZED_USER_ID
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

    # --- Callbacks del coordinador ---

    if data.startswith("spawn_project:"):
        await _handle_spawn_project(query, context)
        return

    if data.startswith("kill_confirm:"):
        await _handle_kill_confirm(query)
        return

    if data == "kill_cancel":
        await query.edit_message_text("Cancelado.")
        return

    # --- Callbacks existentes ---

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


async def _handle_spawn_project(query, context) -> None:
    """Callback cuando el usuario selecciona un proyecto para spawn."""
    from bot.services import token_pool, worker_registry

    project_name = query.data[len("spawn_project:"):]
    role = context.user_data.pop("pending_spawn_role", "general")

    proj = project_manager.find_project(project_name)
    if not proj:
        await query.edit_message_text(f"Proyecto {project_name} no encontrado.")
        return

    # Adquirir token
    token_entry = token_pool.acquire_token(proj["name"], role, pid=0)
    if not token_entry:
        await query.edit_message_text(
            "No hay tokens disponibles.\n"
            "Crea un bot en @BotFather y usa /addtoken."
        )
        return

    # Spawn worker
    try:
        pid = worker_registry.spawn_worker(
            token_id=token_entry["id"],
            bot_token=token_entry["bot_token"],
            bot_username=token_entry["bot_username"],
            project_name=proj["name"],
            project_path=proj["path"],
            role=role,
        )
    except Exception as e:
        token_pool.release_token(token_entry["id"])
        await query.edit_message_text(f"Error al crear worker: {e}")
        return

    # Actualizar PID en el token y registrar worker
    token_pool.update_pid(token_entry["id"], pid)
    worker_registry.register_worker(
        token_id=token_entry["id"],
        bot_username=token_entry["bot_username"],
        project_name=proj["name"],
        project_path=proj["path"],
        role=role,
        pid=pid,
    )

    await query.edit_message_text(
        f"🟢 *Worker creado*\n\n"
        f"Bot: @{token_entry['bot_username']}\n"
        f"Proyecto: *{proj['name']}*\n"
        f"Rol: _{role}_\n"
        f"PID: {pid}\n\n"
        f"Abre el chat con @{token_entry['bot_username']} para empezar.",
        parse_mode="Markdown",
    )


async def _handle_kill_confirm(query) -> None:
    """Callback de confirmación para matar un worker."""
    from bot.services import worker_registry

    token_id = query.data[len("kill_confirm:"):]
    worker = worker_registry.get_worker(token_id)

    if not worker:
        await query.edit_message_text("Worker no encontrado (ya detenido?).")
        return

    worker_registry.kill_worker(token_id)
    await query.edit_message_text(
        f"🔴 Worker detenido: @{worker['bot_username']}\n"
        f"Proyecto: {worker['project_name']}, Rol: {worker['role']}"
    )

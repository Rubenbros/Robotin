import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from pathlib import Path

from bot.config import BASE_DIR, CLAUDE_PROJECTS_DIR
from bot.security import authorized_only
from bot.services import project_manager, session_manager
from bot.services.claude_service import run_claude, stop_claude, is_running
from bot.services.message_formatter import send_long_message

logger = logging.getLogger(__name__)

PROJECT_TYPE_ICONS = {
    "next.js": "Next.js",
    "node": "Node",
    "python": "Python",
    "unreal": "Unreal",
    "rust": "Rust",
    "go": "Go",
    "unknown": "",
}


@authorized_only
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "*Claude Code Bot*\n\n"
        "Bot privado para interactuar con Claude Code desde Telegram.\n\n"
        "*Comandos:*\n"
        "/projects - Ver proyectos disponibles\n"
        "/select `<nombre>` - Seleccionar proyecto\n"
        "/nochat - Volver a modo chat libre (sin proyecto)\n"
        "/newproject `<nombre>` - Crear proyecto nuevo\n"
        "/status - Estado de la sesion actual\n"
        "/clear - Limpiar sesion del proyecto activo\n"
        "/newchat - Nueva conversacion (alias de /clear)\n"
        "/stop - Detener ejecucion en curso\n"
        "/ask `<pregunta>` - Pregunta rapida sin cambiar de proyecto\n"
        "/devbot - Trabajar en el propio bot\n"
        "/gemini - Generar imagenes con Gemini\n"
        "/help - Mostrar ayuda\n\n"
        "Sin proyecto: funciona como chat normal con Claude.\n"
        "Con proyecto: Claude Code trabaja en el directorio del proyecto."
    )
    await send_long_message(update, text)


@authorized_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "*Ayuda*\n\n"
        "*Comandos:*\n"
        "`/start` - Bienvenida\n"
        "`/help` - Esta ayuda\n"
        "`/projects` - Lista de proyectos (botones)\n"
        "`/select <nombre>` - Seleccionar proyecto\n"
        "`/nochat` - Volver a chat libre (sin proyecto)\n"
        "`/newproject <nombre>` - Crear proyecto nuevo\n"
        "`/status` - Info del proyecto y sesion activa\n"
        "`/clear` - Limpiar sesion actual\n"
        "`/newchat` - Alias de /clear\n"
        "`/stop` - Detener ejecucion en curso\n"
        "`/ask <pregunta>` - Pregunta rapida sin cambiar de proyecto\n"
        "`/devbot` - Trabajar en el propio bot\n"
        "`/gemini [rapido|pro] [clean] <prompt>` - Generar imagen\n\n"
        "*Uso:*\n"
        "1. Selecciona un proyecto con /projects\n"
        "2. Envia texto para interactuar con Claude Code\n"
        "3. Envia una imagen para que Claude la analice\n"
        "4. Envia una nota de voz para transcribir y enviar\n"
    )
    await send_long_message(update, text)


@authorized_only
async def projects_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    projects = project_manager.list_projects()
    if not projects:
        await update.message.reply_text("No se encontraron proyectos.")
        return

    active = session_manager.get_active_project()
    buttons = []
    for proj in projects:
        label = proj["name"]
        ptype = PROJECT_TYPE_ICONS.get(proj["type"], "")
        if ptype:
            label = f"{label} [{ptype}]"
        if proj["name"] == active:
            label = f">> {label}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"select:{proj['name']}")])

    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("*Proyectos disponibles:*", reply_markup=keyboard, parse_mode="Markdown")


@authorized_only
async def select_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Uso: `/select <nombre_proyecto>`", parse_mode="Markdown")
        return

    name = " ".join(context.args)
    proj = project_manager.find_project(name)
    if not proj:
        await update.message.reply_text(f"Proyecto `{name}` no encontrado. Usa /projects para ver la lista.", parse_mode="Markdown")
        return

    session_manager.set_active_project(proj["name"])
    await update.message.reply_text(
        f"Proyecto activo: *{proj['name']}* [{proj['type']}]\n`{proj['path']}`",
        parse_mode="Markdown",
    )


@authorized_only
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    active = session_manager.get_active_project()
    session_key = active or "__chat__"
    session_id = session_manager.get_session_id(session_key)

    if active == "__devbot__":
        text = (
            f"*Estado actual*\n\n"
            f"*Modo:* Dev-bot (mejorando el propio bot)\n"
            f"*Ruta:* `{BASE_DIR}`\n"
            f"*Session ID:* `{session_id or 'ninguna'}`\n"
        )
    elif active:
        proj = project_manager.find_project(active)
        text = (
            f"*Estado actual*\n\n"
            f"*Proyecto:* {active}\n"
            f"*Tipo:* {proj['type'] if proj else 'desconocido'}\n"
            f"*Ruta:* `{proj['path'] if proj else 'N/A'}`\n"
            f"*Session ID:* `{session_id or 'ninguna'}`\n"
        )
    else:
        text = (
            f"*Estado actual*\n\n"
            f"*Modo:* Chat libre (sin proyecto)\n"
            f"*Session ID:* `{session_id or 'ninguna'}`\n"
            f"\nUsa /projects para seleccionar un proyecto."
        )
    await send_long_message(update, text)


@authorized_only
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    active = session_manager.get_active_project()
    session_key = active or "__chat__"

    session_manager.clear_session(session_key)
    label = f"*{active}*" if active else "chat libre"
    await update.message.reply_text(
        f"Sesion limpiada para {label}. El proximo mensaje creara una nueva conversacion.",
        parse_mode="Markdown",
    )


@authorized_only
async def nochat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session_manager.set_active_project(None)
    await update.message.reply_text("Modo chat libre activado. Sin proyecto activo.")


@authorized_only
async def newproject_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Uso: `/newproject <nombre>`", parse_mode="Markdown")
        return

    name = " ".join(context.args)

    if project_manager.find_project(name):
        await update.message.reply_text(f"El proyecto `{name}` ya existe.", parse_mode="Markdown")
        return

    project_path = CLAUDE_PROJECTS_DIR / name
    project_path.mkdir(parents=True, exist_ok=True)

    session_manager.set_active_project(name)
    await update.message.reply_text(
        f"Proyecto *{name}* creado y seleccionado.\n`{project_path}`",
        parse_mode="Markdown",
    )


@authorized_only
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    stopped = stop_claude()
    if not stopped:
        await update.message.reply_text("No hay nada en ejecucion.", parse_mode="Markdown")


@authorized_only
async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pregunta rápida a Claude sin cambiar el proyecto activo."""
    if not context.args:
        await update.message.reply_text("Uso: `/ask <pregunta>`", parse_mode="Markdown")
        return

    prompt = " ".join(context.args)

    thinking_msg = await update.message.reply_text("Procesando...")

    async def _notify(msg: str):
        try:
            await thinking_msg.edit_text(msg)
        except Exception:
            pass

    result = await run_claude(
        prompt=prompt,
        cwd=None,
        session_id=None,
        on_notification=_notify,
    )

    await thinking_msg.delete()

    response = result.get("response", "Sin respuesta.")
    await send_long_message(update, response)


@authorized_only
async def devbot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Selecciona el propio bot como proyecto activo para iterar sobre él."""
    session_manager.set_active_project("__devbot__")
    await update.message.reply_text(
        f"Modo dev-bot activado.\n`{BASE_DIR}`\n\nAhora puedes enviar mensajes para mejorar el bot.",
        parse_mode="Markdown",
    )

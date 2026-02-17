"""Comandos del bot coordinador: /spawn, /bots, /kill, /stopall, /addtoken, /removetoken."""

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.security import authorized_only
from bot.services import project_manager, token_pool, worker_registry

logger = logging.getLogger(__name__)


@authorized_only
async def spawn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Spawna un worker bot. Uso: /spawn [rol]"""
    if not context.args:
        role = "general"
    else:
        role = " ".join(context.args)

    # Verificar tokens disponibles
    available = token_pool.get_available_tokens()
    if not available:
        await update.message.reply_text(
            "No hay tokens disponibles en el pool.\n\n"
            "Crea un bot en @BotFather y añádelo con:\n"
            "`/addtoken TU_TOKEN`",
            parse_mode="Markdown",
        )
        return

    # Guardar rol pendiente
    context.user_data["pending_spawn_role"] = role

    # Mostrar proyectos como botones
    projects = project_manager.list_projects()
    if not projects:
        await update.message.reply_text("No hay proyectos disponibles.")
        return

    buttons = []
    for proj in projects:
        label = f"{proj['name']} [{proj['type']}]"
        buttons.append([InlineKeyboardButton(
            label, callback_data=f"spawn_project:{proj['name']}"
        )])

    await update.message.reply_text(
        f"*Spawn worker:* _{role}_\n\n"
        f"Selecciona el proyecto:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
    )


@authorized_only
async def bots_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista todos los worker bots activos."""
    # Limpiar muertos primero
    cleaned = worker_registry.cleanup_dead_workers()

    workers = worker_registry.list_active_workers()
    if not workers:
        await update.message.reply_text("No hay workers activos.")
        return

    lines = ["*Workers activos:*\n"]
    for w in workers:
        alive = worker_registry._is_pid_alive(w.get("pid", 0))
        icon = "🟢" if alive else "🔴"
        lines.append(
            f"{icon} *@{w['bot_username']}*\n"
            f"   Proyecto: {w['project_name']}\n"
            f"   Rol: {w['role']}\n"
            f"   PID: {w['pid']}"
        )

    # Mostrar tokens disponibles
    available = len(token_pool.get_available_tokens())
    total = len(token_pool.list_tokens())
    lines.append(f"\nTokens: {total - available}/{total} en uso")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


@authorized_only
async def kill_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mata un worker bot. Uso: /kill <nombre>"""
    if not context.args:
        # Mostrar workers como botones para elegir
        workers = worker_registry.list_active_workers()
        if not workers:
            await update.message.reply_text("No hay workers activos.")
            return

        buttons = []
        for w in workers:
            label = f"@{w['bot_username']} — {w['project_name']} / {w['role']}"
            buttons.append([InlineKeyboardButton(
                label, callback_data=f"kill_confirm:{w['token_id']}"
            )])
        buttons.append([InlineKeyboardButton("Cancelar", callback_data="kill_cancel")])

        await update.message.reply_text(
            "*Selecciona el worker a detener:*",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown",
        )
        return

    target = context.args[0].lstrip("@")
    worker = worker_registry.find_worker_by_name(target)
    if not worker:
        await update.message.reply_text(f"Worker `{target}` no encontrado.", parse_mode="Markdown")
        return

    # Confirmación
    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("Si, detener", callback_data=f"kill_confirm:{worker['token_id']}"),
        InlineKeyboardButton("Cancelar", callback_data="kill_cancel"),
    ]])
    await update.message.reply_text(
        f"Detener worker *@{worker['bot_username']}*?\n"
        f"Proyecto: {worker['project_name']}, Rol: {worker['role']}",
        reply_markup=buttons,
        parse_mode="Markdown",
    )


@authorized_only
async def stopall_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Detiene todos los worker bots activos."""
    workers = worker_registry.list_active_workers()
    if not workers:
        await update.message.reply_text("No hay workers activos.")
        return

    count = worker_registry.kill_all_workers()
    await update.message.reply_text(f"Detenidos {count} workers.")


@authorized_only
async def addtoken_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Añade un token al pool. Uso: /addtoken TOKEN"""
    if not context.args:
        await update.message.reply_text(
            "Uso: `/addtoken TU_BOT_TOKEN`\n\n"
            "Obtén el token creando un bot en @BotFather.",
            parse_mode="Markdown",
        )
        return

    bot_token = context.args[0]

    # Validar token contra la API de Telegram
    msg = await update.message.reply_text("Validando token...")

    bot_info = token_pool.validate_token(bot_token)
    if not bot_info:
        await msg.edit_text("Token inválido. Verifica que lo copiaste bien.")
        return

    username = bot_info.get("username", "unknown")

    # Comprobar que no esté ya en el pool
    existing = token_pool.find_token_by_username(username)
    if existing:
        await msg.edit_text(f"@{username} ya está en el pool (ID: {existing['id']}).")
        return

    entry = token_pool.add_token(bot_token, username)
    await msg.edit_text(
        f"Token añadido al pool:\n\n"
        f"Bot: *@{username}*\n"
        f"ID: `{entry['id']}`\n"
        f"Estado: disponible",
        parse_mode="Markdown",
    )


@authorized_only
async def removetoken_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Elimina un token del pool. Uso: /removetoken <id o username>"""
    if not context.args:
        tokens = token_pool.list_tokens()
        if not tokens:
            await update.message.reply_text("El pool está vacío.")
            return

        lines = ["*Tokens en el pool:*\n"]
        for t in tokens:
            icon = "🔒" if t["status"] == "in_use" else "✅"
            lines.append(f"{icon} `{t['id']}` — @{t['bot_username']} ({t['status']})")
        lines.append("\nUso: `/removetoken <id>`")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    target = context.args[0]

    # Buscar por ID o username
    token = None
    for t in token_pool.list_tokens():
        if t["id"] == target or t.get("bot_username", "").lower() == target.lstrip("@").lower():
            token = t
            break

    if not token:
        await update.message.reply_text(f"Token `{target}` no encontrado.", parse_mode="Markdown")
        return

    removed = token_pool.remove_token(token["id"])
    if not removed:
        await update.message.reply_text(
            f"No se puede eliminar @{token['bot_username']} porque está en uso.\n"
            f"Usa `/kill` primero.",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(f"Token @{removed['bot_username']} eliminado del pool.")

"""Comandos específicos para worker bots (subset simplificado)."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.security import authorized_only
from bot.services import session_manager
from bot.services.claude_service import stop_claude

logger = logging.getLogger(__name__)


@authorized_only
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    active = session_manager.get_active_project()
    session_id = session_manager.get_session_id(active) if active else None
    status = "sesion existente" if session_id else "nueva sesion"

    await update.message.reply_text(
        f"*Worker Bot*\n\n"
        f"Proyecto: *{active}*\n"
        f"Estado: {status}\n\n"
        f"Envíame texto, imágenes o notas de voz y trabajaré en ello.\n\n"
        f"*Comandos:*\n"
        f"/status — Ver estado\n"
        f"/clear — Nueva sesión\n"
        f"/stop — Detener ejecución actual",
        parse_mode="Markdown",
    )


@authorized_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "*Comandos del Worker:*\n\n"
        "/status — Estado del worker y sesión\n"
        "/clear — Limpiar sesión (empezar de cero)\n"
        "/newchat — Igual que /clear\n"
        "/stop — Detener la ejecución actual de Claude\n\n"
        "Envía texto, imágenes o audio para trabajar en el proyecto.",
        parse_mode="Markdown",
    )


@authorized_only
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    active = session_manager.get_active_project()
    if not active:
        await update.message.reply_text("Sin proyecto activo.")
        return

    info = session_manager.get_session_info(active)
    session_id = info.get("session_id")

    await update.message.reply_text(
        f"*Worker Status*\n\n"
        f"Proyecto: *{active}*\n"
        f"Sesion: `{session_id[:16]}...`" if session_id else f"Sesion: nueva",
        parse_mode="Markdown",
    )


@authorized_only
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    active = session_manager.get_active_project()
    if active:
        session_manager.clear_session(active)
        await update.message.reply_text(f"Sesion limpiada para *{active}*.", parse_mode="Markdown")
    else:
        await update.message.reply_text("Sin proyecto activo.")


@authorized_only
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    stopped = stop_claude()
    if not stopped:
        await update.message.reply_text("No hay nada en ejecucion.")

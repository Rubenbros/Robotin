import atexit
import logging
import os
import signal
import sys
import urllib.request
import urllib.parse

# Limpiar variable CLAUDECODE al inicio para que el SDK funcione
# aunque el bot se lance desde dentro de una sesión de Claude Code
os.environ.pop("CLAUDECODE", None)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from bot.config import TELEGRAM_BOT_TOKEN, AUTHORIZED_USER_ID
from bot.handlers.commands import (
    start_command,
    help_command,
    projects_command,
    select_command,
    status_command,
    clear_command,
    nochat_command,
    newproject_command,
    stop_command,
    ask_command,
    devbot_command,
)
from bot.handlers.coordinator_commands import (
    spawn_command,
    bots_command,
    kill_command,
    stopall_command,
    addtoken_command,
    removetoken_command,
)
from bot.handlers.text_handler import handle_text
from bot.handlers.image_handler import handle_image
from bot.handlers.voice_handler import handle_voice
from bot.handlers.callback_handler import handle_callback

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _on_startup(app) -> None:
    """Registra comandos en el menu de Telegram y notifica inicio."""
    from telegram import BotCommand

    commands = [
        BotCommand("projects", "Lista de proyectos"),
        BotCommand("select", "Seleccionar proyecto"),
        BotCommand("newproject", "Crear proyecto nuevo"),
        BotCommand("nochat", "Volver a chat libre"),
        BotCommand("status", "Info del proyecto y sesion"),
        BotCommand("clear", "Limpiar sesion actual"),
        BotCommand("stop", "Detener ejecucion en curso"),
        BotCommand("ask", "Pregunta rapida sin sesion"),
        BotCommand("devbot", "Trabajar en el propio bot"),
        BotCommand("gemini", "Generar imagen con Gemini"),
        BotCommand("spawn", "Crear worker bot"),
        BotCommand("bots", "Ver workers activos"),
        BotCommand("kill", "Detener un worker"),
        BotCommand("stopall", "Detener todos los workers"),
        BotCommand("addtoken", "Agregar token al pool"),
        BotCommand("removetoken", "Quitar token del pool"),
        BotCommand("help", "Ayuda"),
    ]
    try:
        await app.bot.set_my_commands(commands)
    except Exception as e:
        logger.warning(f"No se pudieron registrar comandos: {e}")

    try:
        await app.bot.send_message(chat_id=AUTHORIZED_USER_ID, text="🟢 Bot iniciado")
    except Exception as e:
        logger.warning(f"No se pudo enviar mensaje de inicio: {e}")


_shutdown_sent = False


def _send_shutdown_sync():
    """Envía mensaje de apagado usando HTTP directo (sin asyncio)."""
    global _shutdown_sent
    if _shutdown_sent or not TELEGRAM_BOT_TOKEN or not AUTHORIZED_USER_ID:
        return
    _shutdown_sent = True
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": AUTHORIZED_USER_ID,
            "text": "🔴 Bot apagado",
        }).encode()
        urllib.request.urlopen(url, data, timeout=5)
    except Exception as e:
        logger.warning(f"No se pudo enviar mensaje de apagado: {e}")


def _signal_handler(signum, frame):
    """Maneja SIGTERM/SIGINT para enviar mensaje antes de morir."""
    # Matar todos los workers antes de morir
    try:
        from bot.services.worker_registry import kill_all_workers
        kill_all_workers()
    except Exception:
        pass
    _send_shutdown_sync()
    sys.exit(0)


# Registrar atexit como respaldo
atexit.register(_send_shutdown_sync)


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN no configurado en .env")
        sys.exit(1)

    if not AUTHORIZED_USER_ID:
        logger.error("AUTHORIZED_USER_ID no configurado en .env")
        sys.exit(1)

    logger.info(f"Usuario autorizado: {AUTHORIZED_USER_ID}")

    # Limpiar workers/tokens huérfanos de ejecuciones anteriores
    try:
        from bot.services.token_pool import release_stale_tokens
        from bot.services.worker_registry import cleanup_dead_workers
        stale = release_stale_tokens()
        dead = cleanup_dead_workers()
        if stale:
            logger.info(f"Tokens huerfanos liberados: {stale}")
        if dead:
            logger.info(f"Workers muertos limpiados: {dead}")
    except Exception as e:
        logger.warning(f"Error limpiando estado previo: {e}")

    # Registrar signal handlers para apagado limpio
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(_on_startup)
        .build()
    )

    # Comandos existentes (chat libre, proyectos, etc.)
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("projects", projects_command))
    app.add_handler(CommandHandler("select", select_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("newchat", clear_command))
    app.add_handler(CommandHandler("nochat", nochat_command))
    app.add_handler(CommandHandler("newproject", newproject_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler("devbot", devbot_command))

    # Comandos del coordinador (multi-bot)
    app.add_handler(CommandHandler("spawn", spawn_command))
    app.add_handler(CommandHandler("bots", bots_command))
    app.add_handler(CommandHandler("kill", kill_command))
    app.add_handler(CommandHandler("stopall", stopall_command))
    app.add_handler(CommandHandler("addtoken", addtoken_command))
    app.add_handler(CommandHandler("removetoken", removetoken_command))

    # Callbacks (inline keyboard)
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Mensajes
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot iniciado. Polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

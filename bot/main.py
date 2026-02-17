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
    """Notifica al usuario que el bot se ha iniciado."""
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

    # Registrar signal handlers para apagado limpio
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(_on_startup)
        .build()
    )

    # Comandos
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

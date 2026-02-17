import logging
import sys

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


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN no configurado en .env")
        sys.exit(1)

    if not AUTHORIZED_USER_ID:
        logger.error("AUTHORIZED_USER_ID no configurado en .env")
        sys.exit(1)

    logger.info(f"Usuario autorizado: {AUTHORIZED_USER_ID}")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

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

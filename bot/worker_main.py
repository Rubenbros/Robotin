"""
Entry point para worker bots. Lanzado por el coordinador como subproceso.
Cada worker está dedicado a un proyecto + rol específico.

Uso: python -m bot.worker_main --token TOKEN --token-id ID --bot-username NAME
     --project-name NAME --project-path PATH --role ROLE --authorized-user-id UID
"""

import argparse
import atexit
import logging
import os
import signal
import sys
import urllib.request
import urllib.parse

# Limpiar CLAUDECODE antes de cualquier import
os.environ.pop("CLAUDECODE", None)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Worker bot de Claude Code")
    parser.add_argument("--token", required=True, help="Token del bot de Telegram")
    parser.add_argument("--token-id", required=True, help="ID del token en el pool")
    parser.add_argument("--bot-username", required=True, help="Username del bot")
    parser.add_argument("--project-name", required=True, help="Nombre del proyecto")
    parser.add_argument("--project-path", required=True, help="Ruta del proyecto")
    parser.add_argument("--role", required=True, help="Rol del worker")
    parser.add_argument("--authorized-user-id", type=int, required=True, help="User ID autorizado")
    return parser.parse_args()


def main():
    args = parse_args()

    # Override config para este worker
    import bot.config as config
    config.TELEGRAM_BOT_TOKEN = args.token
    config.AUTHORIZED_USER_ID = args.authorized_user_id

    # Session manager: archivo basado en proyecto+rol (persiste entre respawns)
    from bot.services import session_manager
    import re
    safe_name = re.sub(r'[^\w\-]', '_', f"{args.project_name}_{args.role}").lower()
    worker_state_file = config.SESSIONS_DIR / f"worker_{safe_name}.json"
    session_manager.STATE_FILE = worker_state_file
    session_manager._cache = None  # Forzar recarga

    # Setear proyecto activo (el worker es single-project)
    session_manager.set_active_project(args.project_name)

    # Inyectar rol en el system prompt de Claude
    from bot.services import claude_service
    role_prompt = (
        f"\n\n# Tu Rol\n"
        f"Eres un *{args.role}* trabajando en el proyecto *{args.project_name}*.\n"
        f"Directorio del proyecto: `{args.project_path}`\n"
        f"Enfocate exclusivamente en tu rol. No cambies de proyecto.\n"
    )
    claude_service._full_append_prompt = role_prompt + claude_service._full_append_prompt

    # Imports de handlers (usan config ya overrideado)
    from telegram.ext import (
        ApplicationBuilder,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        filters,
    )
    from bot.handlers.text_handler import handle_text
    from bot.handlers.image_handler import handle_image
    from bot.handlers.voice_handler import handle_voice
    from bot.handlers.callback_handler import handle_callback
    from bot.handlers.worker_commands import (
        start_command,
        help_command,
        status_command,
        clear_command,
        stop_command,
    )

    # Label para notificaciones
    bot_label = f"@{args.bot_username} [{args.project_name} / {args.role}]"

    # Startup notification
    async def _on_startup(app):
        try:
            await app.bot.send_message(
                chat_id=args.authorized_user_id,
                text=f"🟢 Worker iniciado: {bot_label}",
            )
        except Exception as e:
            logger.warning(f"No se pudo enviar mensaje de inicio: {e}")

    # Shutdown notification (síncrono, sin asyncio)
    _shutdown_sent = False

    def _send_shutdown():
        nonlocal _shutdown_sent
        if _shutdown_sent:
            return
        _shutdown_sent = True
        try:
            url = f"https://api.telegram.org/bot{args.token}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": args.authorized_user_id,
                "text": f"🔴 Worker apagado: {bot_label}",
            }).encode()
            urllib.request.urlopen(url, data, timeout=5)
        except Exception:
            pass

    atexit.register(_send_shutdown)
    signal.signal(signal.SIGTERM, lambda s, f: (_send_shutdown(), sys.exit(0)))
    signal.signal(signal.SIGINT, lambda s, f: (_send_shutdown(), sys.exit(0)))

    # Build the application
    app = (
        ApplicationBuilder()
        .token(args.token)
        .post_init(_on_startup)
        .build()
    )

    # Worker commands (subset del coordinador)
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("newchat", clear_command))
    app.add_handler(CommandHandler("stop", stop_command))

    # Callbacks (botones inline)
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Mensajes
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info(f"Worker iniciado: {bot_label} (PID {os.getpid()})")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

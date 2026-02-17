import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import BASE_DIR, TEMP_DIR
from bot.security import authorized_only
from bot.services import session_manager, project_manager
from bot.services.claude_service import run_claude
from bot.services.message_formatter import send_long_message

logger = logging.getLogger(__name__)


@authorized_only
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    active = session_manager.get_active_project()

    if active == "__devbot__":
        cwd = str(BASE_DIR)
        session_key = "__devbot__"
        images_dir = BASE_DIR / ".claude-bot-images"
    elif active:
        proj = project_manager.find_project(active)
        if not proj:
            await update.message.reply_text(f"Proyecto `{active}` no encontrado.", parse_mode="Markdown")
            return
        cwd = proj["path"]
        session_key = active
        images_dir = Path(cwd) / ".claude-bot-images"
    else:
        cwd = None
        session_key = "__chat__"
        images_dir = TEMP_DIR

    images_dir.mkdir(parents=True, exist_ok=True)

    # Descargar imagen
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_path = images_dir / f"{file.file_unique_id}.jpg"
    await file.download_to_drive(str(image_path))
    logger.info(f"Imagen guardada: {image_path}")

    caption = update.message.caption or "Analiza esta imagen"
    prompt = f"{caption}\n\n[La imagen está en: {image_path.resolve()}]"

    session_id = session_manager.get_session_id(session_key)

    thinking_msg = await update.message.reply_text("Procesando imagen...")

    async def _notify(msg: str):
        try:
            await thinking_msg.edit_text(msg)
        except Exception:
            pass

    result = await run_claude(
        prompt=prompt,
        cwd=cwd,
        session_id=session_id,
        on_notification=_notify,
    )

    await thinking_msg.delete()

    if result.get("session_id") and result["session_id"] != session_id:
        session_manager.save_session_id(session_key, result["session_id"])

    response = result.get("response", "Sin respuesta.")
    await send_long_message(update, response)

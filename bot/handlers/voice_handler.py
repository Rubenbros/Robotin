import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import TEMP_DIR
from bot.security import authorized_only
from bot.services import session_manager, project_manager
from bot.services.claude_service import run_claude
from bot.services.whisper_service import transcribe
from bot.services.message_formatter import send_long_message

logger = logging.getLogger(__name__)


@authorized_only
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    active = session_manager.get_active_project()

    if active:
        proj = project_manager.find_project(active)
        if not proj:
            await update.message.reply_text(f"Proyecto `{active}` no encontrado.", parse_mode="Markdown")
            return
        cwd = proj["path"]
        session_key = active
    else:
        cwd = None
        session_key = "__chat__"

    # Descargar audio
    voice = update.message.voice or update.message.audio
    if not voice:
        return

    file = await voice.get_file()
    audio_path = TEMP_DIR / f"{file.file_unique_id}.ogg"
    await file.download_to_drive(str(audio_path))
    logger.info(f"Audio descargado: {audio_path}")

    transcribing_msg = await update.message.reply_text("Transcribiendo audio...")

    try:
        text = transcribe(str(audio_path))
    except Exception as e:
        logger.error(f"Error transcribiendo: {e}")
        await transcribing_msg.edit_text(f"Error al transcribir audio: {e}")
        return
    finally:
        audio_path.unlink(missing_ok=True)

    if not text.strip():
        await transcribing_msg.edit_text("No se pudo transcribir el audio (vacío).")
        return

    await transcribing_msg.edit_text(f"Transcripcion: _{text}_\n\nProcesando...", parse_mode="Markdown")

    session_id = session_manager.get_session_id(session_key)

    result = await run_claude(
        prompt=text,
        cwd=cwd,
        session_id=session_id,
    )

    await transcribing_msg.delete()

    if result.get("session_id") and result["session_id"] != session_id:
        session_manager.save_session_id(session_key, result["session_id"])

    # Mostrar transcripción + respuesta
    header = f"*Transcripcion:* _{text}_\n\n"
    response = result.get("response", "Sin respuesta.")
    await send_long_message(update, header + response)

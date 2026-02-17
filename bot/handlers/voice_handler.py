import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import TEMP_DIR
from bot.security import authorized_only
from bot.services.whisper_service import transcribe
from bot.handlers.utils import resolve_context, run_with_feedback

logger = logging.getLogger(__name__)


@authorized_only
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ctx = resolve_context()
    if "error" in ctx:
        await update.message.reply_text(ctx["error"], parse_mode="Markdown")
        return

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

    try:
        await transcribing_msg.delete()
    except Exception:
        pass

    header = f"*Transcripcion:* _{text}_\n\n"

    await run_with_feedback(
        prompt=text,
        reply_to=update.message,
        send_to=update,
        cwd=ctx["cwd"],
        session_key=ctx["session_key"],
        thinking_text=f"Transcripcion: _{text}_\n\nProcesando...",
        response_header=header,
    )

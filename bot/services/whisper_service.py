import logging
from pathlib import Path

from bot.config import WHISPER_MODEL, WHISPER_LANGUAGE

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        logger.info(f"Cargando modelo Whisper '{WHISPER_MODEL}'...")
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        logger.info("Modelo Whisper cargado")
    return _model


def transcribe(audio_path: str | Path) -> str:
    """Transcribe un archivo de audio y retorna el texto."""
    model = _get_model()
    segments, info = model.transcribe(
        str(audio_path),
        language=WHISPER_LANGUAGE,
        vad_filter=True,
    )
    text = " ".join(segment.text.strip() for segment in segments)
    logger.info(f"Transcrito ({info.language}, {info.duration:.1f}s): {text[:100]}...")
    return text

import asyncio
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import TEMP_DIR
from bot.security import authorized_only
from bot.handlers.utils import resolve_context, run_with_feedback

logger = logging.getLogger(__name__)

# Buffer para agrupar imágenes de un mismo álbum (media_group)
_media_groups: dict[str, dict] = {}
_media_group_locks: dict[str, asyncio.Lock] = {}


@authorized_only
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    media_group_id = update.message.media_group_id

    # Imagen suelta (sin álbum) — procesar directamente
    if not media_group_id:
        await _process_images(update, context, [update.message])
        return

    # Imagen parte de un álbum — agrupar y esperar
    if media_group_id not in _media_group_locks:
        _media_group_locks[media_group_id] = asyncio.Lock()

    async with _media_group_locks[media_group_id]:
        if media_group_id not in _media_groups:
            _media_groups[media_group_id] = {
                "messages": [],
                "first_update": update,
                "scheduled": False,
            }

        _media_groups[media_group_id]["messages"].append(update.message)

        if not _media_groups[media_group_id]["scheduled"]:
            _media_groups[media_group_id]["scheduled"] = True
            asyncio.create_task(_process_media_group(media_group_id, update, context))


async def _process_media_group(
    media_group_id: str, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Espera a que lleguen todas las imágenes del álbum y las procesa juntas."""
    await asyncio.sleep(1.0)

    group_data = _media_groups.pop(media_group_id, None)
    _media_group_locks.pop(media_group_id, None)

    if not group_data:
        return

    await _process_images(update, context, group_data["messages"])


async def _process_images(
    update: Update, context: ContextTypes.DEFAULT_TYPE, messages: list
) -> None:
    """Descarga y procesa una o varias imágenes en una sola llamada a Claude."""
    ctx = resolve_context()
    if "error" in ctx:
        await update.message.reply_text(ctx["error"], parse_mode="Markdown")
        return

    if ctx["cwd"]:
        images_dir = Path(ctx["cwd"]) / ".claude-bot-images"
    else:
        images_dir = TEMP_DIR

    images_dir.mkdir(parents=True, exist_ok=True)

    # Descargar todas las imágenes
    image_paths = []
    caption = None
    for msg in messages:
        if not msg.photo:
            continue
        photo = msg.photo[-1]
        file = await photo.get_file()
        image_path = images_dir / f"{file.file_unique_id}.jpg"
        await file.download_to_drive(str(image_path))
        image_paths.append(image_path)
        logger.info(f"Imagen guardada: {image_path}")
        if not caption and msg.caption:
            caption = msg.caption

    if not image_paths:
        return

    caption = caption or ("Analiza esta imagen" if len(image_paths) == 1 else "Analiza estas imagenes")

    # Construir prompt con todas las rutas
    paths_text = "\n".join(f"- {p.resolve()}" for p in image_paths)
    if len(image_paths) == 1:
        prompt = f"{caption}\n\n[La imagen está en: {image_paths[0].resolve()}]"
    else:
        prompt = f"{caption}\n\n[Las {len(image_paths)} imágenes están en:\n{paths_text}]"

    n = len(image_paths)
    thinking_text = f"Procesando {n} imagenes..." if n > 1 else "Procesando imagen..."

    await run_with_feedback(
        prompt=prompt,
        reply_to=update.message,
        send_to=update,
        cwd=ctx["cwd"],
        session_key=ctx["session_key"],
        thinking_text=thinking_text,
    )

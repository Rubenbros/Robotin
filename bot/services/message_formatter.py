import logging
import re
from pathlib import Path

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    ForceReply,
)

from bot.config import TELEGRAM_MAX_MESSAGE_LENGTH

logger = logging.getLogger(__name__)


def split_message(text: str, max_length: int = TELEGRAM_MAX_MESSAGE_LENGTH) -> list[str]:
    """Divide un mensaje largo en partes respetando code blocks y párrafos."""
    if len(text) <= max_length:
        return [text]

    parts = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            parts.append(remaining)
            break

        chunk = remaining[:max_length]

        open_blocks = chunk.count("```")
        inside_code_block = open_blocks % 2 == 1

        cut_point = _find_cut_point(chunk, inside_code_block)
        part = remaining[:cut_point]

        if inside_code_block:
            last_open = part.rfind("```")
            lang_match = re.match(r"```(\w*)\n?", part[last_open:])
            lang = lang_match.group(1) if lang_match else ""
            part += "\n```"
            remaining = f"```{lang}\n" + remaining[cut_point:]
        else:
            remaining = remaining[cut_point:]

        parts.append(part.strip())

    return [p for p in parts if p]


def _find_cut_point(chunk: str, inside_code_block: bool) -> int:
    max_len = len(chunk)

    if inside_code_block:
        nl = chunk.rfind("\n")
        if nl > max_len // 2:
            return nl
        return max_len

    double_nl = chunk.rfind("\n\n")
    if double_nl > max_len // 2:
        return double_nl

    nl = chunk.rfind("\n")
    if nl > max_len // 2:
        return nl

    space = chunk.rfind(" ")
    if space > max_len // 2:
        return space

    return max_len


# --- Detección de imágenes ---

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

_PATH_PATTERN = re.compile(
    r'(?:[A-Za-z]:\\[^\s*`"<>|]+|/[^\s*`"<>|]+)\.(?:png|jpg|jpeg|gif|webp|bmp)',
    re.IGNORECASE,
)


def extract_image_paths(text: str) -> list[Path]:
    paths = []
    for match in _PATH_PATTERN.findall(text):
        p = Path(match.strip("`,.'\""))
        if p.exists() and p.suffix.lower() in IMAGE_EXTENSIONS:
            paths.append(p)
    return list(dict.fromkeys(paths))


# --- Detección de elementos interactivos ---

# [BUTTONS: opción 1 | opción 2 | opción 3]  → botones inline, 1 por fila
_BUTTONS_PATTERN = re.compile(r'\[BUTTONS:\s*(.+?)\]', re.DOTALL)

# [GRID: op1 | op2 | op3 | op4]  → botones inline en grid de 2 columnas
_GRID_PATTERN = re.compile(r'\[GRID:\s*(.+?)\]', re.DOTALL)

# [CONFIRM: texto de la acción]  → Sí / No
_CONFIRM_PATTERN = re.compile(r'\[CONFIRM:\s*(.+?)\]', re.DOTALL)

# [QUICK: op1 | op2 | op3]  → reply keyboard (botones grandes abajo)
_QUICK_PATTERN = re.compile(r'\[QUICK:\s*(.+?)\]', re.DOTALL)

# [POLL: pregunta | op1 | op2 | op3]  → encuesta de Telegram
_POLL_PATTERN = re.compile(r'\[POLL:\s*(.+?)\]', re.DOTALL)

# [FORCE_REPLY]  → forzar respuesta del usuario
_FORCE_REPLY_PATTERN = re.compile(r'\[FORCE_REPLY(?::\s*(.+?))?\]', re.DOTALL)


class InteractiveElements:
    """Contenedor para los elementos interactivos extraídos."""
    def __init__(self):
        self.inline_keyboard: list[list[InlineKeyboardButton]] = []
        self.reply_keyboard: list[list[KeyboardButton]] | None = None
        self.reply_keyboard_one_time: bool = True
        self.polls: list[dict] = []
        self.force_reply: bool = False
        self.force_reply_placeholder: str = ""

    @property
    def reply_markup(self):
        if self.force_reply:
            return ForceReply(
                selective=True,
                input_field_placeholder=self.force_reply_placeholder or "Escribe tu respuesta..."
            )
        if self.reply_keyboard:
            return ReplyKeyboardMarkup(
                self.reply_keyboard,
                resize_keyboard=True,
                one_time_keyboard=self.reply_keyboard_one_time,
            )
        if self.inline_keyboard:
            return InlineKeyboardMarkup(self.inline_keyboard)
        return None


def extract_interactive(text: str) -> tuple[str, InteractiveElements]:
    """Extrae todos los marcadores interactivos del texto."""
    elements = InteractiveElements()

    # GRID (2 columnas)
    for match in _GRID_PATTERN.finditer(text):
        options = [o.strip() for o in match.group(1).split("|") if o.strip()]
        row = []
        for opt in options:
            row.append(InlineKeyboardButton(opt, callback_data=f"reply:{opt[:60]}"))
            if len(row) == 2:
                elements.inline_keyboard.append(row)
                row = []
        if row:
            elements.inline_keyboard.append(row)
    text = _GRID_PATTERN.sub("", text)

    # BUTTONS (1 por fila)
    for match in _BUTTONS_PATTERN.finditer(text):
        options = [o.strip() for o in match.group(1).split("|") if o.strip()]
        for opt in options:
            elements.inline_keyboard.append(
                [InlineKeyboardButton(opt, callback_data=f"reply:{opt[:60]}")]
            )
    text = _BUTTONS_PATTERN.sub("", text)

    # CONFIRM (Sí / No)
    for match in _CONFIRM_PATTERN.finditer(text):
        action = match.group(1).strip()
        elements.inline_keyboard.append([
            InlineKeyboardButton("Si", callback_data=f"reply:Si, {action[:50]}"),
            InlineKeyboardButton("No", callback_data="reply:No, cancelar"),
        ])
    text = _CONFIRM_PATTERN.sub("", text)

    # QUICK (reply keyboard)
    for match in _QUICK_PATTERN.finditer(text):
        options = [o.strip() for o in match.group(1).split("|") if o.strip()]
        elements.reply_keyboard = []
        row = []
        for opt in options:
            row.append(KeyboardButton(opt))
            if len(row) == 2:
                elements.reply_keyboard.append(row)
                row = []
        if row:
            elements.reply_keyboard.append(row)
    text = _QUICK_PATTERN.sub("", text)

    # POLL
    for match in _POLL_PATTERN.finditer(text):
        parts = [p.strip() for p in match.group(1).split("|") if p.strip()]
        if len(parts) >= 3:
            elements.polls.append({
                "question": parts[0],
                "options": parts[1:],
            })
    text = _POLL_PATTERN.sub("", text)

    # FORCE_REPLY
    for match in _FORCE_REPLY_PATTERN.finditer(text):
        elements.force_reply = True
        if match.group(1):
            elements.force_reply_placeholder = match.group(1).strip()
    text = _FORCE_REPLY_PATTERN.sub("", text)

    return text.strip(), elements


# --- Envío de mensajes ---

async def send_long_message(update_or_chat, text: str, parse_mode: str | None = "Markdown") -> None:
    """Envía un mensaje con soporte para imágenes y elementos interactivos."""
    from telegram import Update

    images = extract_image_paths(text)
    text, elements = extract_interactive(text)

    parts = split_message(text) if text else []
    reply_markup = elements.reply_markup

    for i, part in enumerate(parts):
        is_last = (i == len(parts) - 1)
        markup = reply_markup if is_last else None

        try:
            if isinstance(update_or_chat, Update):
                await update_or_chat.message.reply_text(
                    part, parse_mode=parse_mode, reply_markup=markup
                )
            else:
                await update_or_chat.send_message(
                    part, parse_mode=parse_mode, reply_markup=markup
                )
        except Exception:
            try:
                if isinstance(update_or_chat, Update):
                    await update_or_chat.message.reply_text(
                        part, parse_mode=None, reply_markup=markup
                    )
                else:
                    await update_or_chat.send_message(
                        part, parse_mode=None, reply_markup=markup
                    )
            except Exception as e:
                logger.error(f"Error enviando mensaje: {e}")

    # Enviar imágenes como fotos
    for img_path in images:
        try:
            with open(img_path, "rb") as f:
                if isinstance(update_or_chat, Update):
                    await update_or_chat.message.reply_photo(photo=f, caption=img_path.name)
                else:
                    await update_or_chat.send_photo(photo=f, caption=img_path.name)
        except Exception as e:
            logger.error(f"Error enviando imagen {img_path}: {e}")

    # Enviar polls
    for poll in elements.polls:
        try:
            if isinstance(update_or_chat, Update):
                await update_or_chat.message.reply_poll(
                    question=poll["question"],
                    options=poll["options"],
                    is_anonymous=False,
                )
            else:
                await update_or_chat.send_poll(
                    question=poll["question"],
                    options=poll["options"],
                    is_anonymous=False,
                )
        except Exception as e:
            logger.error(f"Error enviando poll: {e}")

import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import CLAUDE_SKILLS_DIR
from bot.security import authorized_only
from bot.services import session_manager
from bot.services.claude_service import run_claude
from bot.services.message_formatter import send_long_message

logger = logging.getLogger(__name__)

SKILL_PATH = CLAUDE_SKILLS_DIR / "gemini-image" / "SKILL.md"
_skill_instructions = None


def _load_skill() -> str:
    global _skill_instructions
    if _skill_instructions is None:
        if SKILL_PATH.exists():
            raw = SKILL_PATH.read_text(encoding="utf-8")
            # Quitar frontmatter YAML
            if raw.startswith("---"):
                end = raw.find("---", 3)
                if end != -1:
                    raw = raw[end + 3:].strip()
            _skill_instructions = raw
        else:
            _skill_instructions = ""
    return _skill_instructions


@authorized_only
async def gemini_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "*Uso:* `/gemini [rapido|pro] [clean] <prompt>`\n\n"
            "Ejemplos:\n"
            "`/gemini Un gato astronauta`\n"
            "`/gemini pro Logo minimalista para NovaTech`\n"
            "`/gemini pro clean Un dragon medieval`",
            parse_mode="Markdown",
        )
        return

    skill = _load_skill()
    if not skill:
        await update.message.reply_text("Skill gemini-image no encontrada.")
        return

    user_args = " ".join(context.args)

    prompt = (
        f"Ejecuta las siguientes instrucciones para generar una imagen con Gemini.\n\n"
        f"Argumentos del usuario: {user_args}\n\n"
        f"--- INSTRUCCIONES DE LA SKILL ---\n\n"
        f"{skill}"
    )

    thinking_msg = await update.message.reply_text("Generando imagen con Gemini...")

    # Usar chat libre para no contaminar sesiones de proyecto
    session_id = session_manager.get_session_id("__gemini__")

    result = await run_claude(
        prompt=prompt,
        cwd=None,
        session_id=session_id,
    )

    await thinking_msg.delete()

    if result.get("session_id") and result["session_id"] != session_id:
        session_manager.save_session_id("__gemini__", result["session_id"])

    response = result.get("response", "Sin respuesta.")
    await send_long_message(update, response)

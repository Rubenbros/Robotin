import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.security import authorized_only
from bot.handlers.utils import resolve_context, run_with_feedback

logger = logging.getLogger(__name__)


@authorized_only
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if not text or text.startswith("/"):
        return

    ctx = resolve_context()
    if "error" in ctx:
        await update.message.reply_text(ctx["error"], parse_mode="Markdown")
        return

    await run_with_feedback(
        prompt=text,
        reply_to=update.message,
        send_to=update,
        cwd=ctx["cwd"],
        session_key=ctx["session_key"],
    )

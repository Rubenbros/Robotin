import functools
import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import AUTHORIZED_USER_ID

logger = logging.getLogger(__name__)


def authorized_only(func):
    """Decorador que solo permite la ejecución si el user_id coincide con AUTHORIZED_USER_ID."""

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else None
        if user_id != AUTHORIZED_USER_ID:
            logger.warning(f"Acceso denegado para user_id={user_id}")
            return  # Silencio total para usuarios no autorizados
        return await func(update, context, *args, **kwargs)

    return wrapper

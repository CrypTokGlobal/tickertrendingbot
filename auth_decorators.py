
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from owner_manager import is_authorized, get_owner_id, add_admin

# 🔐 Restrict to Owner + Additional Admins
def owner_only(func):
    """Restricts a command to the owner or whitelisted users"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not is_authorized(user.id, user.username):
            await update.message.reply_text("⛔ You are not authorized to use this command.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# 🔐 Strictly Owner-Only
def strictly_owner(func):
    """Restricts a command to only the registered bot owner"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id != get_owner_id():
            await update.message.reply_text("⛔ Only the bot owner can use this.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

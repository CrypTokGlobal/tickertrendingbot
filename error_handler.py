
import logging
import traceback
from telegram.ext import ContextTypes
from telegram.error import BadRequest, TimedOut, Forbidden

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import admin chat ID from config
try:
    from config import ADMIN_CHAT_ID
except ImportError:
    logger.warning("Could not import ADMIN_CHAT_ID from config")
    ADMIN_CHAT_ID = None

async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler for the bot."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

    if isinstance(context.error, Forbidden):
        logger.error(f"Bot doesn't have permission for this action: {context.error}")

    elif isinstance(context.error, BadRequest):
        logger.error(f"Bad request: {context.error}")

    elif isinstance(context.error, TimedOut):
        logger.error(f"Request timed out: {context.error}")

    else:
        # Log full traceback for unhandled errors
        logger.error(f"Unhandled error: {context.error}\n{traceback.format_exc()}")

        # Notify admin if configured
        if ADMIN_CHAT_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"⚠️ Unhandled Error:\n{context.error}",
                )
            except Exception as notify_error:
                logger.error(f"Error sending error alert to admin: {notify_error}")

def register_error_handler(application):
    """Register the error handler with the application"""
    application.add_error_handler(error_handler)
    logger.info("Error handler registered")
    return application

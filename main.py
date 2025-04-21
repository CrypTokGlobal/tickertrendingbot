import asyncio
import logging
import os
import nest_asyncio
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram import Update
from telegram.ext import ContextTypes
from config import TELEGRAM_BOT_TOKEN
from eth_monitor import get_instance as get_eth_monitor, start_monitoring as start_eth_monitor
from solana_monitor import SolanaMonitor

# Patch Replit loop issues
nest_asyncio.apply()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Globals
sol_monitor = None

async def test_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE, force_eth=False):
    """Generate example alerts for tracked tokens to test notifications"""
    chat_id = update.effective_chat.id

    # Import here to avoid circular imports
    from utils import handle_example_alert
    await handle_example_alert(update, context)

    # If force_eth is True, also send a specific ETH test alert
    if force_eth:
        from eth_monitor import test_eth_alert
        await update.message.reply_text("🧪 Sending Ethereum test alert...")
        await test_eth_alert(chat_id)

async def register_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register a chat for alerts"""
    chat_id = update.effective_chat.id

    # Add to active chats
    try:
        from data_manager import register_chat
        success = register_chat(chat_id)
        if success:
            await update.message.reply_text("✅ This chat has been registered for alerts!")
        else:
            await update.message.reply_text("ℹ️ This chat was already registered.")
    except Exception as e:
        logger.error(f"Error registering chat: {e}")
        await update.message.reply_text("❌ Error registering chat. Please try again later.")

async def register_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register a chat for alerts"""
    chat_id = update.effective_chat.id

    # Add to active chats
    try:
        from data_manager import register_chat
        success = register_chat(chat_id)
        if success:
            await update.message.reply_text("✅ This chat has been registered for alerts!")
        else:
            await update.message.reply_text("ℹ️ This chat was already registered.")
    except Exception as e:
        logger.error(f"Error registering chat: {e}")
        await update.message.reply_text("❌ Error registering chat. Please try again later.")

async def main():
    global sol_monitor

    logger.info("🔧 Building bot application...")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register error handler
    from error_handler import register_error_handler
    register_error_handler(application)

    # === Register Commands ===
    from track_handler import get_track_handlers
    from conversation_handler import handle_track_command

    # Register track handlers
    for handler in get_track_handlers():
        application.add_handler(handler)

    application.add_handler(CommandHandler("track", handle_track_command))

    # === Test and Register Commands ===
    application.add_handler(CommandHandler("test_alert", test_alert_command))
    application.add_handler(CommandHandler("test_eth", lambda u, c: test_alert_command(u, c, force_eth=True)))
    application.add_handler(CommandHandler("register_chat", register_chat_command))

    from utils import handle_status_command, handle_example_alert
    application.add_handler(CommandHandler("status", handle_status_command))
    application.add_handler(CommandHandler("example_alert", handle_example_alert))

    # Import all UI handlers
    from boost_handler import register_boost_handlers
    from boost_menu import get_boost_handlers
    from callback_manager import register_all_callbacks
    from button_handler import register_button_handlers
    from help_handler import get_help_handlers

    # Register start command with premium UI
    logger.info("🚀 Registering premium start UI handlers...")
    from start_handler import get_start_handlers
    for handler in get_start_handlers():
        application.add_handler(handler)
    
    # Register help command handlers with interactive UI
    logger.info("🎮 Registering help UI handlers...")
    for handler in get_help_handlers():
        application.add_handler(handler)

    # Register boost menu with rich UI
    try:
        logger.info("🚀 Loading boost menu handlers...")
        from boost_menu import get_boost_handlers
        for handler in get_boost_handlers():
            application.add_handler(handler)

        # Register boost token command handlers
        from boost_handler import register_boost_handlers
        register_boost_handlers(application)
        logger.info("✅ Boost system fully registered")
    except Exception as e:
        logger.error(f"Error loading boost handlers: {e}")

    # Register all callback and button handlers
    logger.info("🔄 Registering callback handlers...")
    from callback_manager import register_all_callbacks
    from help_handler import get_help_callback_handlers

    # First register all specialized callbacks
    for handler in get_help_callback_handlers():
        application.add_handler(handler)

    # Then register the main callback system
    register_all_callbacks(application)

    try:
        logger.info("👆 Registering button interaction handlers...")
        register_button_handlers(application)
    except Exception as e:
        logger.warning(f"Button handlers registration issue (non-critical): {e}")
        logger.info("Attempting to recover button functionality...")
        from button_handler import get_button_handlers
        for handler in get_button_handlers():
            try:
                application.add_handler(handler)
            except Exception as inner_e:
                logger.error(f"Failed to register button handler: {inner_e}")

    from data_debug import get_data_debug_handlers
    for handler in get_data_debug_handlers():
        application.add_handler(handler)

    from quick_track import register_handlers as register_eth_handlers
    from quick_track_sol import register_handlers as register_sol_handlers
    register_eth_handlers(application)
    register_sol_handlers(application)

    # === Monitoring ===
    try:
        logger.info("🔄 Starting Ethereum monitoring...")
        eth_task = asyncio.create_task(start_eth_monitor(application.bot))
        eth_mon = get_eth_monitor(application.bot)
        logger.info(f"✅ ETH monitor started, tracking {len(eth_mon.tracked_contracts)} tokens")
    except Exception as e:
        logger.error(f"❌ ETH monitor failed: {e}", exc_info=True)

    try:
        logger.info("🔄 Starting Solana monitoring...")
        sol_monitor = SolanaMonitor(application.bot)
        asyncio.create_task(sol_monitor.start())
    except Exception as e:
        logger.warning(f"⚠️ Solana monitor issue: {e}")

    # === Dashboard ===
    try:
        from dashboard import start_dashboard_server
        dashboard_thread = start_dashboard_server(port=8080)
        logger.info("📊 Dashboard server launched on port 8080")
        logger.info(f"📊 Dashboard URL: https://{os.environ.get('REPL_SLUG', 'ticker-trending-bot')}.{os.environ.get('REPL_OWNER', 'arasbaker99')}.repl.co/status")
    except Exception as e:
        logger.error(f"❌ Dashboard failed to start: {e}", exc_info=True)

    logger.info("🧹 Deleting any existing webhook...")
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook deleted successfully")
    except Exception as e:
        logger.error(f"❌ Error deleting webhook: {e}")
        if "Not Found" in str(e) or "Unauthorized" in str(e) or "InvalidToken" in str(e):
            logger.error("⚠️ The bot token appears to be invalid. Please check your TELEGRAM_BOT_TOKEN value.")
            logger.error("🔄 Try restarting the bot after updating the token.")
            return

    logger.info("🚀 Bot is starting polling...")
    await application.run_polling(close_loop=False)


if __name__ == "__main__":
    print("🚀 Starting Telegram bot")
    print("📊 Starting dashboard server on port 8080")
    print(f"📊 Dashboard URL: https://{os.environ.get('REPL_SLUG', 'workspace')}.{os.environ.get('REPL_OWNER', 'arasbaker99')}.repl.co/status")

    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "already running" in str(e):
            logger.info("Using existing event loop...")
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
        else:
            logger.error(f"Startup Error: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Main crash: {e}", exc_info=True)
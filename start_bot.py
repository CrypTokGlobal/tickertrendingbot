#!/usr/bin/env python3
import os
import sys
import signal
import subprocess
import logging
import asyncio
import nest_asyncio
from dotenv import load_dotenv

# Print startup message directly to console for visibility
print("👋 Bot is launching...")
print("📝 Checking environment and configuration...")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bot_starter")

# Apply nest_asyncio to avoid runtime errors with event loops
nest_asyncio.apply()

def cleanup_previous_instances():
    """Kill any running bot instances"""
    try:
        # Kill main.py processes
        subprocess.run("pkill -9 -f 'python main.py'", shell=True)
        # Kill existing start_bot.py processes (except this one)
        current_pid = os.getpid()
        subprocess.run(f"pkill -9 -f 'python start_bot.py' -P {current_pid}", shell=True)

        # Also check for and kill any stalled bot processes
        try:
            import psutil
            current_pid = os.getpid()
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['pid'] == current_pid:
                    continue
                cmd = proc.info['cmdline'] if proc.info['cmdline'] else []
                if len(cmd) >= 2 and 'python' in cmd[0] and ('main.py' in cmd[1] or 'start_bot.py' in cmd[1]):
                    logger.info(f"Killing duplicate process: {proc.info['pid']}")
                    try:
                        os.kill(proc.info['pid'], 9)
                    except Exception as e:
                        logger.warning(f"Failed to kill process {proc.info['pid']}: {e}")
        except ImportError:
            # psutil not available, use simpler method
            pass

        logger.info("✅ Cleaned up previous bot instances")
    except Exception as e:
        logger.warning(f"Error during cleanup: {e}")

def check_environment():
    """Check environment variables and dependencies"""
    load_dotenv()
    token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ No bot token found! Please set TELEGRAM_BOT_TOKEN environment variable")
        return False

    logger.info(f"✅ Bot token found (length: {len(token)})")
    return True

async def delete_webhook():
    """Delete any existing webhooks to prevent conflicts"""
    try:
        from telegram import Bot
        from config import TELEGRAM_BOT_TOKEN

        if not TELEGRAM_BOT_TOKEN:
            logger.error("❌ Cannot delete webhook: No bot token found")
            return False

        # Remove any leading/trailing whitespace from token that might cause URL encoding issues
        clean_token = TELEGRAM_BOT_TOKEN.strip()
        logger.info(f"🧹 Deleting webhook with token: {clean_token[:4]}...{clean_token[-4:]}")
        bot = Bot(token=clean_token)
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook deleted successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Error deleting webhook: {e}", exc_info=True)
        if "Not Found" in str(e) or "Unauthorized" in str(e) or "InvalidToken" in str(e):
            logger.error("⚠️ The bot token appears to be invalid. Please check your TELEGRAM_BOT_TOKEN value.")
        return False

async def start_bot_async():
    """Start the main bot process asynchronously"""
    # First delete any existing webhook
    await delete_webhook()
    
    # Initialize dashboard data
    try:
        from dashboard import update_status, add_tracked_contract
        from data_manager import get_data_manager
        
        # Initialize bot status
        update_status("active", True)
        
        # Load tracked tokens into dashboard
        dm = get_data_manager()
        if "tracked_tokens" in dm.data:
            for token in dm.data["tracked_tokens"]:
                if "address" in token and "network" in token:
                    add_tracked_contract(token["address"], token["network"])
        
        logger.info("📊 Dashboard data initialized")
    except Exception as e:
        logger.warning(f"⚠️ Dashboard initialization issue: {e}")

    # Import main's async functions
    try:
        from main import main as main_async

        logger.info("🚀 Starting Telegram bot with full UI support...")
        try:
            # This will run the complete main.py with all handlers registered
            await main_async()
        except Exception as e:
            logger.error(f"❌ Error in bot execution: {e}", exc_info=True)
            return False
        return True
    except Exception as e:
        logger.error(f"❌ Failed to import from main.py: {e}", exc_info=True)
        return False

def start_bot():
    """Start the main bot process"""
    if not check_environment():
        return 1

    cleanup_previous_instances()

    logger.info("🚀 Starting main bot process...")

    # Run the async function
    try:
        asyncio.run(start_bot_async())
        return 0
    except RuntimeError as e:
        if "already running" in str(e):
            logger.info("Using existing event loop...")
            loop = asyncio.get_event_loop()
            loop.run_until_complete(start_bot_async())
            return 0
        else:
            logger.error(f"❌ Failed to start bot: {e}")
            return 1
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        return 1

if __name__ == "__main__":
    try:
        # Check if we should run async or sync version
        import asyncio
        try:
            from main import main as main_async
            logger.info("Running async main directly for deployment...")
            asyncio.run(main_async())
        except (RuntimeError, ImportError) as e:
            logger.info(f"Falling back to standard start_bot: {e}")
            exit_code = start_bot()
            sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Bot startup interrupted by user")
        sys.exit(0)

#!/usr/bin/env python3
import os
import subprocess
import time
import sys
import signal
import logging
import platform

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_for_bot_token():
    """Check if the BOT_TOKEN env variable is set"""
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("❌ ERROR: No bot token found in environment variables.")
        logger.error("Please set BOT_TOKEN or TELEGRAM_BOT_TOKEN in your .env file or Replit secrets.")
        return False
    logger.info(f"✅ Bot token found, length: {len(token)}")
    return True

async def clean_and_restart():
    """Kill any running bot processes, remove lock files, and restart the bot"""
    logger.info("🧹 Cleaning up locks and restarting bot...")
    
    # Kill any running bot processes (more comprehensive)
    try:
        if platform.system() != "Windows":
            # First with SIGTERM for clean shutdown
            subprocess.run("pkill -f 'python.*main.py'", shell=True)
            time.sleep(2)  # Give processes time to exit cleanly
            # Then with SIGKILL for any stubborn processes
            subprocess.run("pkill -9 -f 'python.*main.py'", shell=True)
        else:
            # Windows alternative
            subprocess.run("taskkill /F /IM python.exe /FI \"WINDOWTITLE eq *main.py*\" 2>NUL", shell=True)
            
        logger.info("✅ Terminated any running bot processes")
    except Exception as e:
        logger.warning(f"⚠️ Warning when killing processes: {e}")
    
    # Remove lock files if they exist
    lock_files = ["app.lock", "bot.lock", "bot.pid"]
    for lockfile in lock_files:
        if os.path.exists(lockfile):
            try:
                os.remove(lockfile)
                logger.info(f"✅ Removed {lockfile} file")
            except Exception as e:
                logger.warning(f"⚠️ Warning when removing lock file {lockfile}: {e}")
    
    # Double check if lock files were completely removed
    if any(os.path.exists(f) for f in lock_files):
        logger.warning("⚠️ Some lock files still exist. Possible permission issue.")
    
    # Run environment test first to make sure all required vars are set
    try:
        logger.info("🧪 Testing environment setup...")
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from test_environment import test_environment
        env_status = test_environment()
        if not env_status:
            logger.error("❌ Environment test failed! Please check your environment variables.")
            return False
        logger.info("✅ Environment test passed")
    except Exception as e:
        logger.error(f"❌ Error running environment test: {e}")
        return False
    
    # Ensure we have a bot token
    if not check_for_bot_token():
        return False
    
    # Start the bot
    logger.info("🚀 Starting the bot...")
    try:
        # Use sys.executable for more reliable Python path detection
        python_cmd = sys.executable or "python3"
        logger.info(f"Using Python executable: {python_cmd}")
        
        # Use a new process that will survive this script ending
        with open("bot.log", "a") as log_file:
            process = subprocess.Popen(
                [python_cmd, "main.py"],
                stdout=log_file,
                stderr=log_file,
                preexec_fn=os.setpgrp if platform.system() != "Windows" else None  # Make process immune to parent ending
            )
            
        # Write PID to file for external monitoring
        with open("bot.pid", "w") as f:
            f.write(str(process.pid))
            
        logger.info(f"✅ Bot started with PID {process.pid}")
        
        # Wait a bit to catch immediate failures
        time.sleep(3)
        if process.poll() is not None:
            logger.error(f"❌ Bot exited immediately with code {process.returncode}")
            with open("bot.log", "r") as log_file:
                last_lines = log_file.readlines()[-10:]  # Get last 10 lines
                logger.error("Last log entries:")
                for line in last_lines:
                    logger.error(f"  {line.strip()}")
            return False
            
        # If we got here, the bot started successfully
        dashboard_url = f"https://{os.environ.get('REPL_SLUG', 'workspace')}.{os.environ.get('REPL_OWNER', 'user')}.repl.co/status"
        logger.info(f"📊 Dashboard will be available at: {dashboard_url}")
        
        return process.pid  # Return PID for external tracking
    except Exception as e:
        logger.error(f"❌ Error running bot: {e}")
        return False

if __name__ == "__main__":
    import asyncio
    pid = asyncio.run(clean_and_restart())
    if pid:
        print(f"✅ Bot successfully started with PID: {pid}")
    else:
        print("❌ Failed to start bot")
        sys.exit(1)

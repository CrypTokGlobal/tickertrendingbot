
#!/usr/bin/env python3
import os
import sys
import time
import logging
import platform
import subprocess
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Optional: Add colored logs if package is available
try:
    import coloredlogs
    coloredlogs.install(level='INFO', logger=logger)
    logger.info("🎨 Colored logs enabled for better readability")
except ImportError:
    logger.info("ℹ️ Colored logs package not available, using standard logs")

def main():
    """Main function to start the bot with proper environment checks and reliability features"""
    # Check environment first
    logger.info("🧪 Testing environment...")
    try:
        from test_environment import test_environment
        env_success = test_environment()
        if not env_success:
            logger.error("❌ Environment test failed! Please check your environment variables.")
            logger.error("Make sure you have set TELEGRAM_BOT_TOKEN and INFURA_URL in Secrets.")
            return 1
    except Exception as e:
        logger.error(f"❌ Error testing environment: {e}")
        return 1

    # Clean up any existing processes and locks
    logger.info("🧹 Cleaning up old processes and locks...")
    try:
        from clean_restart import check_for_bot_token
        if not check_for_bot_token():
            logger.error("❌ Bot token missing! Please set it in Secrets.")
            return 1

        # Kill any running bot processes - with cross-platform support
        if platform.system() != "Windows":
            subprocess.run("pkill -9 -f 'python.*main.py' || true", shell=True)
        else:
            # Windows alternative (though not as effective)
            logger.info("Windows detected, using taskkill instead of pkill")
            subprocess.run("taskkill /F /IM python.exe /FI \"WINDOWTITLE eq *main.py*\" 2>NUL", shell=True)
        
        time.sleep(1)

        # Remove lock files
        for lockfile in ["app.lock", "bot.lock"]:
            if os.path.exists(lockfile):
                os.remove(lockfile)
                logger.info(f"✅ Removed {lockfile}")
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
        return 1

    # Create a new lock file before starting
    logger.info("🔒 Creating lock file...")
    try:
        with open("bot.lock", "w") as f:
            f.write(str(os.getpid()))
        logger.info(f"✅ Created bot.lock with PID {os.getpid()}")
    except Exception as e:
        logger.error(f"❌ Error creating lock file: {e}")
        # Continue anyway, not critical

    # Start the bot
    logger.info("🚀 Starting the bot...")
    try:
        # Use sys.executable as fallback for more reliable Python executable path
        python_cmd = sys.executable or "python3"
        logger.info(f"Using Python executable: {python_cmd}")
        
        with open("bot.log", "a") as log_file:
            process = subprocess.Popen(
                [python_cmd, "main.py"],
                stdout=log_file,
                stderr=log_file,
                preexec_fn=os.setpgrp if platform.system() != "Windows" else None
            )
        
        # Wait a bit to catch immediate failures
        time.sleep(3)
        if process.poll() is not None:
            logger.error(f"❌ Bot exited immediately with code {process.returncode}")
            with open("bot.log", "r") as log_file:
                last_lines = log_file.readlines()[-10:]  # Get last 10 lines
                logger.error("Last log entries:")
                for line in last_lines:
                    logger.error(f"  {line.strip()}")
            return process.returncode
        
        logger.info(f"✅ Bot started successfully with PID {process.pid}")
        logger.info(f"📊 Dashboard will be available at: https://{os.environ.get('REPL_SLUG', 'workspace')}.{os.environ.get('REPL_OWNER', 'user')}.repl.co/status")
        return 0
    except Exception as e:
        logger.error(f"❌ Error running bot: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

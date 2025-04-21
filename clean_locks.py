
import os
import logging
import sys

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_locks(lock_files=None):
    """Remove any stale lock files
    
    Args:
        lock_files (list): List of lock files to remove. Defaults to ["app.lock", "bot.lock"].
    """
    if lock_files is None:
        lock_files = ["app.lock", "bot.lock", "bot.pid"]
    
    removed_count = 0
    try:
        for lock_file in lock_files:
            if os.path.exists(lock_file):
                os.remove(lock_file)
                logger.info(f"✅ Removed stale {lock_file} file")
                removed_count += 1
            else:
                logger.info(f"✅ No {lock_file} file found")
        
        if removed_count > 0:
            print(f"✅ Cleanup complete! Removed {removed_count} lock files. You can now restart the bot.")
        else:
            print("✅ No lock files found. You can safely start the bot.")
        return True
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
        print(f"❌ Error during cleanup: {e}")
        return False
        
if __name__ == "__main__":
    # Check if specific lock files were specified as arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            # Remove all known lock files
            lock_files = ["app.lock", "bot.lock", "bot.pid", "monitor.lock"]
            print("🔍 Cleaning all known lock files...")
        else:
            # Remove specific lock files provided as arguments
            lock_files = sys.argv[1:]
            print(f"🔍 Cleaning specified lock files: {', '.join(lock_files)}")
    else:
        # Default behavior
        lock_files = ["app.lock", "bot.lock"]
        print("🔍 Cleaning default lock files...")
    
    clean_locks(lock_files)

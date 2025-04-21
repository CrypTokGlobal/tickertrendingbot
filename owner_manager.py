import json
import logging
import os
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
OWNER_ID_FILE = Path("owner_id.txt")
ADMINS_FILE = Path("admins.json")

def get_owner_id() -> int:
    """Get the owner's Telegram ID from file"""
    try:
        if OWNER_ID_FILE.exists():
            owner_id = OWNER_ID_FILE.read_text().strip()
            if owner_id and owner_id.isdigit():
                return int(owner_id)
    except Exception as e:
        logger.error(f"Error reading owner ID: {e}")
    return None

def set_owner_id(user_id: int) -> bool:
    """Set the owner's Telegram ID"""
    try:
        OWNER_ID_FILE.write_text(str(user_id))
        return True
    except Exception as e:
        logger.error(f"Error setting owner ID: {e}")
        return False

def ensure_owner(user_id: int) -> bool:
    """Set owner ID automatically if no owner is configured"""
    if not get_owner_id():
        success = set_owner_id(user_id)
        if success:
            logger.info(f"🔐 Owner auto-assigned to {user_id}")
        return success
    return False

def is_owner(user_id: int) -> bool:
    """Check if a user is the bot owner"""
    owner_id = get_owner_id()
    return owner_id is not None and user_id == owner_id

def load_admins() -> dict:
    """Load admin list from file"""
    if not ADMINS_FILE.exists():
        # Create default empty admin list
        return {"user_ids": [], "usernames": []}

    try:
        content = ADMINS_FILE.read_text()
        if not content.strip():
            return {"user_ids": [], "usernames": []}

        data = json.loads(content)

        # Handle legacy format (simple list of ids)
        if isinstance(data, list):
            logger.info("Converting legacy admin format to new structure")
            return {"user_ids": data, "usernames": []}

        # Ensure the structure is correct
        if not isinstance(data, dict):
            logger.warning("Admin data has invalid format, resetting")
            return {"user_ids": [], "usernames": []}

        # Ensure required keys exist
        if "user_ids" not in data:
            data["user_ids"] = []
        if "usernames" not in data:
            data["usernames"] = []

        return data
    except json.JSONDecodeError:
        logger.error("Admin file contains invalid JSON, resetting to defaults")
        return {"user_ids": [], "usernames": []}
    except Exception as e:
        logger.error(f"Error loading admins: {e}")
        return {"user_ids": [], "usernames": []}

def save_admins(admins: dict) -> bool:
    """Save admin list to file"""
    try:
        ADMINS_FILE.write_text(json.dumps(admins, indent=2))
        return True
    except Exception as e:
        logger.error(f"Error saving admins: {e}")
        return False

def is_admin(user_id: int, username: str = None) -> bool:
    """Check if a user is an admin by ID or username"""
    admins = load_admins()

    # Check by user ID first (more reliable)
    if user_id in admins.get("user_ids", []):
        return True

    # If username provided, check that too (case insensitive)
    if username:
        return any(un.lower() == username.lower() for un in admins.get("usernames", []))

    return False
    
def is_authorized(user_id: int, username: str = None) -> bool:
    """Check if a user is authorized (owner or admin)"""
    return is_owner(user_id) or is_admin(user_id, username)

def add_admin(user_id: int = None, username: str = None, notify: bool = True) -> bool:
    """Add a user to admin list by ID, username, or both"""
    if user_id is None and not username:
        logger.error("Cannot add admin: both user_id and username are empty")
        return False

    admins = load_admins()
    changed = False
    timestamp = datetime.now().isoformat()

    if user_id is not None and user_id not in admins["user_ids"]:
        admins["user_ids"].append(user_id)
        changed = True

    if username and username.lower() not in [un.lower() for un in admins["usernames"]]:
        admins["usernames"].append(username)
        changed = True

    if changed:
        success = save_admins(admins)
        if success and notify:
            notify_admin_change(added=True, user_id=user_id, username=username)
        return success

    return True  # Already an admin, no change needed

def remove_admin(user_id: int = None, username: str = None, notify: bool = True) -> bool:
    """Remove a user from admin list by ID, username, or both"""
    if user_id is None and not username:
        logger.error("Cannot remove admin: both user_id and username are empty")
        return False

    admins = load_admins()
    changed = False

    if user_id is not None and user_id in admins["user_ids"]:
        admins["user_ids"].remove(user_id)
        changed = True

    if username:
        # Case insensitive removal
        lower_username = username.lower()
        original_usernames = admins["usernames"].copy()
        admins["usernames"] = [un for un in admins["usernames"] if un.lower() != lower_username]
        if len(original_usernames) != len(admins["usernames"]):
            changed = True

    if changed:
        success = save_admins(admins)
        if success and notify:
            notify_admin_change(added=False, user_id=user_id, username=username)
        return success

    return True  # Already not an admin, no change needed

def reset_admins() -> bool:
    """Reset all admins (for emergency use)"""
    try:
        empty_admins = {"user_ids": [], "usernames": []}
        ADMINS_FILE.write_text(json.dumps(empty_admins, indent=2))
        logger.warning("⚠️ Admin list has been reset!")
        return True
    except Exception as e:
        logger.error(f"Error resetting admins: {e}")
        return False

def get_admin_usernames() -> list:
    """Get list of all admin usernames"""
    admins = load_admins()
    return admins.get("usernames", [])

def get_admin_ids() -> list:
    """Get list of all admin user IDs"""
    admins = load_admins()
    return admins.get("user_ids", [])

def notify_admin_change(added: bool, user_id: int = None, username: str = None):
    """Log admin changes for auditing purposes"""
    action = "added" if added else "removed"
    user_info = []
    if user_id:
        user_info.append(f"ID: {user_id}")
    if username:
        user_info.append(f"username: @{username}")

    user_str = ", ".join(user_info)
    logger.info(f"Admin {action}: {user_str}")

def count_admins() -> int:
    """Count the number of unique admins (combining IDs and usernames)"""
    admins = load_admins()
    return len(admins.get("user_ids", [])) + len(admins.get("usernames", []))

def get_all_authorized() -> list:
    """Get list of all authorized users (owner + admins)"""
    authorized = set()

    # Add owner
    owner_id = get_owner_id()
    if owner_id:
        authorized.add(owner_id)

    # Add admins
    admins = load_admins()
    for admin_id in admins.get("user_ids", []):
        authorized.add(admin_id)

    return list(authorized)

def strictly_owner(func):
    """Decorator to restrict command access to only the owner"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_owner(user_id):
            await update.message.reply_text("❌ This command can only be used by the bot owner.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def admin_only(func):
    """Decorator to restrict command access to admins and owner"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        user_id = user.id
        username = user.username

        if is_owner(user_id) or is_admin(user_id, username):
            return await func(update, context, *args, **kwargs)

        await update.message.reply_text("❌ This command requires admin privileges.")
        return
    return wrapper
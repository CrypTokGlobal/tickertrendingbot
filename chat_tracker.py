
import json
from pathlib import Path
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

CHAT_FILE = Path("active_chats.json")

def load_chats():
    if CHAT_FILE.exists():
        try:
            return json.loads(CHAT_FILE.read_text())
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding active_chats.json: {e}")
            return {}
    return {}

def save_chat(chat_id, chat_info=None):
    """Save a chat to the active_chats.json file"""
    try:
        chats = load_chats()

        chat_id_str = str(chat_id)
        if chat_id_str not in chats:
            # First time seeing this chat
            chats[chat_id_str] = {
                "added_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            }
        else:
            # Update existing chat
            chats[chat_id_str]["last_active"] = datetime.now().isoformat()

        # Add chat info if provided
        if chat_info:
            chats[chat_id_str].update(chat_info)

        with open("active_chats.json", "w") as f:
            json.dump(chats, f, indent=2)

        # Update the dashboard with the new chat count
        try:
            from dashboard import update_chat_count
            update_chat_count(len(chats))
        except ImportError:
            logger.warning("Dashboard module not available for updating chat count")

        return True
    except Exception as e:
        logger.error(f"Error saving chat: {e}")
        return False

def remove_chat(chat_id):
    """Remove a chat from the active_chats.json file"""
    try:
        chats = load_chats()
        chat_id_str = str(chat_id)
        if chat_id_str in chats:
            del chats[chat_id_str]
            with open("active_chats.json", "w") as f:
                json.dump(chats, f, indent=2)
            
            # Update the dashboard with the new chat count
            try:
                from dashboard import update_chat_count
                update_chat_count(len(chats))
            except ImportError:
                logger.warning("Dashboard module not available for updating chat count")
                
            return True
        return False
    except Exception as e:
        logger.error(f"Error removing chat {chat_id}: {e}")
        return False

def get_all_chats():
    return load_chats()

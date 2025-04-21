import os
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# File paths
TRANSACTION_DATA_FILE = 'transaction_data.json'
BOOST_DATA_FILE = 'boost_data.json'

# Create a global instance of DataManager
_data_manager = None

def get_data_manager():
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
    return _data_manager

# Helper functions for token tracking
def add_tracked_token(chat_id, address, name, symbol, min_volume_usd, network="ethereum"):
    """Add a token to track for a specific chat"""
    from utils import save_tracked_tokens, save_group_tokens, load_group_tokens

    dm = get_data_manager()
    address = address.lower()

    # Get existing tracked tokens
    tracked_tokens = dm.data.get("tracked_tokens", [])

    # Check if token is already being tracked for this chat
    token_exists = False
    for token in tracked_tokens:
        if token.get("address", "").lower() == address and str(token.get("chat_id", "")) == str(chat_id):
            # Token already exists for this chat, just update it
            token["name"] = name
            token["symbol"] = symbol
            token["min_volume_usd"] = float(min_volume_usd)
            token["network"] = network
            token["chat_id"] = int(chat_id) if chat_id else None
            token_exists = True
            break

    # If token doesn't exist for this chat, add it
    if not token_exists:
        token_data = {
            "address": address,
            "name": name,
            "symbol": symbol,
            "min_volume_usd": float(min_volume_usd),
            "network": network,
            "chat_id": int(chat_id) if chat_id else None,
            "added_at": datetime.now().isoformat()
        }
        tracked_tokens.append(token_data)
        dm.data["tracked_tokens"] = tracked_tokens

        # Also register the token with the token monitor
        from token_monitor import get_token_monitor
        token_monitor = get_token_monitor()
        token_monitor.add_token(address, network)

    # Save global tokens
    save_tracked_tokens()

    # Now update the group-specific mapping
    group_tracked_tokens = load_group_tokens()

    # Ensure chat_id is registered
    if int(chat_id) not in group_tracked_tokens:
        group_tracked_tokens[int(chat_id)] = set()

    # Add this token to the chat's tracking set
    group_tracked_tokens[int(chat_id)].add(address)

    # Save the updated mapping
    save_group_tokens(group_tracked_tokens)

    # Log the action
    logger.info(f"✅ Added/updated token {name} ({address}) for chat {chat_id}")

    return True

def remove_tracked_token(chat_id, address, network=None):
    """
    Remove a tracked token.

    Args:
        chat_id: The chat ID where the token is tracked
        address: Token contract address
        network: Optional network filter

    Returns:
        bool: True if removed, False if not found
    """
    dm = get_data_manager()
    if "tracked_tokens" not in dm.data:
        return False

    # Normalize inputs
    address = address.lower().strip()
    chat_id = str(chat_id)

    initial_length = len(dm.data["tracked_tokens"])

    # Find matching tokens before removal for token monitor cleanup
    matching_tokens = []
    if network:
        network = network.lower().strip()
        matching_tokens = [
            t for t in dm.data["tracked_tokens"] 
            if (str(t.get("chat_id")) == chat_id and 
               t.get("address").lower() == address and
               t.get("network", "").lower() == network)
        ]
        dm.data["tracked_tokens"] = [
            t for t in dm.data["tracked_tokens"] 
            if not (str(t.get("chat_id")) == chat_id and 
                   t.get("address").lower() == address and
                   t.get("network", "").lower() == network)
        ]
    else:
        matching_tokens = [
            t for t in dm.data["tracked_tokens"] 
            if (str(t.get("chat_id")) == chat_id and 
               t.get("address").lower() == address)
        ]
        dm.data["tracked_tokens"] = [
            t for t in dm.data["tracked_tokens"] 
            if not (str(t.get("chat_id")) == chat_id and 
                   t.get("address").lower() == address)
        ]

    if len(dm.data["tracked_tokens"]) < initial_length:
        logger.info(f"Removed token {address} for chat {chat_id}")

        # Stop monitoring this token with the token monitor
        try:
            from token_monitor import get_token_monitor
            token_monitor = get_token_monitor()
            token_monitor.stop_tracking(address, chat_id)
        except Exception as e:
            logger.error(f"Error stopping token monitoring: {e}")

        # Save changes to transaction_data.json
        try:
            from utils import save_tracked_tokens
            save_tracked_tokens()
            logger.info(f"Saved updated tokens list after removing {address}")
        except Exception as e:
            logger.error(f"Error saving tracked tokens: {e}")

        return dm._save_data()

    logger.info(f"Token {address} not found for chat {chat_id}")
    return False

def list_tracked_tokens(chat_id, network=None):
    """
    List tracked tokens for a chat.

    Args:
        chat_id: The chat ID to list tokens for
        network: Optional network filter

    Returns:
        list: Tracked tokens for the chat
    """
    dm = get_data_manager()
    if "tracked_tokens" not in dm.data:
        return []

    chat_id = str(chat_id)

    if network:
        network = network.lower().strip()
        return [
            t for t in dm.data["tracked_tokens"] 
            if str(t.get("chat_id")) == chat_id and t.get("network", "").lower() == network
        ]
    else:
        return [
            t for t in dm.data["tracked_tokens"] 
            if str(t.get("chat_id")) == chat_id
        ]

def get_tokens_by_network(network):
    """
    Get all tokens for a specific network.

    Args:
        network: The blockchain network

    Returns:
        list: All tokens for the network
    """
    dm = get_data_manager()
    if "tracked_tokens" not in dm.data:
        return []

    network = network.lower().strip()
    return [t for t in dm.data["tracked_tokens"] if t.get("network", "").lower() == network]

def register_group(chat_id, name, is_admin=False):
    """
    Register a new group/chat for token tracking.

    Args:
        chat_id: The chat ID to register
        name: Name of the chat or group
        is_admin: Whether the bot has admin rights

    Returns:
        bool: Success or failure
    """
    dm = get_data_manager()
    chat_id = str(chat_id)

    # Initialize group tracking if it doesn't exist
    if "groups" not in dm.data:
        dm.data["groups"] = {}

    # Check if group already registered
    if chat_id in dm.data["groups"]:
        # Update existing group info
        dm.data["groups"][chat_id]["name"] = name
        dm.data["groups"][chat_id]["is_admin"] = is_admin
        dm.data["groups"][chat_id]["last_activity"] = datetime.now().isoformat()
        logger.info(f"Updated existing group: {name} ({chat_id})")
    else:
        # Register new group
        dm.data["groups"][chat_id] = {
            "name": name,
            "is_admin": is_admin,
            "registered_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "active": True
        }
        logger.info(f"Registered new group: {name} ({chat_id})")

    # Also update chat settings for backward compatibility
    update_chat_settings(chat_id, "chat_title", name)
    update_chat_settings(chat_id, "bot_is_admin", is_admin)
    update_chat_settings(chat_id, "active", True)

    return dm._save_data()

def update_chat_settings(chat_id, setting_name, setting_value):
    """
    Update settings for a specific chat.

    Args:
        chat_id: The chat ID to update settings for
        setting_name: Setting key
        setting_value: Setting value

    Returns:
        bool: Success or failure
    """
    dm = get_data_manager()
    chat_id = str(chat_id)

    # Initialize chat_settings if it doesn't exist
    if "chat_settings" not in dm.data:
        dm.data["chat_settings"] = {}

    # Initialize this chat's settings if needed
    if chat_id not in dm.data["chat_settings"]:
        dm.data["chat_settings"][chat_id] = {
            "registered_at": datetime.now().isoformat(),
            "active": True
        }

    # Update the setting
    dm.data["chat_settings"][chat_id][setting_name] = setting_value
    logger.info(f"Updated setting {setting_name}={setting_value} for chat {chat_id}")

    return dm._save_data()

def get_chat_settings(chat_id, setting_name=None, default=None):
    """
    Get chat settings.

    Args:
        chat_id: The chat ID to get settings for
        setting_name: Optional specific setting to retrieve
        default: Default value if setting doesn't exist

    Returns:
        The setting value or all settings if setting_name is None
    """
    dm = get_data_manager()
    chat_id = str(chat_id)

    if "chat_settings" not in dm.data or chat_id not in dm.data["chat_settings"]:
        return default

    if setting_name:
        return dm.data["chat_settings"][chat_id].get(setting_name, default)

    return dm.data["chat_settings"][chat_id]

def get_registered_chats(chat_type=None, active_only=True):
    """
    Get all registered chats.

    Args:
        chat_type: Optional filter by chat type ('group', 'supergroup', etc.)
        active_only: Only return active chats

    Returns:
        list: List of chat IDs matching criteria
    """
    dm = get_data_manager()

    if "chat_settings" not in dm.data:
        return []

    chats = []
    for chat_id, settings in dm.data["chat_settings"].items():
        if active_only and not settings.get("active", True):
            continue

        if chat_type and settings.get("chat_type") != chat_type:
            continue

        chats.append(chat_id)

    return chats

def remove_chat_data(chat_id):
    """
    Remove all data for a chat (when bot is removed, etc.)

    Args:
        chat_id: The chat ID to clean up

    Returns:
        bool: Success or failure
    """
    dm = get_data_manager()
    chat_id = str(chat_id)

    # Mark as inactive instead of deleting
    if "chat_settings" in dm.data and chat_id in dm.data["chat_settings"]:
        dm.data["chat_settings"][chat_id]["active"] = False
        logger.info(f"Marked chat {chat_id} as inactive")

    # Remove tracked tokens for this chat
    if "tracked_tokens" in dm.data:
        initial_count = len(dm.data["tracked_tokens"])
        dm.data["tracked_tokens"] = [
            t for t in dm.data["tracked_tokens"] if str(t.get("chat_id")) != chat_id
        ]
        removed = initial_count - len(dm.data["tracked_tokens"])
        if removed > 0:
            logger.info(f"Removed {removed} tracked tokens for chat {chat_id}")

    return dm._save_data()

class DataManager:
    def __init__(self, data_file=TRANSACTION_DATA_FILE):
        self.data_file = data_file
        self.data = self._load_data()

    def _load_data(self):
        """Load data from JSON file or create a new data structure."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Error decoding {self.data_file}, creating new data")
                return self._create_new_data()
        else:
            return self._create_new_data()

    def _create_new_data(self):
        """Create a new data structure."""
        return {
            "transactions": [],
            "tracked_tokens": [],
            "users": {}
        }

    def _save_data(self):
        """Save data to JSON file."""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            return False

    def save(self):
        """Public method to save data to file."""
        return self._save_data()

    def record_transaction(self, transaction_type, token_address, amount, price=None, tx_hash=None, user_id=None):
        """Record a transaction in the data file."""
        transaction = {
            "timestamp": datetime.now().isoformat(),
            "type": transaction_type,  # "buy" or "sell"
            "token_address": token_address,
            "amount": amount,
            "price": price,
            "tx_hash": tx_hash,
            "user_id": user_id
        }

        self.data["transactions"].append(transaction)
        return self._save_data()

    def add_watched_token(self, token_address, token_name=None, token_symbol=None):
        """Add a token to the watchlist."""
        for token in self.data.get("watched_tokens", []):
            if token["address"] == token_address:
                logger.info(f"Token {token_address} already in watchlist")
                return True

        token_data = {
            "address": token_address,
            "name": token_name,
            "symbol": token_symbol,
            "added_at": datetime.now().isoformat()
        }

        self.data.setdefault("watched_tokens", []).append(token_data)
        return self._save_data()

    def remove_watched_token(self, token_address):
        """Remove a token from the watchlist."""
        if "watched_tokens" not in self.data:
            return False

        initial_length = len(self.data["watched_tokens"])
        self.data["watched_tokens"] = [t for t in self.data["watched_tokens"] if t["address"] != token_address]

        if len(self.data["watched_tokens"]) < initial_length:
            return self._save_data()
        else:
            logger.info(f"Token {token_address} not found in watchlist")
            return False

    def get_watched_tokens(self):
        """Get all watched tokens."""
        return self.data.get("watched_tokens", [])

    def get_user_transactions(self, user_id):
        """Get all transactions for a specific user."""
        return [t for t in self.data.get("transactions", []) if t.get("user_id") == user_id]

    def register_user(self, user_id, telegram_username=None, wallet_address=None):
        """Register or update a user."""
        if str(user_id) not in self.data.get("users", {}):
            if "users" not in self.data:
                self.data["users"] = {}

            self.data["users"][str(user_id)] = {
                "telegram_username": telegram_username,
                "wallet_address": wallet_address,
                "registered_at": datetime.now().isoformat(),
                "settings": {
                    "notifications_enabled": True,
                    "max_slippage": 1.0  # Default 1% slippage
                }
            }
        else:
            # Update existing user
            if telegram_username:
                self.data["users"][str(user_id)]["telegram_username"] = telegram_username
            if wallet_address:
                self.data["users"][str(user_id)]["wallet_address"] = wallet_address

        return self._save_data()

    def update_user_setting(self, user_id, setting_name, setting_value):
        """Update a user setting."""
        if "users" not in self.data or str(user_id) not in self.data["users"]:
            logger.error(f"User {user_id} not found")
            return False

        if "settings" not in self.data["users"][str(user_id)]:
            self.data["users"][str(user_id)]["settings"] = {}

        self.data["users"][str(user_id)]["settings"][setting_name] = setting_value
        return self._save_data()

    def get_user_data(self, user_id):
        """Get user data."""
        if "users" not in self.data:
            return None
        return self.data["users"].get(str(user_id))

def get_tracked_token_info(address, chat_id=None):
    """Return tracked token info based on address and optional chat ID."""
    dm = get_data_manager()
    tokens = dm.data.get("tracked_tokens", [])
    address = address.lower().strip()

    if chat_id:
        chat_id = str(chat_id)
        for token in tokens:
            if token["address"].lower() == address and str(token.get("chat_id", "")) == chat_id:
                return token
    else:
        for token in tokens:
            if token["address"].lower() == address:
                return token

    return None

# Example usage
if __name__ == "__main__":
    dm = DataManager()
    # Add a test token to watchlist
    dm.add_watched_token("0x1f9840a85d5af5bf1d1762f925bdaddc4201f984", "Uniswap", "UNI")
    # Show watched tokens
    watched_tokens = dm.get_watched_tokens()
    print(f"Watched tokens: {watched_tokens}")
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

# Set up logging
logger = logging.getLogger(__name__)

TRANSACTION_DATA_FILE = "transaction_data.json"

def load_transaction_data() -> Dict[str, Any]:
    """Load transaction data from file"""
    try:
        if os.path.exists(TRANSACTION_DATA_FILE):
            with open(TRANSACTION_DATA_FILE, "r") as f:
                return json.load(f)
        else:
            logger.info(f"Transaction data file not found, creating new one.")
            return create_default_transaction_data()
    except Exception as e:
        logger.error(f"Error loading transaction data: {e}")
        return create_default_transaction_data()

def save_transaction_data(data: Dict[str, Any]) -> bool:
    """Save transaction data to file"""
    try:
        with open(TRANSACTION_DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Transaction data saved successfully.")
        return True
    except Exception as e:
        logger.error(f"Error saving transaction data: {e}")
        return False

def create_default_transaction_data() -> Dict[str, Any]:
    """Create default transaction data structure"""
    return {
        "tracked_tokens": [],
        "groups": {},
        "chat_settings": {},
        "last_updated": datetime.now().isoformat()
    }

def save_tokens_to_file(tokens: List[Dict[str, Any]], filename: str = TRANSACTION_DATA_FILE) -> bool:
    """Save tokens to a file"""
    try:
        data = load_transaction_data()
        data["tracked_tokens"] = tokens
        data["last_updated"] = datetime.now().isoformat()
        return save_transaction_data(data)
    except Exception as e:
        logger.error(f"Error saving tokens to file: {e}")
        return False

def add_tracked_token(
    chat_id: Union[str, int], 
    address: str, 
    name: str, 
    symbol: str, 
    min_volume_usd: float = 5.0, 
    network: str = "ethereum"
) -> bool:
    """Add a token to the tracked tokens"""
    try:
        # Ensure we're using string for chat_id consistently
        chat_id_str = str(chat_id)

        data = load_transaction_data()

        # Check if token is already tracked
        for token in data["tracked_tokens"]:
            if token["address"].lower() == address.lower() and str(token["chat_id"]) == chat_id_str:
                logger.info(f"Token {address} already tracked in chat {chat_id}")
                return False

        # Add the new token
        token_data = {
            "chat_id": chat_id_str,
            "address": address,
            "name": name,
            "symbol": symbol,
            "min_volume_usd": float(min_volume_usd),
            "network": network,
            "added_at": datetime.now().isoformat(),
            "last_alert_sent_at": None
        }

        data["tracked_tokens"].append(token_data)
        data["last_updated"] = datetime.now().isoformat()

        # Save the updated data
        return save_transaction_data(data)
    except Exception as e:
        logger.error(f"Error adding tracked token: {e}")
        return False

def remove_tracked_token(chat_id: Union[str, int], address: str) -> bool:
    """Remove a token from the tracked tokens"""
    try:
        # Ensure we're using string for chat_id consistently
        chat_id_str = str(chat_id)

        data = load_transaction_data()

        # Find the token to remove
        initial_count = len(data["tracked_tokens"])
        data["tracked_tokens"] = [
            t for t in data["tracked_tokens"] 
            if not (t["address"].lower() == address.lower() and str(t["chat_id"]) == chat_id_str)
        ]

        # If no tokens were removed, return False
        if len(data["tracked_tokens"]) == initial_count:
            logger.info(f"Token {address} not found for chat {chat_id}")
            return False

        data["last_updated"] = datetime.now().isoformat()

        # Save the updated data
        return save_transaction_data(data)
    except Exception as e:
        logger.error(f"Error removing tracked token: {e}")
        return False

def update_last_alert_sent(chat_id: Union[str, int], address: str) -> bool:
    """Update the last_alert_sent_at timestamp for a token"""
    try:
        # Ensure we're using string for chat_id consistently
        chat_id_str = str(chat_id)

        data = load_transaction_data()

        # Find the token to update
        for token in data["tracked_tokens"]:
            if token["address"].lower() == address.lower() and str(token["chat_id"]) == chat_id_str:
                token["last_alert_sent_at"] = datetime.now().isoformat()
                data["last_updated"] = datetime.now().isoformat()
                return save_transaction_data(data)

        logger.info(f"Token {address} not found for chat {chat_id}")
        return False
    except Exception as e:
        logger.error(f"Error updating last alert sent: {e}")
        return False

def register_chat(chat_id: Union[str, int], chat_title: str, is_admin: bool = False) -> bool:
    """Register a chat in the transaction data"""
    try:
        # Ensure we're using string for chat_id consistently
        chat_id_str = str(chat_id)

        data = load_transaction_data()

        now = datetime.now().isoformat()

        # Add/update group info
        if chat_id_str not in data["groups"]:
            data["groups"][chat_id_str] = {
                "name": chat_title,
                "is_admin": is_admin,
                "registered_at": now,
                "last_activity": now,
                "active": True
            }
        else:
            data["groups"][chat_id_str]["last_activity"] = now
            data["groups"][chat_id_str]["active"] = True
            data["groups"][chat_id_str]["name"] = chat_title

        # Add/update chat settings
        if chat_id_str not in data["chat_settings"]:
            data["chat_settings"][chat_id_str] = {
                "registered_at": now,
                "active": True,
                "chat_title": chat_title,
                "bot_is_admin": is_admin
            }
        else:
            data["chat_settings"][chat_id_str]["active"] = True
            data["chat_settings"][chat_id_str]["chat_title"] = chat_title
            data["chat_settings"][chat_id_str]["bot_is_admin"] = is_admin

        data["last_updated"] = now

        # Save the updated data
        return save_transaction_data(data)
    except Exception as e:
        logger.error(f"Error registering chat: {e}")
        return False

def get_tokens_by_chat(chat_id: Union[str, int], network: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get tokens tracked by a specific chat"""
    try:
        # Ensure we're using string for chat_id consistently
        chat_id_str = str(chat_id)

        data = load_transaction_data()

        # Filter tokens by chat_id and optionally network
        tokens = [t for t in data["tracked_tokens"] if str(t["chat_id"]) == chat_id_str]

        if network:
            tokens = [t for t in tokens if t["network"].lower() == network.lower()]

        return tokens
    except Exception as e:
        logger.error(f"Error getting tokens by chat: {e}")
        return []

def get_tokens_by_network(network: str) -> List[Dict[str, Any]]:
    """Get all tokens for a specific network"""
    try:
        data = load_transaction_data()

        # Filter tokens by network
        return [t for t in data["tracked_tokens"] if t["network"].lower() == network.lower()]
    except Exception as e:
        logger.error(f"Error getting tokens by network: {e}")
        return []

def add_token_to_file(token_info: Dict[str, Any]) -> bool:
    """Add a token to the file"""
    try:
        data = load_transaction_data()
        # Check if token is already tracked for this chat
        for token in data["tracked_tokens"]:
            if (token.get("address", "").lower() == token_info["address"].lower() and 
                str(token.get("chat_id", "")) == str(token_info["chat_id"])):
                # Already tracked, update it
                token.update(token_info)
                return save_transaction_data(data)

        # Add new token
        data["tracked_tokens"].append(token_info)
        return save_transaction_data(data)
    except Exception as e:
        logger.error(f"Error adding token to file: {e}")
        return False

def remove_token_from_file(address: str, chat_id: Union[str, int], chain: str = "ethereum") -> bool:
    """Remove a token from the file"""
    try:
        chat_id_str = str(chat_id)
        data = load_transaction_data()

        # Find and remove token
        initial_count = len(data["tracked_tokens"])
        data["tracked_tokens"] = [
            t for t in data["tracked_tokens"] 
            if not (t["address"].lower() == address.lower() and 
                   str(t.get("chat_id", "")) == chat_id_str and
                   t.get("chain", "ethereum").lower() == chain.lower())
        ]

        # If no tokens were removed, return False
        if len(data["tracked_tokens"]) == initial_count:
            logger.info(f"Token {address} not found for chat {chat_id} on {chain}")
            return False

        return save_transaction_data(data)
    except Exception as e:
        logger.error(f"Error removing token from file: {e}")
        return False

def get_timestamp():
    """
    Get current timestamp in seconds
    """
    import time
    return int(time.time())
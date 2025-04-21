import time
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

# Setup logging
logger = logging.getLogger(__name__)

class BoostManager:
    """Manages boosted tokens that appear on alerts"""

    def __init__(self):
        self.active_boosts = {}  # key: "chain:token_address", value: boost info
        self.boost_file = "boost_data.json"
        self._load_data()

    def _load_data(self):
        """Load boost data from file"""
        try:
            with open(self.boost_file, "r") as f:
                data = json.load(f)
                self.active_boosts = data.get("active_boosts", {})
                logger.info(f"Loaded {len(self.active_boosts)} active boosts from file")
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(f"No boost data file found or invalid JSON. Starting with empty boosts.")
            self.active_boosts = {}
            self._save_data()  # Create the file

    def _save_data(self):
        """Save boost data to file"""
        try:
            with open(self.boost_file, "w") as f:
                json.dump({"active_boosts": self.active_boosts}, f, indent=2)
                logger.debug("Boost data saved to file")
        except Exception as e:
            logger.error(f"Error saving boost data: {e}")

    def add_boost(self, token_address: str, chat_link: str, duration_hours: int, 
                 boosted_by: str, tx_hash: Optional[str] = None, chain: str = "ethereum",
                 custom_emojis: str = "🚀🔥💰") -> bool:
        """
        Add a new boost for a token

        Args:
            token_address: The token contract address
            chat_link: Telegram group/channel link to promote
            duration_hours: How long the boost should last in hours
            boosted_by: User ID of who purchased the boost
            tx_hash: Transaction hash for the payment (optional)
            chain: Blockchain network (ethereum or solana)
            custom_emojis: Custom emoji string for the boost

        Returns:
            bool: Success or failure
        """
        try:
            # Normalize token address and create key
            token_address = token_address.lower()
            boost_key = f"{chain}:{token_address}"

            # Calculate expiry time
            now = time.time()
            expires_at = now + (duration_hours * 3600)
            expires_datetime = datetime.fromtimestamp(expires_at)

            # Create boost data
            boost_data = {
                "token_address": token_address,
                "chat_link": chat_link,
                "duration_hours": duration_hours,
                "boosted_by": boosted_by,
                "tx_hash": tx_hash,
                "chain": chain,
                "created_at": now,
                "expires_at": expires_at,
                "expires_at_readable": expires_datetime.strftime("%Y-%m-%d %H:%M UTC"),
                "custom_emojis": custom_emojis
            }

            # Add or update the boost
            self.active_boosts[boost_key] = boost_data
            self._save_data()

            logger.info(f"Added boost for {boost_key} until {expires_datetime}")
            return True
        except Exception as e:
            logger.error(f"Error adding boost: {e}")
            return False

    def remove_boost(self, token_address: str, chain: str = "ethereum") -> bool:
        """
        Remove a boost for a token

        Args:
            token_address: The token contract address
            chain: Blockchain network

        Returns:
            bool: True if removed, False if not found
        """
        try:
            # Normalize token address and create key
            token_address = token_address.lower()
            boost_key = f"{chain}:{token_address}"

            if boost_key in self.active_boosts:
                del self.active_boosts[boost_key]
                self._save_data()
                logger.info(f"Removed boost for {boost_key}")
                return True
            else:
                logger.warning(f"No boost found for {boost_key}")
                return False
        except Exception as e:
            logger.error(f"Error removing boost: {e}")
            return False

    def get_boost_data(self, token_address: str, chain: str = "ethereum") -> Optional[Dict[str, Any]]:
        """
        Get boost data for a token if it exists

        Args:
            token_address: The token contract address
            chain: Blockchain network

        Returns:
            Dict or None: Boost data or None if not boosted
        """
        # Normalize token address and create key
        token_address = token_address.lower()
        boost_key = f"{chain}:{token_address}"

        # Return data if exists and not expired
        boost_data = self.active_boosts.get(boost_key)
        if boost_data:
            if boost_data.get("expires_at", 0) > time.time():
                return boost_data
            else:
                # Auto-remove expired boosts when queried
                logger.info(f"Auto-removing expired boost for {boost_key}")
                self.remove_boost(token_address, chain)

        return None

    def list_active_boosts(self) -> Dict[str, Dict[str, Any]]:
        """
        List all currently active boosts

        Returns:
            Dict: All active boosts
        """
        # Filter out expired boosts
        now = time.time()
        active = {k: v for k, v in self.active_boosts.items() 
                 if v.get("expires_at", 0) > now}

        # If we filtered any, save the update
        if len(active) != len(self.active_boosts):
            self.active_boosts = active
            self._save_data()

        return active

    async def check_and_clean_expired(self):
        """Background task to periodically check and remove expired boosts"""
        while True:
            try:
                now = time.time()
                expired_keys = [k for k, v in self.active_boosts.items() 
                              if v.get("expires_at", 0) <= now]

                if expired_keys:
                    for key in expired_keys:
                        chain, addr = key.split(":", 1)
                        logger.info(f"Cleaning expired boost for {key}")
                        self.remove_boost(addr, chain)
            except Exception as e:
                logger.error(f"Error in expired boost cleanup: {e}")

            # Check every hour
            await asyncio.sleep(3600)

    async def process_boost_payment(self, network: str, token_address: str, 
                                  duration: int, telegram_link: str,
                                  emojis: str = "🚀🔥💰") -> bool:
        """
        Process a boost payment (simulated for now)

        Args:
            network: Blockchain network (ethereum or solana)
            token_address: Token address to boost
            duration: Duration in hours
            telegram_link: Link to promote
            emojis: Custom emojis

        Returns:
            bool: Success status
        """
        try:
            # In a real implementation, we'd verify payment here
            # For now, we'll just add the boost
            return self.add_boost(
                token_address=token_address,
                chat_link=telegram_link,
                duration_hours=duration,
                boosted_by="system",
                chain=network,
                custom_emojis=emojis
            )
        except Exception as e:
            logger.error(f"Error processing boost payment: {e}")
            return False

# Singleton instance
_boost_manager = None

def get_boost_manager():
    """Get or create the singleton BoostManager instance"""
    global _boost_manager
    if _boost_manager is None:
        _boost_manager = BoostManager()
    return _boost_manager
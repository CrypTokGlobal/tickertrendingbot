import asyncio
import logging
import time
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TokenMonitor:
    def __init__(self, bot):
        self.bot = bot
        self.tracked_tokens = {}  # {token_address_chat_id: {token_info}}
        self.monitoring_tasks = {}
        self.is_running = False
        self.eth_monitor = None
        self.sol_monitor = None
        self.last_check_time = {}  # Track last check time per token_chat combo

    async def start(self):
        """Start the token monitor"""
        self.is_running = True
        logger.info("🚀 Starting Token Monitor")

        # Load tracked tokens from data manager
        await self.load_from_db()

        # Start monitoring existing tokens
        for token_key in self.tracked_tokens:
            if token_key not in self.monitoring_tasks:
                self.monitoring_tasks[token_key] = asyncio.create_task(
                    self.monitor_token(token_key)
                )

        logger.info(f"✅ Now monitoring {len(self.tracked_tokens)} tokens")

    async def shutdown(self):
        """Stop all monitoring tasks"""
        self.is_running = False
        if self.monitoring_tasks:
            logger.info(f"🛑 Stopping {len(self.monitoring_tasks)} token monitoring tasks")
            await asyncio.gather(*[task.cancel() for task in self.monitoring_tasks.values()], 
                                return_exceptions=True)
            self.monitoring_tasks = {}
        logger.info("✅ Token Monitor shutdown complete")

    async def load_from_db(self):
        """Load tracked tokens from data manager"""
        try:
            from data_manager import get_data_manager
            dm = get_data_manager()

            if "tracked_tokens" in dm.data:
                for token_info in dm.data["tracked_tokens"]:
                    address = token_info.get("address", "").lower()
                    chat_id = token_info.get("chat_id")
                    network = token_info.get("network", "").lower()

                    if address and chat_id and network in ["ethereum", "solana"]:
                        token_key = f"{address}_{chat_id}"
                        self.tracked_tokens[token_key] = token_info

            logger.info(f"📋 Loaded {len(self.tracked_tokens)} tokens from data manager")
        except Exception as e:
            logger.error(f"❌ Error loading tokens from data manager: {e}")

    async def save_group_tokens(self):
        """Save tracked tokens to data manager"""
        try:
            from data_manager import get_data_manager
            dm = get_data_manager()

            # Update tracked_tokens in data manager
            dm.data["tracked_tokens"] = list(self.tracked_tokens.values())
            dm.save()

            logger.info(f"💾 Saved {len(self.tracked_tokens)} tokens to persistent storage")
        except Exception as e:
            logger.error(f"❌ Error saving to persistent storage: {e}")

    async def add_token(self, token_info):
        """Add a token to be monitored"""
        if not token_info or "address" not in token_info or "chat_id" not in token_info:
            logger.error("❌ Invalid token_info provided")
            return False

        address = token_info["address"].lower()
        chat_id = token_info["chat_id"]
        token_key = f"{address}_{chat_id}"

        # Add to tracked tokens
        self.tracked_tokens[token_key] = token_info

        # Start monitoring if not already running
        if token_key not in self.monitoring_tasks:
            self.monitoring_tasks[token_key] = asyncio.create_task(
                self.monitor_token(token_key)
            )

        # Save to persistent storage
        await self.save_group_tokens()

        logger.info(f"✅ Added token {token_info.get('symbol')} ({address}) for chat {chat_id}")
        return True

    async def remove_token(self, address, chat_id):
        """Remove a token from monitoring"""
        address = address.lower()
        token_key = f"{address}_{chat_id}"

        if token_key in self.tracked_tokens:
            del self.tracked_tokens[token_key]

            # Cancel monitoring task
            if token_key in self.monitoring_tasks:
                self.monitoring_tasks[token_key].cancel()
                del self.monitoring_tasks[token_key]

            # Save to persistent storage
            await self.save_group_tokens()

            logger.info(f"🛑 Removed token {address} for chat {chat_id}")
            return True

        return False

    def get_token_by_address(self, chat_id, address):
        """Get token info by address and chat_id"""
        address = address.lower()
        token_key = f"{address}_{chat_id}"

        return self.tracked_tokens.get(token_key)

    def get_tokens_by_chat_id(self, chat_id):
        """Get all tokens tracked for a specific chat_id"""
        chat_id_str = str(chat_id)
        return [token for key, token in self.tracked_tokens.items() if str(token.get("chat_id")) == chat_id_str]

    def get_tokens_by_network(self, network):
        """Get all tokens for a specific network"""
        network = network.lower()
        return [token for token in self.tracked_tokens.values() if token.get("network", "").lower() == network]

    def list_tracked(self):
        """Return a list of all tracked token keys for debugging"""
        return list(self.tracked_tokens.keys())

    async def restart_tracking(self, address, network, chat_id):
        """Restart monitoring for a specific token"""
        address = address.lower()
        token_key = f"{address}_{chat_id}"

        # Cancel existing task if running
        if token_key in self.monitoring_tasks:
            self.monitoring_tasks[token_key].cancel()
            del self.monitoring_tasks[token_key]

        # Start new monitoring task
        if token_key in self.tracked_tokens:
            self.monitoring_tasks[token_key] = asyncio.create_task(
                self.monitor_token(token_key)
            )
            logger.info(f"🔄 Restarted monitoring for {address} on {network} in chat {chat_id}")
            return True
        return False

    async def monitor_token(self, token_key):
        """Monitor a specific token"""
        if token_key not in self.tracked_tokens:
            logger.error(f"❌ Token {token_key} not found in tracked_tokens")
            return

        token_info = self.tracked_tokens[token_key]
        address = token_info.get("address", "").lower()
        network = token_info.get("network", "").lower()
        chat_id = token_info.get("chat_id")
        name = token_info.get("name", "Unknown")
        symbol = token_info.get("symbol", "???")

        logger.info(f"🔍 Starting to monitor {symbol} ({address}) on {network}")

        # Initialize monitor instances as needed
        if network == "ethereum":
            from eth_monitor import get_instance as get_eth_monitor

            if not self.eth_monitor:
                self.eth_monitor = get_eth_monitor(self.bot)

            # Add to eth_monitor's tracked contracts if not already there
            if address not in self.eth_monitor.tracked_contracts:
                self.eth_monitor.track_contract(
                    address=address,
                    name=name,
                    symbol=symbol,
                    chat_id=token_info.get("chat_id"),
                    min_usd=token_info.get("min_volume_usd", 0)
                )

        elif network == "solana":
            # Get solana monitor from the main module, avoiding circular imports
            if not self.sol_monitor:
                try:
                    # Try to get from main first
                    import sys
                    if 'main' in sys.modules:
                        from main import sol_monitor
                        self.sol_monitor = sol_monitor
                    else:
                        # Fall back to creating a new instance if needed
                        from solana_monitor import SolanaMonitor
                        self.sol_monitor = SolanaMonitor(self.bot)
                except Exception as e:
                    logger.error(f"❌ Error getting Solana monitor: {e}")

            # Ensure sol_monitor exists
            if not self.sol_monitor:
                logger.warning(f"⚠️ Solana monitor not initialized, can't monitor {symbol}")

        else:
            logger.warning(f"⚠️ Unsupported network {network} for token {symbol}")
            return

        # Initialize last check time for this token-chat combination
        self.last_check_time[token_key] = datetime.now()

        # Main monitoring loop
        check_interval = 30  # seconds
        adaptive_interval = True

        try:
            while self.is_running:
                try:
                    if network == "ethereum" and self.eth_monitor:
                        # Ethereum tokens are monitored centrally by eth_monitor
                        # Just verify the token is being tracked
                        if address not in self.eth_monitor.tracked_contracts:
                            logger.warning(f"⚠️ Token {symbol} ({address}) not in eth_monitor.tracked_contracts, re-adding")
                            self.eth_monitor.track_contract(
                                address=address,
                                name=name,
                                symbol=symbol,
                                chat_id=token_info.get("chat_id"),
                                min_usd=token_info.get("min_volume_usd", 0)
                            )

                        # Check token activity if implemented
                        if hasattr(self.eth_monitor, 'check_token_activity'):
                            await self.eth_monitor.check_token_activity(address, token_info)

                    elif network == "solana" and self.sol_monitor:
                        # For Solana, we need to actively check each token
                        await self.sol_monitor.check_token_activity(address, token_info)

                    # Update last check time
                    self.last_check_time[token_key] = datetime.now()

                    # Adaptive sleep if configured
                    if adaptive_interval:
                        # Shorter interval during active hours, longer during quiet times
                        hour = datetime.now().hour
                        if 9 <= hour <= 24:  # More active hours
                            check_interval = 15
                        else:
                            check_interval = 30

                except Exception as e:
                    logger.error(f"❌ Error monitoring {symbol} ({address}): {e}")

                # Sleep before next check
                await asyncio.sleep(check_interval)

        except asyncio.CancelledError:
            logger.info(f"🛑 Stopped monitoring {symbol} ({address})")

        except Exception as e:
            logger.error(f"❌ Unexpected error monitoring {symbol} ({address}): {e}")

# Singleton instance
_instance = None

def get_instance(bot=None):
    global _instance
    if _instance is None and bot is not None:
        _instance = TokenMonitor(bot)
    return _instance
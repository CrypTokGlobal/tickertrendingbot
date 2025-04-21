import asyncio
import logging
import json
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/tokens"
PUMPFUN_API_URL = "https://api.pump.fun/pump"
DEX_URL_BASE = "https://dexscreener.com/solana"
PUMPFUN_URL_BASE = "https://pump.fun/token"
SOLSCAN_TX_URL = "https://solscan.io/tx"

class SolanaMonitor:
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.tokens = []
        self.running = True
        self.last_processed_txs = {}
        self.solana_tokens_to_track = {}  # Initialize properly

    async def start(self):
        import aiohttp
        self.session = aiohttp.ClientSession()
        while self.running:
            try:
                await self.monitor_tokens()
                await asyncio.sleep(15)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)

    async def monitor_tokens(self):
        for token in self.tokens:
            address = token.get("address")
            token_name = token.get("name")

            # First try pump.fun API for any contract deployed there
            pump_data = await self.fetch_pumpfun_data(address)
            if pump_data and len(pump_data.get("swaps", [])) > 0:
                await self.process_pumpfun_buys(token, pump_data)

            # Also check dexscreener as fallback
            dex_data = await self.fetch_dexscreener_data(address)
            if dex_data:
                await self.process_dexscreener_buys(token, dex_data)

    async def fetch_pumpfun_data(self, address):
        try:
            url = f"{PUMPFUN_API_URL}/{address}/swaps"
            async with self.session.get(url) as res:
                if res.status == 200:
                    return await res.json()
                if res.status != 404:  # Log only if it's not a 404 (token not on pump.fun)
                    logger.warning(f"Pump.fun API fetch failed for {address}: {res.status}")
        except Exception as e:
            logger.error(f"Pump.fun fetch error for {address}: {e}")
        return None

    async def fetch_dexscreener_data(self, address):
        try:
            async with self.session.get(f"{DEXSCREENER_URL}/{address}") as res:
                if res.status == 200:
                    return await res.json()
                logger.warning(f"DEXScreener fetch failed: {res.status}")
        except Exception as e:
            logger.error(f"Fetch error for {address}: {e}")
        return {}

    async def process_pumpfun_buys(self, token, data):
        address = token.get("address")

        # Initialize tracking for this token if not already done
        if address not in self.last_processed_txs:
            self.last_processed_txs[address] = set()

        # Get recent swaps (buys)
        swaps = data.get("swaps", [])

        # Limit the number of alerts we process at once to prevent flood controls
        max_alerts_per_cycle = 3
        alerts_sent = 0

        for swap in swaps:
            # Rate limit the number of alerts we process in a single cycle
            if alerts_sent >= max_alerts_per_cycle:
                logger.info(f"Rate limiting alerts for {token.get('symbol', 'Unknown')} - max {max_alerts_per_cycle} per cycle")
                break

            tx_hash = swap.get("txId")
            # Skip if we've already processed this transaction
            if tx_hash in self.last_processed_txs[address]:
                continue

            # Check if it's a buy (tokenIn is SOL)
            token_in = swap.get("tokenIn", {}).get("ticker", "").lower()
            if token_in == "sol":
                amount_sol = float(swap.get("tokenIn", {}).get("amount", 0))
                amount_usd = amount_sol * float(swap.get("tokenIn", {}).get("usdPrice", 0))
                dex_name = "Pump.fun"

                # Rate limit alerts to prevent flooding
                from utils import should_send_alert

                # Check if we should send an alert for this token
                if should_send_alert(address):
                    # Send the alert
                    await send_alert(
                        bot=self.bot,
                        token_info=token,
                        chain="solana",
                        value_token=amount_sol,
                        value_usd=amount_usd,
                        tx_hash=tx_hash,
                        dex_name=dex_name
                    )
                    logger.info(f"✅ Alert sent for {token.get('symbol', '???')} - {amount_sol} SOL (${amount_usd:.2f})")
                else:
                    logger.info(f"⏱️ Rate limited alert for {token.get('symbol', '???')} - {amount_sol} SOL")

                # Add to processed transactions
                self.last_processed_txs[address].add(tx_hash)

                # Keep processed tx list manageable
                if len(self.last_processed_txs[address]) > 100:
                    self.last_processed_txs[address] = set(list(self.last_processed_txs[address])[-50:])

                # Send alert with longer delay between messages
                await self.send_pump_alert(token, tx_hash, amount_sol, amount_usd, dex_name)
                alerts_sent += 1
                # Add extra delay between alerts to avoid Telegram rate limits
                await asyncio.sleep(1.5)  # This is already using asyncio.sleep correctly

    async def process_dexscreener_buys(self, token, data):
        pairs = data.get("pairs", [])
        if pairs is None:
            pairs = []

        sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
        for pair in sol_pairs:
            tx = pair.get("txns", {}).get("m5", {})
            if tx and tx.get("buys", 0) > 0:
                await self.send_dex_alert(token, pair)

    async def send_pump_alert(self, token, tx_hash, amount_sol, amount_usd, dex_name):
        from utils import send_alert

        success = await send_alert(
            bot=self.bot,
            token_info=token,
            chain="solana",
            value_token=amount_sol,
            value_usd=amount_usd,
            tx_hash=tx_hash,
            dex_name=dex_name
        )

        if success:
            logger.info(f"✅ Pump.fun alert sent for {token.get('symbol', '???')}")
        else:
            logger.error(f"Failed to send Pump.fun alert for {token.get('symbol', '???')}")

    async def send_dex_alert(self, token, pair):
        from utils import send_alert

        tx_hash = pair.get("pairCreatedAt", "UNKNOWN")
        dex = pair.get("dexId", "DEX")
        price = float(pair.get("priceUsd", 0))
        sol = float(pair.get("priceNative", 0))

        success = await send_alert(
            bot=self.bot,
            token_info=token,
            chain="solana",
            value_token=sol,
            value_usd=price,
            tx_hash=tx_hash,
            dex_name=dex
        )

        if success:
            logger.info(f"✅ DEX alert sent for {token.get('symbol', '???')}")
        else:
            logger.error(f"Failed to send DEX alert for {token.get('symbol', '???')}")

    async def shutdown(self):
        self.running = False
        # Clean up any reference to PUMP token first
        self.remove_token("C3DwDjT17gDvvCYC2nsdGHxDHVmQRdhKfpAdqQ29pump")
        # Also clean lowercase version
        self.remove_token("c3dwdjt17gdvvcyc2nsdghxdhvmqrdhkfpadqq29pump")

        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Session closed")

    def add_token(self, address, name, symbol, group_id):
        # Normalize address to lowercase
        address = address.lower()

        # Check if token is already being tracked
        for token in self.tokens:
            if token["address"].lower() == address and token["group_id"] == group_id:
                # Update existing token info
                token["name"] = name
                token["symbol"] = symbol
                logger.info(f"Updated existing token: {symbol} ({address})")
                return

        # Add new token
        self.tokens.append({
            "address": address,
            "name": name,
            "symbol": symbol,
            "group_id": group_id
        })
        logger.info(f"Added new token to monitor: {symbol} ({address})")

    def remove_token(self, address, group_id=None):
        """Remove a token from active monitoring"""
        # Normalize address to lowercase
        address = address.lower()

        # Keep track of how many tokens were removed
        initial_count = len(self.tokens)

        # Remove from tokens list
        if group_id:
            # Remove for specific group
            self.tokens = [t for t in self.tokens 
                          if not (t["address"].lower() == address and t["group_id"] == group_id)]
        else:
            # Remove for all groups
            self.tokens = [t for t in self.tokens if t["address"].lower() != address]

        # Also clear any cached transaction data
        if address in self.last_processed_txs:
            del self.last_processed_txs[address]

        # Make sure token is not in solana_tokens_to_track (if the attribute exists)
        if hasattr(self, 'solana_tokens_to_track') and address in self.solana_tokens_to_track:
            del self.solana_tokens_to_track[address]
            logger.info(f"🔕 Removed token {address} from solana_tokens_to_track dictionary")

        # Also check for address with added prefix (important cleanup)
        if hasattr(self, 'solana_tokens_to_track'):
            # Sometimes tokens may be stored with different formats
            alternate_keys = [k for k in self.solana_tokens_to_track.keys() 
                             if k.lower().endswith(address.lower())]
            for key in alternate_keys:
                del self.solana_tokens_to_track[key]
                logger.info(f"🔕 Removed alternate format token {key} from tracking")

        # Log the result
        removed_count = initial_count - len(self.tokens)
        if removed_count > 0:
            logger.info(f"🔕 Removed token {address} from active monitoring (removed {removed_count} instances)")
            return True
        else:
            logger.warning(f"⚠️ Token {address} not found in active monitoring")
            return False

    def get_tracked_addresses(self):
        """Return a list of all tracked addresses"""
        return [t["address"].lower() for t in self.tokens]

    async def test_dexscreener_integration(self, token_address):
        """Test method to verify DexScreener integration for a specific token"""
        try:
            # Create a demo token for testing
            test_token = {
                "address": token_address,
                "name": "Test Token",
                "symbol": "TEST",
                "group_id": "-1001234567890"  # Replace with actual chat ID
            }

            # Fetch data
            data = await self.fetch_dexscreener_data(token_address)
            if not data or not data.get("pairs"):
                logger.warning(f"No pairs found for {token_address}")
                return False

            # Simulate an alert
            await self.process_dexscreener_buys(test_token, data)
            return True
        except Exception as e:
            logger.error(f"Test failed: {e}")
            return False

    async def add_new_token(self, chat_id, token_address, token_name, token_symbol, min_volume=0.0):
        """Add a new token to monitoring and verify its data"""
        logger.info(f"Adding new token: {token_symbol} ({token_address}) for chat {chat_id}")

        # Add the token
        self.add_token(token_address, token_name, token_symbol, chat_id)

        # Try to fetch some initial data
        dex_data = await self.fetch_dexscreener_data(token_address)
        pump_data = await self.fetch_pumpfun_data(token_address)

        if (dex_data and dex_data.get("pairs")) or (pump_data and pump_data.get("swaps")):
            logger.info(f"Successfully verified data for {token_symbol}")
            return True
        else:
            logger.warning(f"Added token {token_symbol} but could not verify data")
            return False

    async def check_token_activity(self, token_address, token_info):
        """Check recent activity for a token"""
        logger.info(f"🔍 Checking activity for Solana token: {token_info.get('symbol')} ({token_address})")

        # Fetch data from both sources
        try:
            dex_data = await self.fetch_dexscreener_data(token_address)
            logger.info(f"📊 Received data for token {token_address}: {len(dex_data.get('pairs', []))} pairs")
        except Exception as e:
            logger.error(f"Error checking DEXScreener for {token_address}: {e}")

        try:
            pump_data = await self.fetch_pumpfun_data(token_address)
            if pump_data:
                logger.info(f"📊 Received Pump.fun data for token {token_address}: {len(pump_data.get('swaps', []))} swaps")
        except Exception as e:
            logger.error(f"Error checking Pump.fun for {token_address}: {e}")

        return True

async def send_alert(bot, token_info, chain, value_token, value_usd, tx_hash, dex_name):
    from utils import generate_alert_message, get_buttons
    chat_id = token_info.get("group_id")
    token_address = token_info.get("address")
    alert_message = generate_alert_message(token_info, chain, value_token, value_usd, tx_hash, dex_name)
    buttons = get_buttons(token_address)

    # Update dashboard statistics
    try:
        from dashboard import increment_alerts, set_last_alert, add_tracked_contract
        increment_alerts()
        set_last_alert(alert_message)
        add_tracked_contract(token_address, "solana")
    except ImportError:
        logger.warning("Dashboard module not available for updating stats")

    # Get token customization to check for media
    from customization_handler import apply_token_customization
    alert_message, media = apply_token_customization(token_address, alert_message)

    # Send alert with media if available
    if media and media.get("type") == "photo":
        await bot.send_photo(
            chat_id=chat_id,
            photo=media["file_id"],
            caption=alert_message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif media and (media.get("type") == "animation" or media.get("type") == "document"):
        await bot.send_animation(
            chat_id=chat_id,
            animation=media["file_id"],
            caption=alert_message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif media and media.get("type") == "sticker":
        # First send the sticker
        await bot.send_sticker(
            chat_id=chat_id,
            sticker=media["file_id"]
        )
        # Then send the alert
        await bot.send_message(
            chat_id=chat_id,
            text=alert_message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        # Send regular message if no media
        await bot.send_message(
            chat_id=chat_id,
            text=alert_message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    return True

# Global instance
sol_monitor_instance = None

def get_instance(bot=None):
    global sol_monitor_instance
    if sol_monitor_instance is None:
        sol_monitor_instance = SolanaMonitor(bot)
    elif bot is not None:
        sol_monitor_instance.bot = bot
    return sol_monitor_instance

async def start_solana_monitor(application):
    """Start the Solana monitoring task"""
    monitor = get_instance(application.bot)
    logger.info("🚀 Starting Solana monitoring task...")
    monitor_task = asyncio.create_task(monitor.start())
    return monitor_task
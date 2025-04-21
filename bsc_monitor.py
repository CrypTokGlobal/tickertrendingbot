import os
import time
import logging
import json
import asyncio
from datetime import datetime
from web3 import Web3
from web3.exceptions import TransactionNotFound
from dotenv import load_dotenv
from data_manager import get_data_manager
from telegram.constants import ParseMode
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

class BNBMonitor:
    _instance = None

    @classmethod
    def get_instance(cls, bot=None):
        if cls._instance is None:
            cls._instance = cls(bot)
        elif bot is not None:
            cls._instance.bot = bot
        return cls._instance

    def __init__(self, bot):
        self.bot = bot
        self.tracked_tokens = {}
        self.data_manager = get_data_manager()
        logger.info("BNB Monitor initialized")
        #Added this for web3 init consistency with original code
        from config import BSC_NODE_URL, BSCSCAN_API_KEY
        default_bsc_node = "https://bsc-dataseed1.binance.org"
        node_url = BSC_NODE_URL if 'BSC_NODE_URL' in locals() else default_bsc_node
        try:
            logger.info("Attempting to connect to BSC provider")
            self.web3 = Web3(Web3.HTTPProvider(node_url))
            self.last_checked_block = self.web3.eth.block_number
            logger.info(f"Connected to BSC network - latest block: {self.last_checked_block}")
        except Exception as e:
            logger.warning(f"Could not connect to primary BSC provider: {e}")
            # Try fallback
            try:
                fallback_url = "https://bsc-dataseed2.binance.org"
                logger.info(f"Trying fallback BSC provider: {fallback_url}")
                self.web3 = Web3(Web3.HTTPProvider(fallback_url))
                self.last_checked_block = self.web3.eth.block_number
                logger.info(f"Connected to fallback BSC network - latest block: {self.last_checked_block}")
            except Exception as e2:
                logger.error(f"Could not connect to fallback BSC provider: {e2}")
                # Initialize with defaults
                self.web3 = None
                self.last_checked_block = 0

    async def start_tracking(self, token_address, token_name, token_symbol, chat_id):
        """Start tracking a token"""
        normalized_address = token_address.lower()

        # Add to tracked tokens
        self.tracked_tokens[normalized_address] = {
            "address": normalized_address,
            "name": token_name,
            "symbol": token_symbol,
            "chat_id": chat_id,
            "network": "bnb"
        }

        # Also add to data_manager for persistence

        # Initialize tracked_tokens if not exists
        if "tracked_tokens" not in self.data_manager.data:
            self.data_manager.data["tracked_tokens"] = []

        # Check if already tracking this token in this chat
        for token in self.data_manager.data["tracked_tokens"]:
            if (token.get("address", "").lower() == normalized_address and
                str(token.get("chat_id")) == str(chat_id) and
                token.get("network") == "bnb"):
                # Already tracking, update info
                token["name"] = token_name
                token["symbol"] = token_symbol
                self.data_manager._save_data()
                logger.info(f"✅ Updated existing BNB token {token_symbol} ({normalized_address})")
                return True

        # Add new token to track
        self.data_manager.data["tracked_tokens"].append({
            "address": normalized_address,
            "name": token_name,
            "symbol": token_symbol,
            "chat_id": chat_id,
            "network": "bnb"
        })
        self.data_manager._save_data()

        logger.info(f"✅ Started tracking new BNB token {token_symbol} ({normalized_address})")
        return True

    async def send_alert(self, chat_id, token_address, tx_hash, value_bnb, value_usd=None):
        """Send a BNB token alert"""
        try:
            from utils import build_alert_message, build_inline_buttons
            from customization_handler import apply_token_customization

            # Get token info from tracked tokens
            normalized_address = token_address.lower()
            token_info = self.tracked_tokens.get(normalized_address, None)

            if not token_info:
                # Try to get from data_manager
                for token in self.data_manager.data.get("tracked_tokens", []):
                    if token.get("address", "").lower() == normalized_address and token.get("network") == "bnb":
                        token_info = token
                        break

            if not token_info:
                logger.warning(f"Cannot find token info for BNB alert: {token_address}")
                # Use minimal info
                token_info = {
                    "address": normalized_address,
                    "name": "Unknown",
                    "symbol": "BNB",
                    "network": "bnb"
                }

            # Ensure transaction hash is properly formatted
            if tx_hash.startswith('0x'):
                clean_hash = tx_hash
            else:
                clean_hash = '0x' + tx_hash

            # Build URLs
            tx_url = f"https://bscscan.com/tx/{clean_hash}"
            chart_url = f"https://dexscreener.com/bsc/{normalized_address}"
            swap_url = f"https://pancakeswap.finance/swap?outputCurrency={normalized_address}"

            # Calculate USD value if not provided
            if value_usd is None:
                # Placeholder BNB price
                bnb_price_usd = 500
                value_usd = value_bnb * bnb_price_usd

            # Build alert message
            message = await build_alert_message(
                token_info=token_info,
                symbol=token_info.get("symbol", "BNB"),
                name=token_info.get("name", "Unknown"),
                value_crypto=value_bnb,
                value_usd=value_usd,
                tx_hash=clean_hash,
                dex_name="PancakeSwap",
                explorer_url=tx_url,
                chart_url=chart_url,
                swap_url=swap_url,
                chain="bnb"
            )

            # Apply token customization
            message, media = apply_token_customization(normalized_address, message)

            # Build buttons
            keyboard = build_inline_buttons(
                chart_url=chart_url,
                tx_url=tx_url,
                swap_url=swap_url,
                token_info=token_info,
                bot_username=self.bot.username
            )

            # Send alert with appropriate media
            if media and media.get("type") == "photo":
                await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=media["file_id"],
                    caption=message,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            elif media and (media.get("type") == "animation" or media.get("type") == "document"):
                await self.bot.send_animation(
                    chat_id=chat_id,
                    animation=media["file_id"],
                    caption=message,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            elif media and media.get("type") == "sticker":
                # First send the sticker
                await self.bot.send_sticker(
                    chat_id=chat_id,
                    sticker=media["file_id"]
                )
                # Then send the alert
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                # Send regular message if no media
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )

            logger.info(f"✅ BNB alert sent for {token_info.get('symbol')} ({token_address})")
            return True
        except Exception as e:
            logger.error(f"Failed to send BNB alert: {e}")
            return False


    def remove_token(self, address, chat_id=None):
        """Remove a token from active tracking"""
        try:
            # Normalize address
            normalized_address = address.lower()

            # Track removed count
            removed_count = 0

            # Get the tracked tokens list
            tracked_tokens = self.data_manager.data.get("tracked_tokens", [])

            # Create a new list without the specified token
            if chat_id:
                # Remove for specific chat
                self.data_manager.data["tracked_tokens"] = [
                    t for t in tracked_tokens 
                    if not (t.get("address", "").lower() == normalized_address and 
                           str(t.get("chat_id")) == str(chat_id) and
                           t.get("network", "").lower() == "bnb")
                ]
            else:
                # Remove for all chats
                self.data_manager.data["tracked_tokens"] = [
                    t for t in tracked_tokens
                    if not (t.get("address", "").lower() == normalized_address and
                           t.get("network", "").lower() == "bnb")
                ]

            # Calculate removed count
            removed_count = len(tracked_tokens) - len(self.data_manager.data["tracked_tokens"])

            # Save the changes
            self.data_manager._save_data()

            # Clear any additional in-memory references that might be tracking this token
            if hasattr(self, 'active_tokens'):
                self.active_tokens = [t for t in getattr(self, 'active_tokens', [])
                                    if t.get("address", "").lower() != normalized_address]

            if removed_count > 0:
                logger.info(f"🔕 Removed {removed_count} instances of BNB token {address} from active monitoring")
                return True
            else:
                logger.warning(f"⚠️ BNB token {address} not found in active monitoring")
                return False

        except Exception as e:
            logger.error(f"Error removing BNB token {address}: {e}")
            return False

    def get_tracked_addresses(self):
        """Return a list of all tracked addresses"""
        tracked_tokens = self.data_manager.data.get("tracked_tokens", [])
        return [t.get("address", "").lower() for t in tracked_tokens 
                if t.get("network", "").lower() == "bnb"]

    async def monitor_binance(self):
        """Main monitoring loop for BSC"""
        while True:
            try:
                # Skip monitoring if Web3 is not configured
                if not self.web3:
                    logger.info("BNB monitoring is disabled. Sleeping...")
                    await asyncio.sleep(60)
                    continue

                current_block = self.web3.eth.block_number
                if self.last_checked_block == 0:
                    # First run - just set the current block without processing history
                    self.last_checked_block = current_block
                    logger.info(f"Starting BNB monitoring from block {current_block}")
                else:
                    # Process new blocks
                    for block_number in range(self.last_checked_block + 1, current_block + 1):
                        block = self.web3.eth.get_block(block_number, full_transactions=True)
                        for tx in block.transactions:
                            await self.process_transaction(tx)

                    # Update last checked block
                    if current_block > self.last_checked_block:
                        self.last_checked_block = current_block
                        logger.info(f"Processed BNB blocks up to {current_block}")
            except Exception as e:
                logger.error(f"BNB monitoring error: {e}")

            # Sleep before next check
            await asyncio.sleep(10)

    async def process_transaction(self, tx):
        """Process a single BSC transaction"""
        to_address = tx.to.lower() if tx.to else None
        tracked_tokens = self.data_manager.data.get("tracked_tokens", [])

        for token in tracked_tokens:
            if token.get("network") == "bnb" and token.get("address", "").lower() == to_address:
                # Verify token has a chat_id
                if "chat_id" not in token:
                    logger.warning(f"Token {token.get('symbol', 'unknown')} ({to_address}) has no chat_id, skipping alert")
                    continue

                # Format transaction hash correctly
                tx_hash_str = tx.hash.hex() if hasattr(tx.hash, 'hex') else str(tx.hash)

                # Ensure hash doesn't start with '0x' twice
                if tx_hash_str.startswith('0x'):
                    clean_hash = tx_hash_str
                else:
                    clean_hash = '0x' + tx_hash_str

                # Try to identify the DEX used
                from utils import decode_method
                dex_name = "PancakeSwap"  # Default for BSC

                # Check if it's a function call we can identify
                if hasattr(tx, 'input') and tx.input and len(tx.input) >= 10:
                    method_id = tx.input[:10]
                    method_name = decode_method(method_id)

                    # Update DEX name based on common BSC DEX routers
                    if to_address == "0x10ed43c718714eb63d5aa57b78b54704e256024e":
                        dex_name = "PancakeSwap V2"
                    elif to_address == "0xcf0febd3f17cef5b47b0cd257acf6025c5bff3b7":
                        dex_name = "ApeSwap"
                    elif to_address == "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506":
                        dex_name = "SushiSwap"

                    logger.info(f"Detected method: {method_name} on {dex_name}")

                try:
                    await self.send_alert(
                        chat_id=token["chat_id"],
                        token_address=to_address,
                        tx_hash=clean_hash,
                        value_bnb=tx.value / 1e18,

                    )
                except Exception as e:
                    logger.error(f"Error handling BNB transaction {clean_hash}: {e}")

async def handle_confirmation_bnb(bot, tx_hash, bnb_amount, matched_token, dex_name="PancakeSwap"):
    """Handle a confirmed BNB transaction"""
    try:
        logger.info(f"🟡 DETECTED: {matched_token.get('symbol', 'UNKNOWN')} token in transaction {tx_hash}")

        # Check if chat_id exists
        if "chat_id" not in matched_token:
            logger.error(f"Missing chat_id in token data: {matched_token}")
            return False

        # Estimate USD value - in production would use a price API
        bnb_price_usd = 500  # placeholder for BNB price
        usd_value = bnb_amount * bnb_price_usd

        #This function is now redundant, replaced by the new send_alert method in BNBMonitor
        # await send_bnb_alert(
        #     bot=bot,
        #     chat_id=matched_token["chat_id"],
        #     symbol=matched_token.get("symbol", "UNKNOWN"),
        #     amount=bnb_amount,
        #     tx_hash=tx_hash,
        #     token_info=matched_token,
        #     usd_value=usd_value,
        #     dex_name=dex_name
        # )
        monitor = BNBMonitor.get_instance(bot)
        await monitor.send_alert(matched_token["chat_id"], matched_token["address"], tx_hash, bnb_amount, usd_value)
        return True
    except Exception as e:
        logger.error(f"Error in handle_confirmation_bnb: {e}")
        return False

async def send_bnb_alert(bot, chat_id, symbol, amount, tx_hash, token_info=None, usd_value=None, dex_name="PancakeSwap"):
    """Send an alert for a BNB transaction"""
    try:
        from utils import build_alert_message, build_inline_buttons
        from customization_handler import apply_token_customization

        # Ensure transaction hash is properly formatted for URL
        if tx_hash.startswith('0x'):
            clean_hash = tx_hash
        else:
            clean_hash = '0x' + tx_hash

        # If we don't have token_info, create minimal version
        if not token_info:
            token_info = {
                "address": clean_hash,
                "symbol": symbol,
                "name": symbol,
                "chain": "bnb"
            }

        # Default value in USD if not provided
        if not usd_value:
            # Rough estimate of BNB value in USD
            bnb_price_usd = 500  # placeholder
            usd_value = amount * bnb_price_usd

        # Gather all necessary URLs and data
        token_address = token_info.get("address", "")
        token_name = token_info.get("name", symbol)
        token_symbol = token_info.get("symbol", symbol)

        # Build URLs
        tx_url = f"https://bscscan.com/tx/{clean_hash}"
        chart_url = f"https://dexscreener.com/bsc/{token_address}"
        swap_url = f"https://pancakeswap.finance/swap?outputCurrency={token_address}"

        # Use the same alert format as other chains for consistency
        message = await build_alert_message(
            token_info=token_info,
            symbol=token_symbol,
            name=token_name,
            value_crypto=amount,
            value_usd=usd_value,
            tx_hash=clean_hash,
            dex=dex_name,
            explorer_url=tx_url,
            chart_url=chart_url,
            swap_url=swap_url,
            chain="bnb"
        )

        # Get token customization to check for media
        message, media = apply_token_customization(token_address, message)

        # Use the same button layout as other chains for consistency
        keyboard = build_inline_buttons(
            chart_url=chart_url,
            tx_url=tx_url,
            swap_url=swap_url,
            token_info=token_info,
            bot_username=bot.username
        )

        # Send alert with media if available
        if media and media.get("type") == "photo":
            await bot.send_photo(
                chat_id=chat_id,
                photo=media["file_id"],
                caption=message,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        elif media and (media.get("type") == "animation" or media.get("type") == "document"):
            await bot.send_animation(
                chat_id=chat_id,
                animation=media["file_id"],
                caption=message,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=True
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
                text=message,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        else:
            # Send regular message if no media
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        # Add delay to reduce risk of hitting Telegram rate limits
        await asyncio.sleep(0.5)
        logger.info(f"✅ Sent BNB alert for {symbol} transaction {clean_hash}")
        return True
    except Exception as send_error:
        logger.error(f"Failed to send BNB alert for {symbol}: {send_error}")
        return False
def get_instance(bot=None):
    return BNBMonitor.get_instance(bot)

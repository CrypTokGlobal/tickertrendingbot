import logging
import asyncio
from web3 import Web3
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from config import TELEGRAM_BOT_TOKEN

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Store chat IDs for notifications
TELEGRAM_CHAT_IDS = set()

# Initialize Web3 connection
try:
    from config import INFURA_API_KEY
    w3 = Web3(Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{INFURA_API_KEY}"))
except:
    # Fallback to public node
    w3 = Web3(Web3.HTTPProvider("https://eth.public-rpc.com"))

# Global application reference
application = None

async def send_alert(msg, tx_url=None, chart_url=None):
    logger.info(f"🚨 ALERT: {msg}")

    # Ensure there are chat IDs to send to
    if not TELEGRAM_CHAT_IDS:
        logger.warning("No chat IDs available to send alerts to!")
        # Add default chat ID if available
        try:
            from config import ADMIN_CHAT_ID
            if ADMIN_CHAT_ID:
                TELEGRAM_CHAT_IDS.add(ADMIN_CHAT_ID)
                logger.info(f"Added default admin chat ID: {ADMIN_CHAT_ID}")
        except Exception as e:
            logger.error(f"Could not add default chat ID: {e}")

    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            # Build the full message with all links
            full_msg = msg

            if tx_url:
                full_msg += f"\n\n🔗 View TX: {tx_url}"
            if chart_url:
                full_msg += f"\n📊 Chart: {chart_url}"

            # Create boost button with clearer label
            boost_button = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 BOOST? (Promote your Telegram link)", url="https://tickertrending.com")]
            ])

            # Send with retry mechanism
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    await application.bot.send_message(
                        chat_id=chat_id, 
                        text=full_msg, 
                        reply_markup=boost_button,
                        disable_web_page_preview=True  # Disable preview for cleaner messages
                    )
                    logger.info(f"✅ Alert sent to {chat_id}")
                    break
                except Exception as retry_error:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"Retry {retry_count}/{max_retries} failed: {retry_error}")
                        await asyncio.sleep(1)  # Wait before retrying
                    else:
                        logger.error(f"Failed to send alert to {chat_id} after {max_retries} attempts: {retry_error}")
        except Exception as e:
            logger.error(f"Error sending alert to {chat_id}: {e}")

def set_application(app):
    """Set the global application reference for sending messages"""
    global application
    application = app
    logger.info("Application reference set in dual_chain_tracker")

def register_chat_id(chat_id):
    """Register a chat ID for alerts"""
    TELEGRAM_CHAT_IDS.add(str(chat_id))
    logger.info(f"Registered chat ID: {chat_id}")
    return True

def unregister_chat_id(chat_id):
    """Unregister a chat ID from alerts"""
    chat_id_str = str(chat_id)
    if chat_id_str in TELEGRAM_CHAT_IDS:
        TELEGRAM_CHAT_IDS.remove(chat_id_str)
        logger.info(f"Unregistered chat ID: {chat_id}")
        return True
    return False

def get_registered_chat_ids():
    """Get all registered chat IDs"""
    return list(TELEGRAM_CHAT_IDS)

# Import these modules here to avoid circular imports
from data_manager import add_tracked_token, remove_tracked_token, list_tracked_tokens, get_tokens_by_network

async def track_token(chat_id, chain, address, name, symbol, min_volume_usd):
    """Track a token on the specified chain"""
    chain = chain.lower()

    if chain not in ["ethereum", "eth", "solana", "sol"]:
        return False, f"Unsupported chain: {chain}. Use 'ethereum' or 'solana'."

    # Normalize chain names
    network = "ethereum" if chain in ["ethereum", "eth"] else "solana"

    # Add to tracking database
    add_tracked_token(
        chat_id=chat_id,
        address=address,
        name=name,
        symbol=symbol,
        min_volume_usd=float(min_volume_usd),
        network=network
    )

    # Register chat for alerts
    register_chat_id(chat_id)

    return True, f"Now tracking {name} ({symbol}) on {network.capitalize()} with {min_volume_usd} USD minimum volume"

async def untrack_token(chat_id, chain, address):
    """Untrack a token on the specified chain"""
    chain = chain.lower()

    if chain not in ["ethereum", "eth", "solana", "sol"]:
        return False, f"Unsupported chain: {chain}. Use 'ethereum' or 'solana'."

    # Normalize chain names
    network = "ethereum" if chain in ["ethereum", "eth"] else "solana"

    # Remove from tracking database
    success = remove_tracked_token(chat_id, address, network)
    
    # Also remove from EthMonitor if it's an ETH token
    if network == "ethereum":
        try:
            from New import EthMonitor
            eth_monitor = EthMonitor.get_instance(None)
            eth_monitor.untrack_contract(address)
            logger.info(f"Removed {address} from EthMonitor tracking")
        except Exception as e:
            logger.error(f"Error removing from EthMonitor: {e}")

    if success:
        return True, f"Successfully removed {address} from tracking on {network.capitalize()}"
    else:
        return False, f"Token {address} not found in tracking list for {network.capitalize()}"

async def list_tokens(chat_id):
    """List all tracked tokens for a chat"""
    eth_tokens = list_tracked_tokens(chat_id, "ethereum")
    sol_tokens = list_tracked_tokens(chat_id, "solana")

    if not eth_tokens and not sol_tokens:
        return "No tokens currently tracked. Use /track_chain to start tracking."

    result = []

    if eth_tokens:
        result.append("📊 <b>Ethereum Tokens:</b>")
        for i, token in enumerate(eth_tokens, 1):
            result.append(f"{i}. <b>{token.get('name', 'Unknown')}</b> ({token.get('symbol', '?')})")
            result.append(f"   Address: <code>{token.get('address', 'Unknown')}</code>")
            result.append(f"   Min Volume: ${token.get('min_volume_usd', 0)} USD")
            result.append("")

    if sol_tokens:
        result.append("🌞 <b>Solana Tokens:</b>")
        for i, token in enumerate(sol_tokens, 1):
            result.append(f"{i}. <b>{token.get('name', 'Unknown')}</b> ({token.get('symbol', '?')})")
            result.append(f"   Address: <code>{token.get('address', 'Unknown')}</code>")
            result.append(f"   Min Volume: ${token.get('min_volume_usd', 0)} USD")
            result.append("")

    return "\n".join(result)

async def start_eth_monitor():
    """Start monitoring Ethereum tokens"""
    from eth_monitor import start_monitoring
    await start_monitoring()

async def start_sol_monitor():
    """Start monitoring Solana tokens"""
    from solana_monitor import start_monitoring
    await start_monitoring()

async def test_eth_alert(chat_id):
    """Send a test Ethereum alert"""
    test_msg = "🧪 <b>TEST ETHEREUM ALERT</b>\n\n"
    test_msg += "This is a test alert for Ethereum token tracking.\n"
    test_msg += "If you see this, your Ethereum alerts are working!"

    await send_alert(test_msg, "https://etherscan.io", "https://dexscreener.com")
    return True

async def test_sol_alert(chat_id):
    """Send a test Solana alert"""
    test_msg = "🧪 <b>TEST SOLANA ALERT</b>\n\n"
    test_msg += "This is a test alert for Solana token tracking.\n"
    test_msg += "If you see this, your Solana alerts are working!"

    await send_alert(test_msg, "https://solscan.io", "https://dexscreener.com")
    return True

# Initialize monitoring tasks
async def start_monitoring():
    """Start monitoring both chains"""
    logger.info("Starting dual-chain monitoring...")

    # Start Ethereum monitoring
    eth_task = asyncio.create_task(start_eth_monitor())

    # Start Solana monitoring
    sol_task = asyncio.create_task(start_sol_monitor())

    return eth_task, sol_task


async def dual_chain_command(update, context):
    """Display dual chain options"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = [
        [InlineKeyboardButton("Track ETH Token", callback_data="track_eth")],
        [InlineKeyboardButton("Track SOL Token", callback_data="track_sol")],
        [InlineKeyboardButton("List Tracked Tokens", callback_data="list_chain")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔄 *Dual Chain Tracker*\n\n"
        "Track tokens across Ethereum and Solana from one interface.\n\n"
        "• `/track_chain eth <address> <symbol> [min_usd]` - Track Ethereum token\n"
        "• `/track_chain sol <address> <symbol> [min_usd]` - Track Solana token\n"
        "• `/untrack_chain eth|sol <address>` - Stop tracking token\n"
        "• `/list_chain` - Show all tracked tokens\n"
        "• `/test_eth` - Test Ethereum alerts\n"
        "• `/test_sol` - Test Solana alerts",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def track_chain_command(update, context):
    """Track a token on either chain"""
    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ Usage: `/track_chain <eth|sol> <address> <symbol> [min_usd]`\n\n"
            "Example ETH: `/track_chain eth 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984 UNI 10`\n"
            "Example SOL: `/track_chain sol EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v USDC 10`",
            parse_mode="Markdown"
        )
        return

    chain = context.args[0].lower()
    address = context.args[1]
    symbol = context.args[2]

    # Validate min_usd parameter
    try:
        min_usd = float(context.args[3]) if len(context.args) > 3 else 5.0
        if min_usd <= 0:
            await update.message.reply_text("⚠️ Minimum USD value must be greater than zero. Setting to default $5.0")
            min_usd = 5.0
    except ValueError:
        await update.message.reply_text("⚠️ Invalid minimum USD value. Setting to default $5.0")
        min_usd = 5.0

    # Add chat ID to notification list
    chat_id = update.effective_chat.id
    success, message = await track_token(chat_id, chain, address, symbol, symbol, min_usd)

    await update.message.reply_text(message, parse_mode="Markdown")

    if success and chain.startswith('eth'):
        chart_url = f"https://dexscreener.com/ethereum/{address}"
        keyboard = [[InlineKeyboardButton("📊 View Chart", url=chart_url)], [InlineKeyboardButton("🧪 Test Alert", callback_data="test_eth")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)
    elif success and chain.startswith('sol'):
        chart_url = f"https://dexscreener.com/solana/{address}"
        keyboard = [[InlineKeyboardButton("📊 View Chart", url=chart_url)], [InlineKeyboardButton("🧪 Test Alert", callback_data="test_sol")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)


async def untrack_chain_command(update, context):
    """Stop tracking a token"""
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: `/untrack_chain <eth|sol> <address>`", parse_mode="Markdown")
        return

    chain = context.args[0].lower()
    address = context.args[1]
    chat_id = update.effective_chat.id

    success, message = await untrack_token(chat_id, chain, address)
    await update.message.reply_text(message)

async def list_chain_command(update, context):
    """List all tracked tokens across both chains"""
    chat_id = update.effective_chat.id
    message = await list_tokens(chat_id)
    await update.message.reply_text(message, parse_mode="HTML")

async def test_eth_alert(update, context):
    """Send a test ETH alert to verify notifications are working."""
    try:
        chat_id = update.effective_chat.id
        success = await test_eth_alert(chat_id)
        if success:
            await update.message.reply_text("✅ Ethereum test alert sent successfully!")
        else:
            await update.message.reply_text("❌ Error sending test Ethereum alert")
    except Exception as e:
        logger.error(f"Error sending test ETH alert: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

async def test_sol_alert(update, context):
    """Send a test Solana alert to verify notifications are working."""
    try:
        chat_id = update.effective_chat.id
        success = await test_sol_alert(chat_id)
        if success:
            await update.message.reply_text("✅ Solana test alert sent successfully!")
        else:
            await update.message.reply_text("❌ Error sending test Solana alert")
    except Exception as e:
        logger.error(f"Error sending test SOL alert: {e}")
        await update.message.reply_text(
            f"❌ Error sending Solana test alert: {e}\n\n"
            "Please check your connection and try again."
        )

async def monitor_ethereum(bot):
    """Monitor Ethereum for transactions involving tracked tokens"""
    logger.info("🔎 Starting Ethereum monitoring...")

    # Get tracked tokens from data manager
    from data_manager import get_data_manager
    dm = get_data_manager()

    # Track last processed block
    last_block = w3.eth.block_number

    while True:
        try:
            current_block = w3.eth.block_number

            if current_block > last_block:
                logger.info(f"Processing blocks {last_block + 1} to {current_block}")

                # Get updated token list
                tracked_tokens = []
                for token in dm.data.get("tracked_tokens", []):
                    if token.get("network", "ethereum").lower() == "ethereum":
                        tracked_tokens.append(token)

                # Process each block
                for block_number in range(last_block + 1, current_block + 1):
                    # Get block with full transaction details
                    block = w3.eth.get_block(block_number, full_transactions=True)

                    # Check each transaction
                    for tx in block.transactions:
                        if tx.to is None:
                            continue

                        # Check against tracked tokens
                        for token in tracked_tokens:
                            try:
                                # Check if transaction involves this token
                                if token['address'].lower() == tx.to.lower():
                                    # Calculate value
                                    value_eth = Web3.from_wei(tx.value, 'ether')
                                    usd_estimate = float(value_eth) * 3000  # Approximate

                                    # Check if above threshold
                                    if usd_estimate >= token.get('min_volume_usd', 0):
                                        symbol = token.get('symbol', 'Unknown')
                                        tx_link = f"https://etherscan.io/tx/{tx.hash.hex()}"

                                        # Send formatted alert
                                        message = (
                                            f"🟢 *[ETH BUY ALERT]* 🟢\n\n"
                                            f"🪙 *Token:* {symbol}\n"
                                            f"💰 *Amount:* {value_eth:.4f} ETH\n"
                                            f"💵 *Value:* ${usd_estimate:.2f}\n"
                                            f"📦 *Block:* {block_number}\n\n"
                                            f"[View on Etherscan]({tx_link})"
                                        )

                                        await send_alert(
                                            f"💎 DETECTED: {symbol} token in transaction {tx.hash.hex()}",
                                            tx_url=f"https://etherscan.io/tx/{tx.hash.hex()}",
                                            chart_url=f"https://dexscreener.com/ethereum/{tx.to}"
                                        )
                            except Exception as e:
                                logger.error(f"Error processing ETH transaction: {e}")

                last_block = current_block

            await asyncio.sleep(15)  # Check every 15 seconds
        except Exception as e:
            logger.error(f"Error in Ethereum monitoring: {e}")
            await asyncio.sleep(30) 

async def monitor_solana(bot):
    """Monitor Solana for transactions involving tracked tokens"""
    logger.info("🔎 Starting Solana monitoring...")

    try:
        # Import necessary Solana libraries
        from solana.rpc.async_api import AsyncClient
        from solders.pubkey import Pubkey
        from datetime import datetime

        # Set up Solana client
        client = AsyncClient("https://api.mainnet-beta.solana.com")

        # Get data manager
        from data_manager import get_data_manager
        dm = get_data_manager()

        # Track last processed slot
        resp = await client.get_slot()
        latest_slot = resp.value if hasattr(resp, 'value') else 0

        while True:
            try:
                # Get current slot
                resp = await client.get_slot()
                current_slot = resp.value if hasattr(resp, 'value') else 0

                if current_slot > latest_slot:
                    logger.info(f"Processing new Solana slots: {latest_slot} to {current_slot}")

                    # Get tracked tokens
                    tracked_tokens = []
                    for token in dm.data.get("tracked_tokens", []):
                        if token.get("network", "").lower() == "solana":
                            tracked_tokens.append(token)

                    # Skip if no tokens to track
                    if not tracked_tokens:
                        latest_slot = current_slot
                        await asyncio.sleep(30)
                        continue

                    # Process tokens
                    for token in tracked_tokens:
                        address = token.get('address')
                        symbol = token.get('symbol', 'Unknown')
                        min_usd = token.get('min_volume_usd', 0)

                        # Get signatures for this token's transactions
                        resp = await client.get_signatures_for_address(address, limit=10)

                        if hasattr(resp, 'value') and resp.value:
                            for sig_info in resp.value:
                                # Check if this is a new signature
                                sig = sig_info.signature

                                # Process transaction
                                tx_resp = await client.get_transaction(sig)

                                if hasattr(tx_resp, 'value') and tx_resp.value:
                                    # Extract approximate value (simplified example)
                                    ui_amount = 0.5  # Placeholder, actual extraction would be more complex
                                    usd_estimate = ui_amount * 150  # Approximate SOL price

                                    if usd_estimate >= min_usd:
                                        # Determine if we have buyer address
                                        buyer_text = ""
                                        if 'buyer_address' in locals() and buyer_address != "Unknown":
                                            short_buyer = f"{buyer_address[:4]}...{buyer_address[-4:]}"
                                            buyer_text = f"👤 Buyer: {short_buyer}\n"

                                        # Determine swap provider if available
                                        provider_text = ""
                                        if 'swap_provider' in locals() and swap_provider != "Unknown":
                                            provider_text = f"🔄 Via: {swap_provider}\n"

                                        # Create a more informative message with more details
                                        message = (
                                            f"🔵 SOLANA BUY ALERT 🔵\n\n"
                                            f"🪙 Token: {symbol} (${symbol})\n"
                                            f"💰 Amount: {ui_amount:.4f} SOL\n"
                                            f"💵 Value: ${usd_estimate:.2f}\n"
                                            f"{provider_text}"
                                            f"{buyer_text}"
                                            f"⏱️ Time: {datetime.now().strftime('%H:%M:%S')}\n"
                                        )
                                        await send_alert(
                                            message,
                                            tx_url=f"https://solscan.io/tx/{sig}"
                                        )

                    latest_slot = current_slot

                await asyncio.sleep(15)

            except Exception as e:
                logger.error(f"Error in Solana monitoring: {e}")
                await asyncio.sleep(30)

    except ImportError:
        logger.error("Solana libraries not installed. Solana monitoring disabled.")
        await asyncio.sleep(300)  # Sleep to avoid rapid restarts

async def start_dual_chain_monitors(bot):
    """Start monitoring for both Ethereum and Solana chains"""
    # Start Ethereum monitoring
    eth_task = asyncio.create_task(monitor_ethereum(bot))

    # Try to start Solana monitoring
    try:
        sol_task = asyncio.create_task(monitor_solana(bot))
    except Exception as e:
        logger.error(f"Failed to start Solana monitoring: {e}")
        sol_task = None

    return eth_task, sol_task

def register_dual_chain_commands(app):
    """Register commands related to dual chain tracking"""
    set_application(app)

    # Add command handlers for dual chain
    from telegram.ext import CommandHandler

    app.add_handler(CommandHandler("dual_chain", dual_chain_command))
    app.add_handler(CommandHandler("track_chain", track_chain_command))
    app.add_handler(CommandHandler("untrack_chain", untrack_chain_command))
    app.add_handler(CommandHandler("list_chain", list_chain_command))
    app.add_handler(CommandHandler("test_eth", test_eth_alert))
    app.add_handler(CommandHandler("test_sol", test_sol_alert))

    logger.info("✅ Dual chain commands registered")
    return app
import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Union, Set

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, ApplicationBuilder

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory cache for tracked tokens
token_cache = {
    "ethereum": [],
    "solana": [],
    "last_update": datetime.now().timestamp()
}

class DualChainTracker:
    def __init__(self, application=None):
        self.application = application
        self.eth_monitor = None
        self.sol_monitor = None
        self.register_handlers()
        
        # Cache refresh interval in seconds
        self.cache_refresh_interval = 300  # 5 minutes
        
        # Initialize cache
        self.refresh_token_cache()
    
    def register_handlers(self):
        """Register handlers for dual chain commands"""
        if not self.application:
            logger.warning("⚠️ Application not provided, handlers not registered")
            return
            
        # Add command handlers
        self.application.add_handler(CommandHandler("track_chain", self.track_chain_command))
        self.application.add_handler(CommandHandler("untrack_chain", self.untrack_chain_command))
        self.application.add_handler(CommandHandler("list_chain", self.list_chain_command))
        self.application.add_handler(CommandHandler("test_eth", self.handle_test_eth_command))
        self.application.add_handler(CommandHandler("test_sol", self.handle_test_sol_command))
        self.application.add_handler(CommandHandler("status_chain", self.status_chain_command))
        
        logger.info("✅ Dual chain tracker handlers registered")
    
    def refresh_token_cache(self):
        """Refresh the in-memory token cache from data manager"""
        try:
            from data_manager import get_data_manager
            dm = get_data_manager()
            
            if "tracked_tokens" in dm.data:
                # Clear current cache
                token_cache["ethereum"] = []
                token_cache["solana"] = []
                
                # Populate cache from data manager
                for token in dm.data["tracked_tokens"]:
                    network = token.get("network", "").lower()
                    if network in ["ethereum", "solana"]:
                        token_cache[network].append(token)
                
                # Update timestamp
                token_cache["last_update"] = datetime.now().timestamp()
                
                logger.info(f"✅ Token cache refreshed - ETH: {len(token_cache['ethereum'])}, SOL: {len(token_cache['solana'])}")
            else:
                logger.warning("No tracked_tokens found in data manager")
        except Exception as e:
            logger.error(f"❌ Error refreshing token cache: {e}")
    
    def get_tracked_tokens(self, network: str) -> List[Dict]:
        """Get tracked tokens for a specific network, using cache when possible"""
        # Check if cache needs refreshing (older than cache_refresh_interval)
        current_time = datetime.now().timestamp()
        if current_time - token_cache["last_update"] > self.cache_refresh_interval:
            self.refresh_token_cache()
        
        return token_cache.get(network.lower(), [])
    
    async def track_chain_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Track a token on Ethereum or Solana chains"""
        if not context.args or len(context.args) < 3:
            await update.message.reply_text(
                "❌ Usage: `/track_chain <eth|sol> <address> <symbol> [min_usd]`\n\n"
                "Examples:\n"
                "• `/track_chain eth 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984 UNI 10`\n"
                "• `/track_chain sol EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v USDC 10`",
                parse_mode="Markdown"
            )
            return
        
        chain = context.args[0].lower()
        address = context.args[1]
        symbol = context.args[2]
        min_usd = float(context.args[3]) if len(context.args) > 3 and context.args[3].replace(".", "", 1).isdigit() else 10.0
        chat_id = update.effective_chat.id
        
        if chain not in ["eth", "ethereum", "sol", "solana"]:
            await update.message.reply_text("❌ Invalid chain. Use 'eth' or 'sol'.")
            return
        
        # Map shorthand to full chain name
        full_chain = "ethereum" if chain in ["eth", "ethereum"] else "solana"
        
        # Track based on chain
        if full_chain == "ethereum":
            await self.track_ethereum(update, context, address, symbol, min_usd, chat_id)
        else:
            await self.track_solana(update, context, address, symbol, min_usd, chat_id)
    
    async def track_ethereum(self, update, context, address, symbol, min_usd, chat_id):
        """Track an Ethereum token"""
        if not address.startswith("0x"):
            await update.message.reply_text("❌ Invalid Ethereum address. It should start with 0x.")
            return
        
        # Initialize eth_monitor if needed
        if not self.eth_monitor:
            from eth_monitor import get_instance
            self.eth_monitor = get_instance(context.bot)
        
        # Create token name from symbol
        name = f"{symbol} Token"
        
        # Track in eth_monitor
        success = self.eth_monitor.track_contract(address, name, symbol, chat_id, min_usd)
        
        # Also save to data manager
        try:
            from data_manager import add_tracked_token
            add_tracked_token(chat_id, address, name, symbol, min_usd, "ethereum")
            logger.info(f"💾 Saved ETH token {symbol} to data manager")
            
            # Update token cache
            self.refresh_token_cache()
        except Exception as e:
            logger.error(f"❌ Failed to save token to data manager: {e}")
        
        # Create chart buttons
        etherscan_url = f"https://etherscan.io/token/{address}"
        dextools_url = f"https://www.dextools.io/app/ether/pair-explorer/{address}"
        keyboard = [
            [
                InlineKeyboardButton("📊 Chart", url=dextools_url),
                InlineKeyboardButton("🔍 Etherscan", url=etherscan_url)
            ],
            [
                InlineKeyboardButton("🧪 Test Alert", callback_data=f"test_eth_{address}"),
                InlineKeyboardButton("🚀 BOOST", callback_data=f"boost_{address}")
            ]
        ]
        
        await update.message.reply_text(
            f"✅ Now tracking *{symbol}* on Ethereum\n\n"
            f"📋 *Details:*\n"
            f"• Address: `{address}`\n"
            f"• Min value: ${min_usd}\n"
            f"• Tracking in: This chat\n\n"
            f"🔔 You'll receive alerts when buys exceed ${min_usd}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def track_solana(self, update, context, address, symbol, min_usd, chat_id):
        """Track a Solana token"""
        # Initialize sol_monitor if needed
        if not self.sol_monitor:
            try:
                from solana_monitor import get_instance
                self.sol_monitor = get_instance(context.bot)
            except ImportError:
                # Try alternate import pattern
                from main import sol_monitor
                self.sol_monitor = sol_monitor
        
        # Create token name from symbol
        name = f"{symbol} Token"
        
        # Track in sol_monitor
        success = False
        if self.sol_monitor:
            success = self.sol_monitor.add_token(address, name, symbol, chat_id, min_usd)
        
        # Save to data manager
        try:
            from data_manager import add_tracked_token
            add_tracked_token(chat_id, address, name, symbol, min_usd, "solana")
            logger.info(f"💾 Saved SOL token {symbol} to data manager")
            
            # Update token cache
            self.refresh_token_cache()
            success = True
        except Exception as e:
            logger.error(f"❌ Failed to save token to data manager: {e}")
        
        # Create chart buttons
        solscan_url = f"https://solscan.io/token/{address}"
        dexscreener_url = f"https://dexscreener.com/solana/{address}"
        keyboard = [
            [
                InlineKeyboardButton("📊 Chart", url=dexscreener_url),
                InlineKeyboardButton("🔍 Solscan", url=solscan_url)
            ],
            [
                InlineKeyboardButton("🧪 Test Alert", callback_data=f"test_sol_{address}"),
                InlineKeyboardButton("🚀 BOOST", callback_data=f"boost_{address}")
            ]
        ]
        
        if success:
            await update.message.reply_text(
                f"✅ Now tracking *{symbol}* on Solana\n\n"
                f"📋 *Details:*\n"
                f"• Address: `{address}`\n"
                f"• Min value: ${min_usd}\n"
                f"• Tracking in: This chat\n\n"
                f"🔔 You'll receive alerts when buys exceed ${min_usd}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                f"⚠️ Token added to database but Solana monitor not available.\n"
                f"Tracking may not be active until the bot restarts.",
                parse_mode="Markdown"
            )
    
    async def untrack_chain_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Untrack a token from either chain"""
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ Usage: `/untrack_chain <eth|sol> <address>`\n\n"
                "Examples:\n"
                "• `/untrack_chain eth 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984`\n"
                "• `/untrack_chain sol EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`",
                parse_mode="Markdown"
            )
            return
        
        chain = context.args[0].lower()
        address = context.args[1]
        chat_id = update.effective_chat.id
        
        if chain not in ["eth", "ethereum", "sol", "solana"]:
            await update.message.reply_text("❌ Invalid chain. Use 'eth' or 'sol'.")
            return
        
        # Map shorthand to full chain name
        full_chain = "ethereum" if chain in ["eth", "ethereum"] else "solana"
        
        # Untrack based on chain
        if full_chain == "ethereum":
            await self.untrack_ethereum(update, context, address, chat_id)
        else:
            await self.untrack_solana(update, context, address, chat_id)
    
    async def untrack_ethereum(self, update, context, address, chat_id):
        """Untrack an Ethereum token"""
        if not self.eth_monitor:
            from eth_monitor import get_instance
            self.eth_monitor = get_instance(context.bot)
        
        # Untrack in eth_monitor
        success = self.eth_monitor.untrack_contract(address, chat_id)
        
        # Remove from data manager
        try:
            from data_manager import remove_tracked_token
            removed = remove_tracked_token(chat_id, address, "ethereum")
            logger.info(f"💾 Removed ETH token {address} from data manager: {removed}")
            
            # Update token cache
            self.refresh_token_cache()
            success = True
        except Exception as e:
            logger.error(f"❌ Failed to remove token from data manager: {e}")
        
        if success:
            await update.message.reply_text(f"✅ Untracked Ethereum token: `{address}`", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"⚠️ Token `{address}` was not being tracked or could not be removed.", parse_mode="Markdown")
    
    async def untrack_solana(self, update, context, address, chat_id):
        """Untrack a Solana token"""
        if not self.sol_monitor:
            try:
                from solana_monitor import get_instance
                self.sol_monitor = get_instance(context.bot)
            except ImportError:
                from main import sol_monitor
                self.sol_monitor = sol_monitor
        
        success = False
        # Remove from sol_monitor if available
        if self.sol_monitor:
            success = self.sol_monitor.remove_token(address, chat_id)
        
        # Remove from data manager
        try:
            from data_manager import remove_tracked_token
            removed = remove_tracked_token(chat_id, address, "solana")
            logger.info(f"💾 Removed SOL token {address} from data manager: {removed}")
            
            # Update token cache
            self.refresh_token_cache()
            success = True
        except Exception as e:
            logger.error(f"❌ Failed to remove token from data manager: {e}")
        
        if success:
            await update.message.reply_text(f"✅ Untracked Solana token: `{address}`", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"⚠️ Token `{address}` was not being tracked or could not be removed.", parse_mode="Markdown")
    
    async def list_chain_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all tracked tokens from both chains for this chat"""
        chat_id = update.effective_chat.id
        
        # Get tokens from cache
        eth_tokens = [t for t in self.get_tracked_tokens("ethereum") if str(t.get("chat_id", "")) == str(chat_id)]
        sol_tokens = [t for t in self.get_tracked_tokens("solana") if str(t.get("chat_id", "")) == str(chat_id)]
        
        if not eth_tokens and not sol_tokens:
            await update.message.reply_text(
                "📋 You are not tracking any tokens.\n\n"
                "Use `/track_chain eth <address> <symbol> [min_usd]` to track an Ethereum token\n"
                "Use `/track_chain sol <address> <symbol> [min_usd]` to track a Solana token",
                parse_mode="Markdown"
            )
            return
        
        message = "📋 *Tracked Tokens*\n\n"
        
        if eth_tokens:
            message += "*Ethereum Tokens:*\n"
            for i, token in enumerate(eth_tokens[:10], 1):
                symbol = token.get("symbol", "???")
                address = token.get("address", "Unknown")
                min_usd = token.get("min_volume_usd", 0)
                short_addr = f"{address[:8]}...{address[-6:]}"
                message += f"{i}. {symbol} - `{short_addr}` - Min: ${min_usd}\n"
            
            if len(eth_tokens) > 10:
                message += f"...and {len(eth_tokens) - 10} more\n"
            
            message += "\n"
        
        if sol_tokens:
            message += "*Solana Tokens:*\n"
            for i, token in enumerate(sol_tokens[:10], 1):
                symbol = token.get("symbol", "???")
                address = token.get("address", "Unknown")
                min_usd = token.get("min_volume_usd", 0)
                short_addr = f"{address[:8]}...{address[-6:] if len(address) > 14 else ''}"
                message += f"{i}. {symbol} - `{short_addr}` - Min: ${min_usd}\n"
            
            if len(sol_tokens) > 10:
                message += f"...and {len(sol_tokens) - 10} more\n"
        
        # Create management buttons
        keyboard = [
            [
                InlineKeyboardButton("➕ Track ETH Token", callback_data="track_eth"),
                InlineKeyboardButton("➕ Track SOL Token", callback_data="track_sol")
            ],
            [
                InlineKeyboardButton("🚀 BOOST Your Token", callback_data="boost"),
                InlineKeyboardButton("📊 Chain Status", callback_data="status_chain")
            ]
        ]
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def status_chain_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show status of monitored chains"""
        chat_id = update.effective_chat.id
        
        # Get tokens from cache
        eth_tokens = [t for t in self.get_tracked_tokens("ethereum") if str(t.get("chat_id", "")) == str(chat_id)]
        sol_tokens = [t for t in self.get_tracked_tokens("solana") if str(t.get("chat_id", "")) == str(chat_id)]
        
        # Get monitor instances
        if not self.eth_monitor:
            try:
                from eth_monitor import get_instance
                self.eth_monitor = get_instance(context.bot)
            except Exception as e:
                logger.error(f"❌ Error getting ETH monitor: {e}")
        
        if not self.sol_monitor:
            try:
                from solana_monitor import get_instance
                self.sol_monitor = get_instance(context.bot)
            except ImportError:
                try:
                    from main import sol_monitor
                    self.sol_monitor = sol_monitor
                except Exception as e:
                    logger.error(f"❌ Error getting SOL monitor: {e}")
        
        # Check ETH connection
        eth_status = "✅ Connected" if self.eth_monitor and hasattr(self.eth_monitor, 'web3') and self.eth_monitor.web3.is_connected() else "❌ Disconnected"
        
        # Check SOL connection 
        sol_status = "✅ Connected" if self.sol_monitor else "❌ Disconnected"
        
        message = "🔍 *Chain Monitor Status*\n\n"
        message += f"*Ethereum:*\n"
        message += f"• Connection: {eth_status}\n"
        message += f"• Tokens tracked in this chat: {len(eth_tokens)}\n"
        message += f"• Total tokens tracked: {len(self.get_tracked_tokens('ethereum'))}\n"
        
        if self.eth_monitor and hasattr(self.eth_monitor, 'total_alerts_sent'):
            message += f"• Alerts sent: {self.eth_monitor.total_alerts_sent}\n"
        
        message += f"\n*Solana:*\n"
        message += f"• Connection: {sol_status}\n"
        message += f"• Tokens tracked in this chat: {len(sol_tokens)}\n"
        message += f"• Total tokens tracked: {len(self.get_tracked_tokens('solana'))}\n"
        
        if self.sol_monitor and hasattr(self.sol_monitor, 'alerts_sent'):
            message += f"• Alerts sent: {self.sol_monitor.alerts_sent}\n"
        
        # Add some diagnostic info
        message += f"\n*System:*\n"
        message += f"• Cache last updated: {datetime.fromtimestamp(token_cache['last_update']).strftime('%H:%M:%S')}\n"
        message += f"• Current time: {datetime.now().strftime('%H:%M:%S')}\n"
        
        # Add command tips
        message += f"\n💡 *Commands:*\n"
        message += f"• `/track_chain eth|sol <address> <symbol> [min_usd]` - Track a token\n"
        message += f"• `/untrack_chain eth|sol <address>` - Untrack a token\n"
        message += f"• `/test_eth` or `/test_sol` - Send test alerts\n"
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh Status", callback_data="refresh_status"),
                InlineKeyboardButton("📋 List Tokens", callback_data="list_tokens")
            ],
            [
                InlineKeyboardButton("🧪 Test ETH Alert", callback_data="test_eth_alert"),
                InlineKeyboardButton("🧪 Test SOL Alert", callback_data="test_sol_alert")
            ]
        ]
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_test_eth_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the test_eth command to send an Ethereum test alert"""
        chat_id = update.effective_chat.id
        await update.message.reply_text("🧪 Sending Ethereum test alert...")
        
        # Use the fixed function name for test alerts
        await self.send_eth_test_alert(chat_id)
    
    async def handle_test_sol_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the test_sol command to send a Solana test alert"""
        chat_id = update.effective_chat.id
        await update.message.reply_text("🧪 Sending Solana test alert...")
        
        await self.send_sol_test_alert(chat_id)
    
    async def send_eth_test_alert(self, chat_id):
        """Send an Ethereum test alert - FIXED to avoid recursion"""
        try:
            # Get a tracked ETH token for this chat
            eth_tokens = [t for t in self.get_tracked_tokens("ethereum") if str(t.get("chat_id", "")) == str(chat_id)]
            
            if eth_tokens:
                test_token = eth_tokens[0]
                logger.info(f"📋 Using tracked token for test: {test_token.get('symbol')} ({test_token.get('address')})")
            else:
                # Default test token (UNI)
                test_token = {
                    "address": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
                    "name": "Uniswap",
                    "symbol": "UNI",
                    "chain": "ethereum",
                    "network": "ethereum",
                    "chat_id": str(chat_id)
                }
                logger.info(f"📋 Using default UNI test token")
            
            # Import the send_eth_alert function from eth_monitor
            from eth_monitor import send_eth_alert
            
            # Send the alert
            success = await send_eth_alert(
                bot=self.application.bot,
                chat_id=chat_id,
                symbol=test_token.get("symbol", "TEST"),
                amount=1.5,
                tx_hash="0x" + "abcdef1234567890" * 4,
                token_info=test_token,
                usd_value=3000,
                dex_name="Uniswap (Test)"
            )
            
            return success
        except Exception as e:
            logger.error(f"❌ Error sending ETH test alert: {e}")
            return False
    
    async def send_sol_test_alert(self, chat_id):
        """Send a Solana test alert"""
        try:
            # Get a tracked SOL token for this chat
            sol_tokens = [t for t in self.get_tracked_tokens("solana") if str(t.get("chat_id", "")) == str(chat_id)]
            
            if sol_tokens:
                test_token = sol_tokens[0]
                logger.info(f"📋 Using tracked token for test: {test_token.get('symbol')} ({test_token.get('address')})")
            else:
                # Default test token (Wrapped SOL)
                test_token = {
                    "address": "So11111111111111111111111111111111111111112",
                    "name": "Wrapped SOL",
                    "symbol": "WSOL",
                    "chain": "solana",
                    "network": "solana",
                    "chat_id": str(chat_id)
                }
                logger.info(f"📋 Using default WSOL test token")
            
            try:
                # Try to import from solana_monitor
                from solana_monitor import send_solana_alert
                
                # Send the alert
                success = await send_solana_alert(
                    bot=self.application.bot,
                    token_info=test_token,
                    value_token=2.5,
                    value_usd=150,
                    tx_hash="solana_test_" + test_token.get("address", "")[-8:],
                    dex_name="Raydium (Test)",
                    chain="solana"
                )
                
                return success
            except ImportError:
                # Fallback to a standard message if solana_monitor is not available
                markup = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📊 Chart", url=f"https://dexscreener.com/solana/{test_token.get('address')}"),
                        InlineKeyboardButton("🛒 Buy Now", url=f"https://jup.ag/swap/SOL-{test_token.get('address')}")
                    ]
                ])
                
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=f"🚨 *TEST SOLANA ALERT*\n\n"
                         f"🪙 *Token:* {test_token.get('name')} ({test_token.get('symbol')})\n"
                         f"💰 *Amount:* 2.5 SOL (~$150)\n"
                         f"🏦 *DEX:* Raydium (Test)\n\n"
                         f"This is a test alert.",
                    parse_mode="Markdown",
                    reply_markup=markup
                )
                
                return True
        except Exception as e:
            logger.error(f"❌ Error sending SOL test alert: {e}")
            return False

    async def monitor_ethereum(self, txs):
        """Enhanced Ethereum transaction monitoring with input data decoding"""
        if not txs:
            return
        
        try:
            # Get tracked tokens
            eth_tokens = self.get_tracked_tokens("ethereum")
            if not eth_tokens:
                return
            
            # Import Web3 for transaction decoding
            from web3 import Web3
            web3 = Web3()
            
            # Define common method signatures for token buys
            buy_signatures = [
                "0x7ff36ab5",  # swapExactETHForTokens
                "0xb6f9de95",  # swapExactETHForTokensSupportingFeeOnTransferTokens
                "0x38ed1739",  # swapExactTokensForTokens
                "0x5c11d795",  # swapExactTokensForTokensSupportingFeeOnTransferTokens
                "0x04e45aaf",  # exactInputSingle (Uniswap V3)
                "0xc04b8d59"   # exactInput (Uniswap V3)
            ]
            
            for tx in txs:
                # Skip if no transaction data or not on the right chain
                if not tx.get("input") or tx.get("chain") != "ethereum":
                    continue
                
                # Extract method signature from input data
                method_sig = tx.get("input")[:10].lower() if len(tx.get("input", "")) >= 10 else ""
                
                # Skip if not a buy method
                if method_sig not in buy_signatures:
                    continue
                
                # Decode input data to look for token addresses
                input_data = tx.get("input", "")
                
                # Check if any tracked token address is in the input data
                for token in eth_tokens:
                    token_address = token.get("address", "").lower()
                    
                    # Skip if token address not in input
                    if token_address.replace("0x", "") not in input_data.lower():
                        continue
                    
                    # Token found in transaction input, likely a buy
                    logger.info(f"🚨 Potential ETH buy detected: {token.get('symbol')} in tx {tx.get('hash', 'unknown')}")
                    
                    # Process the buy - in a real implementation, you'd parse amount, etc.
                    # For demonstration, we'll use placeholder values
                    chat_id = token.get("chat_id")
                    if not chat_id:
                        continue
                    
                    # Get token amount - in a real implementation, parse this from logs
                    # This is a placeholder for demonstration
                    tx_value_eth = float(Web3.from_wei(int(tx.get("value", "0"), 16), "ether")) if tx.get("value") else 0
                    tx_value_usd = tx_value_eth * 3000  # Using fixed ETH price for example
                    
                    # Check if the transaction value meets the minimum threshold
                    min_usd = token.get("min_volume_usd", 0)
                    if tx_value_usd < min_usd:
                        logger.info(f"⚠️ ETH buy below threshold: ${tx_value_usd} < ${min_usd}")
                        continue
                    
                    # Send alert for this token
                    from eth_monitor import send_eth_alert
                    
                    await send_eth_alert(
                        bot=self.application.bot,
                        chat_id=chat_id,
                        symbol=token.get("symbol", "???"),
                        amount=tx_value_eth,
                        tx_hash=tx.get("hash", "0x"),
                        token_info=token,
                        usd_value=tx_value_usd,
                        dex_name="Uniswap"
                    )
                    
        except Exception as e:
            logger.error(f"❌ Error in monitor_ethereum: {e}")
    
    async def monitor_solana(self, txs):
        """Enhanced Solana transaction monitoring with value parsing"""
        if not txs:
            return
        
        try:
            # Get tracked tokens
            sol_tokens = self.get_tracked_tokens("solana")
            if not sol_tokens:
                return
            
            for tx in txs:
                # Skip if no transaction data or not on the right chain
                if not tx.get("signature") or tx.get("chain") != "solana":
                    continue
                
                # Process each token in the transaction
                for token_mint in tx.get("tokens", []):
                    for tracked_token in sol_tokens:
                        if tracked_token.get("address") == token_mint:
                            # Token found in transaction
                            logger.info(f"🚨 Potential SOL transaction detected: {tracked_token.get('symbol')} in tx {tx.get('signature', 'unknown')}")
                            
                            # Parse token amount from the transaction
                            # In a real implementation, use the actual token amount from tx
                            ui_amount = tx.get("amount", 0.5)  # Try to get amount from tx, default to 0.5
                            
                            # Calculate USD value based on SOL price
                            # In a real implementation, get the actual SOL price from an oracle
                            sol_price_usd = 60  # Fixed SOL price for example
                            value_usd = ui_amount * sol_price_usd
                            
                            # Check if the transaction value meets the minimum threshold
                            min_usd = tracked_token.get("min_volume_usd", 0)
                            if value_usd < min_usd:
                                logger.info(f"⚠️ SOL transaction below threshold: ${value_usd} < ${min_usd}")
                                continue
                            
                            # Send alert for this token
                            chat_id = tracked_token.get("chat_id")
                            if not chat_id:
                                continue
                            
                            try:
                                from solana_monitor import send_solana_alert
                                
                                await send_solana_alert(
                                    bot=self.application.bot,
                                    token_info=tracked_token,
                                    value_token=ui_amount,
                                    value_usd=value_usd,
                                    tx_hash=tx.get("signature", ""),
                                    dex_name=tx.get("dex", "Solana DEX"),
                                    chain="solana"
                                )
                            except ImportError:
                                # Fallback if the function isn't available
                                logger.warning(f"⚠️ Could not import send_solana_alert, using fallback alert")
                                
                                # Create a fallback alert
                                markup = InlineKeyboardMarkup([
                                    [
                                        InlineKeyboardButton("📊 Chart", url=f"https://dexscreener.com/solana/{tracked_token.get('address')}"),
                                        InlineKeyboardButton("🔍 Solscan", url=f"https://solscan.io/tx/{tx.get('signature', '')}")
                                    ]
                                ])
                                
                                await self.application.bot.send_message(
                                    chat_id=chat_id,
                                    text=f"🚨 *SOLANA BUY ALERT*\n\n"
                                         f"🪙 *Token:* {tracked_token.get('name')} ({tracked_token.get('symbol')})\n"
                                         f"💰 *Amount:* {ui_amount} SOL (~${value_usd:.2f})\n"
                                         f"🏦 *DEX:* {tx.get('dex', 'Solana DEX')}\n\n"
                                         f"[View Transaction](https://solscan.io/tx/{tx.get('signature', '')})",
                                    parse_mode="Markdown",
                                    reply_markup=markup
                                )
                            
        except Exception as e:
            logger.error(f"❌ Error in monitor_solana: {e}")

# Create a function to get or create the dual chain tracker instance
_instance = None

def get_instance(application=None):
    """Get or create a dual chain tracker instance"""
    global _instance
    if _instance is None:
        _instance = DualChainTracker(application)
    elif application is not None:
        _instance.application = application
        _instance.register_handlers()
    return _instance

# Add command to set up dual chain tracker when imported
def setup_dual_chain_tracker(application):
    """Set up the dual chain tracker with the given application"""
    tracker = get_instance(application)
    logger.info("✅ Dual Chain Tracker initialized")
    return tracker

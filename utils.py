import asyncio
import logging
import json
from datetime import datetime

def save_tracked_tokens(chain: str, address: str, group_id: int):
    """
    Save a tracked token to the appropriate storage

    Args:
        chain: The blockchain (ethereum, solana, bnb)
        address: The token contract address
        group_id: The Telegram chat/group ID
    """
    import json
    import os
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        path = f"data/tracked_{chain}.json"

        # Load existing data if available
        data = {}
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse {path}, creating new file")

        # Add or update the token entry
        key = f"{address.lower()}_{group_id}"
        if key not in data:
            data[key] = {
                "address": address.lower(),
                "chain": chain,
                "chat_id": group_id,
                "added_at": str(datetime.now())
            }

        # Save updated data
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"✅ Saved tracked token: {chain}, {address}, group: {group_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving tracked token: {e}")
        return False


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from data_manager import get_tokens_by_network, get_tracked_token_info

async def handle_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show status of bot including tracked tokens"""
    chat_id = update.effective_chat.id

    # Get tracked tokens for this chat using the utility functions
    from transaction_utils import get_tokens_by_chat, get_tokens_by_network

    eth_tokens_for_chat = get_tokens_by_chat(chat_id, "ethereum")
    sol_tokens_for_chat = get_tokens_by_chat(chat_id, "solana")

    # Get total tokens by network for diagnostics
    eth_tokens = get_tokens_by_network("ethereum") 
    sol_tokens = get_tokens_by_network("solana")

    # Get eth_monitor instance to check web3 connection
    from eth_monitor import get_instance
    eth_monitor = get_instance()

    web3_status = "✅ Connected" if eth_monitor and eth_monitor.web3 and eth_monitor.web3.is_connected() else "❌ Disconnected"

    # Prepare status message
    status_msg = f"🤖 *Bot Status Report* 🤖\n\n"
    status_msg += f"🔗 Web3 Connection: {web3_status}\n"
    status_msg += f"🔍 Monitoring Status: ✅ Active\n\n"

    # Add tracking info
    status_msg += f"📊 *Tracked Tokens in This Chat:*\n"
    status_msg += f"• Ethereum: {len(eth_tokens_for_chat)} tokens\n"
    status_msg += f"• Solana: {len(sol_tokens_for_chat)} tokens\n\n"

    # List tracked token details
    if eth_tokens_for_chat:
        status_msg += "*Ethereum Tokens:*\n"
        for i, token in enumerate(eth_tokens_for_chat[:5], 1):  # Show first 5 only
            symbol = token.get("symbol", "???")
            address = token.get("address", "Unknown")
            min_usd = token.get("min_volume_usd", 0)
            status_msg += f"{i}. {symbol} (`{address[:8]}...{address[-6:]}`) - min: ${min_usd}\n"
        if len(eth_tokens_for_chat) > 5:
            status_msg += f"...and {len(eth_tokens_for_chat) - 5} more\n"

    if sol_tokens_for_chat:
        status_msg += "\n*Solana Tokens:*\n"
        for i, token in enumerate(sol_tokens_for_chat[:5], 1):  # Show first 5 only
            symbol = token.get("symbol", "???")
            address = token.get("address", "Unknown")
            min_usd = token.get("min_volume_usd", 0)
            status_msg += f"{i}. {symbol} (`{address[:8]}...{address[-6:] if len(address) > 14 else ''}`) - min: ${min_usd}\n"
        if len(sol_tokens_for_chat) > 5:
            status_msg += f"...and {len(sol_tokens_for_chat) - 5} more\n"

    # Add diagnostics info
    status_msg += "\n🔧 *Diagnostics:*\n"
    status_msg += f"• Chat ID: `{chat_id}`\n"
    status_msg += f"• Total tracked tokens: {len(eth_tokens) + len(sol_tokens)}\n"

    # Add tips
    status_msg += "\n💡 *Commands:*\n"
    status_msg += "• `/track 0xADDRESS TokenName SYMBOL 5` - Track Ethereum token\n"
    status_msg += "• `/test_alert` - Test notification delivery\n"
    status_msg += "• `/list` - List all tracked tokens"

    await update.message.reply_text(status_msg, parse_mode="Markdown")

logger = logging.getLogger(__name__)

async def handle_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Automatically register a chat when any interaction happens"""
    await update.message.reply_text("✅ Bot is running and ready to track tokens!")

async def handle_example_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate example alerts for tracked tokens to test notifications"""
    chat_id = update.effective_chat.id

    # Get tracked tokens for the chat
    eth_tokens = get_tokens_by_network("ethereum")
    sol_tokens = get_tokens_by_network("solana")

    # Check if any tokens are being tracked
    if not eth_tokens and not sol_tokens:
        await update.message.reply_text(
            "❌ No tokens are currently being tracked in this chat.\n\n"
            "Please add tokens using:\n"
            "• `/track 0xTOKENADDRESS TokenName Symbol 10` (for Ethereum)\n"
            "• `/tracksol SoTOKENADDRESS TokenName Symbol 10` (for Solana)"
        )
        return

    await update.message.reply_text("🚀 Generating example alerts for tracked tokens...")

    # Generate Ethereum alerts
    if eth_tokens:
        for token in eth_tokens:
            try:
                # Import here to avoid circular imports
                from eth_monitor import send_eth_alert

                # Example values for test
                symbol = token.get("symbol", "ETH")
                token_name = token.get("name", "Example Token")
                token_address = token.get("address", "0x")
                token_info = {
                    "address": token_address,
                    "name": token_name,
                    "symbol": symbol,
                    "chain": "ethereum",
                    "chat_id": str(chat_id)  # Important - ensure chat_id is included
                }

                await send_eth_alert(
                    bot=context.bot,
                    chat_id=chat_id,
                    symbol=symbol,
                    amount=1.5,
                    tx_hash="0xexample" + token_address[-8:],
                    token_info=token_info,
                    usd_value=3000,
                    dex_name="Uniswap (Test Alert)"
                )

                # Add delay to avoid rate limits
                await asyncio.sleep(1.5)

            except Exception as e:
                logger.error(f"Error sending ETH example alert: {e}")
                await update.message.reply_text(f"❌ Error sending ETH example alert: {str(e)}")

    # Generate Solana alerts
    if sol_tokens:
        for token in sol_tokens:
            try:
                # Import here to avoid circular imports
                from solana_monitor import send_solana_alert

                # Example values for test
                symbol = token.get("symbol", "SOL")
                token_name = token.get("name", "Example Sol Token")
                token_address = token.get("address", "So111111")

                # Send test alert
                await send_solana_alert(
                    bot=context.bot,
                    token_info=token,
                    chain="solana",
                    value_token=2.5,
                    value_usd=150,
                    tx_hash="example" + token_address[-8:],
                    dex_name="Raydium (Test Alert)"
                )

                # Add delay to avoid rate limits
                await asyncio.sleep(1.5)

            except Exception as e:
                logger.error(f"Error sending Solana example alert: {e}")
                await update.message.reply_text(f"❌ Error sending Solana example alert: {str(e)}")

    await update.message.reply_text("✅ Example alerts have been processed. Check that they appeared in this chat!")

# Added to address missing 'get_timestamp' and 'add_token' errors.  Placeholders used.  Requires context-specific implementations.

from transaction_utils import get_timestamp # Placeholder import - replace with actual import if needed


class EthMonitor:  # Placeholder class - replace with actual class definition
    def __init__(self):
        self.web3 = None # Placeholder - replace with web3 initialization

    def add_token(self, token_info): # Placeholder method
        print(f"Adding token: {token_info}")
        pass


def get_instance(): # Placeholder get_instance function
    return EthMonitor()
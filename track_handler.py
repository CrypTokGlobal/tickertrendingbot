import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler, 
    MessageHandler, filters, CallbackQueryHandler
)

from data_manager import get_data_manager
from owner_manager import is_owner, is_admin, is_authorized
from auth_decorators import owner_only, strictly_owner
import transaction_utils
from transaction_utils import get_tokens_by_chat

# Import the chain-specific monitors
from eth_monitor import get_instance as get_eth_instance
from solana_monitor import get_instance as get_sol_instance
from bsc_monitor import get_instance as get_bnb_instance

# States for conversation handlers
ETH_TRACK_STATE, SOL_TRACK_STATE, BNB_TRACK_STATE, UNTRACK_STATE = range(4)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get chain monitor instances
eth_monitor = get_eth_instance()
sol_monitor = get_sol_instance()
bnb_monitor = get_bnb_instance()

async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the tracking process for an Ethereum token"""
    if context.args and len(context.args) >= 1:
        # Direct command with arguments
        try:
            address = context.args[0].lower().strip()
            name = context.args[1] if len(context.args) > 1 else "Unknown"
            symbol = context.args[2] if len(context.args) > 2 else "???"
            min_usd = float(context.args[3]) if len(context.args) > 3 else 5.0

            # Validate Ethereum address format
            if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
                await update.message.reply_text("❌ Invalid Ethereum address format. Must start with 0x followed by 40 hex characters.")
                return

            chat_id = update.effective_chat.id

            # Add the token to tracking
            await track_eth_token(update, context, address, name, symbol, min_usd, chat_id)

        except Exception as e:
            logger.error(f"Error in track command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}\n\nPlease use format:\n`/track 0xADDRESS TokenName SYMBOL [min_usd]`", parse_mode="Markdown")

    else:
        # Start the conversation handler
        await update.message.reply_text(
            "📝 Please enter the Ethereum token address to track (starting with 0x):"
        )
        return ETH_TRACK_STATE

async def tracksol_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the tracking process for a Solana token"""
    if context.args and len(context.args) >= 1:
        # Direct command with arguments
        try:
            address = context.args[0].strip()
            name = context.args[1] if len(context.args) > 1 else "Unknown"
            symbol = context.args[2] if len(context.args) > 2 else "???"
            min_usd = float(context.args[3]) if len(context.args) > 3 else 5.0

            # Validate Solana address format (base58 check)
            if not re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", address):
                await update.message.reply_text("❌ Invalid Solana address format. Must be a valid base58 string 32-44 chars long.")
                return

            chat_id = update.effective_chat.id

            # Add the token to tracking
            await track_sol_token(update, context, address, name, symbol, min_usd, chat_id)

        except Exception as e:
            logger.error(f"Error in tracksol command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}\n\nPlease use format:\n`/tracksol ADDRESS TokenName SYMBOL [min_usd]`", parse_mode="Markdown")

    else:
        # Start the conversation handler
        await update.message.reply_text(
            "📝 Please enter the Solana token address to track:"
        )
        return SOL_TRACK_STATE

async def trackbnb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the tracking process for a BSC (Binance Smart Chain) token"""
    if context.args and len(context.args) >= 1:
        # Direct command with arguments
        try:
            address = context.args[0].lower().strip()
            name = context.args[1] if len(context.args) > 1 else "Unknown"
            symbol = context.args[2] if len(context.args) > 2 else "???"
            min_usd = float(context.args[3]) if len(context.args) > 3 else 5.0

            # Validate BSC address format (same as Ethereum)
            if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
                await update.message.reply_text("❌ Invalid BSC address format. Must start with 0x followed by 40 hex characters.")
                return

            chat_id = update.effective_chat.id

            # Add the token to tracking
            await track_bnb_token(update, context, address, name, symbol, min_usd, chat_id)

        except Exception as e:
            logger.error(f"Error in trackbnb command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}\n\nPlease use format:\n`/trackbnb 0xADDRESS TokenName SYMBOL [min_usd]`", parse_mode="Markdown")

    else:
        # Start the conversation handler
        await update.message.reply_text(
            "📝 Please enter the Binance Smart Chain token address to track (starting with 0x):"
        )
        return BNB_TRACK_STATE

async def untrack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a token from tracking"""
    if context.args and len(context.args) >= 1:
        try:
            address = context.args[0].lower().strip()
            chat_id = update.effective_chat.id

            # Check if token exists in tracking
            dm = get_data_manager()
            tokens = dm.data.get("tracked_tokens", [])

            # Find tokens for this chat
            target_token = None
            for token in tokens:
                if token.get("address", "").lower() == address.lower() and str(token.get("chat_id", "")) == str(chat_id):
                    target_token = token
                    break

            if not target_token:
                await update.message.reply_text(f"❌ Token `{address}` is not being tracked in this chat.", parse_mode="Markdown")
                return

            # Remove from data manager
            tokens.remove(target_token)
            dm.data["tracked_tokens"] = tokens
            dm.save()

            # Remove from JSON file
            chain = target_token.get("chain", "ethereum")
            transaction_utils.remove_token_from_file(address, chat_id, chain)

            # Remove from monitor
            if chain == "ethereum" and eth_monitor:
                eth_monitor.remove_token(address, chat_id)
            elif chain == "solana" and sol_monitor:
                sol_monitor.remove_token(address, chat_id)
            elif chain == "binance" and bnb_monitor:
                bnb_monitor.remove_token(address, chat_id)

            await update.message.reply_text(f"✅ Token {target_token.get('name', address)} ({target_token.get('symbol', '???')}) has been removed from tracking.")

        except Exception as e:
            logger.error(f"Error in untrack command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}\n\nPlease use format:\n`/untrack 0xADDRESS`", parse_mode="Markdown")
    else:
        # Start conversation for untracking
        chat_id = update.effective_chat.id

        # Get tokens for this chat
        eth_tokens = get_tokens_by_chat(chat_id, "ethereum")
        sol_tokens = get_tokens_by_chat(chat_id, "solana")
        bnb_tokens = get_tokens_by_chat(chat_id, "binance")

        if not eth_tokens and not sol_tokens and not bnb_tokens:
            await update.message.reply_text("❌ No tokens are currently being tracked in this chat.")
            return

        # Create inline buttons for each token
        buttons = []

        if eth_tokens:
            for token in eth_tokens:
                symbol = token.get("symbol", "???")
                address = token.get("address", "")
                if address:
                    buttons.append([InlineKeyboardButton(f"🔹 ETH: {symbol} ({address[:6]}...{address[-4:]})", callback_data=f"untrack_{address}")])

        if sol_tokens:
            for token in sol_tokens:
                symbol = token.get("symbol", "???")
                address = token.get("address", "")
                if address:
                    buttons.append([InlineKeyboardButton(f"☀️ SOL: {symbol} ({address[:6]}...{address[-4:]})", callback_data=f"untrack_{address}")])

        if bnb_tokens:
            for token in bnb_tokens:
                symbol = token.get("symbol", "???")
                address = token.get("address", "")
                if address:
                    buttons.append([InlineKeyboardButton(f"🟡 BNB: {symbol} ({address[:6]}...{address[-4:]})", callback_data=f"untrack_{address}")])

        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="untrack_cancel")])

        await update.message.reply_text(
            "🗑️ Select a token to remove from tracking:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        return UNTRACK_STATE

async def mytokens_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tokens being tracked in this chat"""
    chat_id = update.effective_chat.id

    # Get tokens for this chat
    eth_tokens = get_tokens_by_chat(chat_id, "ethereum")
    sol_tokens = get_tokens_by_chat(chat_id, "solana")
    bnb_tokens = get_tokens_by_chat(chat_id, "binance")

    if not eth_tokens and not sol_tokens and not bnb_tokens:
        await update.message.reply_text("❌ No tokens are currently being tracked in this chat.")
        return

    message = "🔍 *Tokens tracked in this chat:*\n\n"

    if eth_tokens:
        message += "*Ethereum Tokens:*\n"
        for token in eth_tokens:
            symbol = token.get("symbol", "???")
            name = token.get("name", "Unknown")
            address = token.get("address", "")
            min_usd = token.get("min_volume_usd", 5.0)
            message += f"• {symbol} ({name})\n  `{address}`\n  Min: ${min_usd:.2f}\n\n"

    if sol_tokens:
        message += "*Solana Tokens:*\n"
        for token in sol_tokens:
            symbol = token.get("symbol", "???")
            name = token.get("name", "Unknown")
            address = token.get("address", "")
            min_usd = token.get("min_volume_usd", 5.0)
            message += f"• {symbol} ({name})\n  `{address}`\n  Min: ${min_usd:.2f}\n\n"

    if bnb_tokens:
        message += "*Binance Smart Chain Tokens:*\n"
        for token in bnb_tokens:
            symbol = token.get("symbol", "???")
            name = token.get("name", "Unknown")
            address = token.get("address", "")
            min_usd = token.get("min_volume_usd", 5.0)
            message += f"• {symbol} ({name})\n  `{address}`\n  Min: ${min_usd:.2f}\n\n"

    message += "\nUse `/untrack ADDRESS` to remove a token from tracking."

    await update.message.reply_text(message, parse_mode="Markdown")

async def handle_eth_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Ethereum address input"""
    address = update.message.text.strip().lower()

    # Validate Ethereum address
    if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
        await update.message.reply_text("❌ Invalid Ethereum address format. Must start with 0x followed by 40 hex characters. Please try again:")
        return ETH_TRACK_STATE

    # Store the address in user_data
    context.user_data["eth_address"] = address

    # Ask for token name
    await update.message.reply_text("📝 Enter the token name (e.g., 'Ethereum'):")
    return ETH_TRACK_STATE + 1

async def handle_eth_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Ethereum token name input"""
    name = update.message.text.strip()

    # Store the name in user_data
    context.user_data["eth_name"] = name

    # Ask for token symbol
    await update.message.reply_text("📝 Enter the token symbol (e.g., 'ETH'):")
    return ETH_TRACK_STATE + 2

async def handle_eth_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Ethereum token symbol input"""
    symbol = update.message.text.strip().upper()

    # Store the symbol in user_data
    context.user_data["eth_symbol"] = symbol

    # Ask for minimum USD value
    await update.message.reply_text("📝 Enter the minimum USD value to trigger alerts (default is 5.0):")
    return ETH_TRACK_STATE + 3

async def handle_eth_min_usd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Ethereum token minimum USD value input"""
    try:
        min_usd = float(update.message.text.strip())
        if min_usd <= 0:
            raise ValueError("Min USD must be greater than 0")
    except ValueError:
        # If conversion fails, use default
        min_usd = 5.0
        await update.message.reply_text("⚠️ Invalid value, using default of $5.0")

    # Get stored values
    address = context.user_data.get("eth_address", "")
    name = context.user_data.get("eth_name", "Unknown")
    symbol = context.user_data.get("eth_symbol", "???")
    chat_id = update.effective_chat.id

    # Track the token
    await track_eth_token(update, context, address, name, symbol, min_usd, chat_id)

    # Clear user data
    context.user_data.clear()

    return ConversationHandler.END

async def track_eth_token(update: Update, context: ContextTypes.DEFAULT_TYPE, address, name, symbol, min_usd, chat_id):
    """Add an Ethereum token to tracking"""
    try:
        # Prepare token info
        token_info = {
            "address": address.lower(),
            "name": name,
            "symbol": symbol.upper(),
            "min_volume_usd": float(min_usd),
            "chain": "ethereum",
            "chat_id": chat_id,
            "added_at": transaction_utils.get_timestamp()
        }

        # Add to data manager
        dm = get_data_manager()
        tokens = dm.data.get("tracked_tokens", [])

        # Check if already tracking
        for token in tokens:
            if token.get("address", "").lower() == address.lower() and str(token.get("chat_id", "")) == str(chat_id):
                await update.message.reply_text(f"⚠️ Token {name} ({symbol}) is already being tracked in this chat.")
                return

        tokens.append(token_info)
        dm.data["tracked_tokens"] = tokens
        dm.save()

        # Save to JSON file
        transaction_utils.add_token_to_file(token_info)

        # Add to ETH monitor
        if eth_monitor:
            eth_monitor.add_token(address.lower(), name, symbol, chat_id, min_usd)
            await eth_monitor.start_tracking(address.lower())

        keyboard = [
            [InlineKeyboardButton("📈 Test Alert", callback_data=f"test_alert_{address}")],
            [
                InlineKeyboardButton("🔍 View Token", url=f"https://etherscan.io/token/{address}"),
                InlineKeyboardButton("📊 Chart", url=f"https://dexscreener.com/ethereum/{address}")
            ]
        ]

        await update.message.reply_text(
            f"✅ Now tracking {name} ({symbol}) on Ethereum!\n\n"
            f"📝 Address: `{address}`\n"
            f"💵 Min alert value: ${min_usd}\n\n"
            f"You will receive alerts when swaps exceed the minimum value.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error tracking ETH token: {e}")
        await update.message.reply_text(f"❌ Error: Could not track token - {str(e)}")

# Solana token tracking handlers
async def handle_sol_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Solana address input"""
    address = update.message.text.strip()

    # Validate Solana address format (base58 check)
    if not re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", address):
        await update.message.reply_text("❌ Invalid Solana address format. Must be a valid base58 string 32-44 chars long. Please try again:")
        return SOL_TRACK_STATE

    # Store the address in user_data
    context.user_data["sol_address"] = address

    # Ask for token name
    await update.message.reply_text("📝 Enter the token name (e.g., 'Solana'):")
    return SOL_TRACK_STATE + 1

async def handle_sol_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Solana token name input"""
    name = update.message.text.strip()

    # Store the name in user_data
    context.user_data["sol_name"] = name

    # Ask for token symbol
    await update.message.reply_text("📝 Enter the token symbol (e.g., 'SOL'):")
    return SOL_TRACK_STATE + 2

async def handle_sol_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Solana token symbol input"""
    symbol = update.message.text.strip().upper()

    # Store the symbol in user_data
    context.user_data["sol_symbol"] = symbol

    # Ask for minimum USD value
    await update.message.reply_text("📝 Enter the minimum USD value to trigger alerts (default is 5.0):")
    return SOL_TRACK_STATE + 3

async def handle_sol_min_usd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Solana token minimum USD value input"""
    try:
        min_usd = float(update.message.text.strip())
        if min_usd <= 0:
            raise ValueError("Min USD must be greater than 0")
    except ValueError:
        # If conversion fails, use default
        min_usd = 5.0
        await update.message.reply_text("⚠️ Invalid value, using default of $5.0")

    # Get stored values
    address = context.user_data.get("sol_address", "")
    name = context.user_data.get("sol_name", "Unknown")
    symbol = context.user_data.get("sol_symbol", "???")
    chat_id = update.effective_chat.id

    # Track the token
    await track_sol_token(update, context, address, name, symbol, min_usd, chat_id)

    # Clear user data
    context.user_data.clear()

    return ConversationHandler.END

async def track_sol_token(update: Update, context: ContextTypes.DEFAULT_TYPE, address, name, symbol, min_usd, chat_id):
    """Add a Solana token to tracking"""
    try:
        # Prepare token info
        token_info = {
            "address": address,
            "name": name,
            "symbol": symbol.upper(),
            "min_volume_usd": float(min_usd),
            "chain": "solana",
            "chat_id": chat_id,
            "added_at": transaction_utils.get_timestamp()
        }

        # Add to data manager
        dm = get_data_manager()
        tokens = dm.data.get("tracked_tokens", [])

        # Check if already tracking
        for token in tokens:
            if token.get("address", "") == address and str(token.get("chat_id", "")) == str(chat_id):
                await update.message.reply_text(f"⚠️ Token {name} ({symbol}) is already being tracked in this chat.")
                return

        tokens.append(token_info)
        dm.data["tracked_tokens"] = tokens
        dm.save()

        # Save to JSON file
        transaction_utils.add_token_to_file(token_info)

        # Add to Solana monitor
        if sol_monitor:
            sol_monitor.add_token(address, name, symbol, chat_id, min_usd)
            await sol_monitor.start_tracking(address)

        keyboard = [
            [InlineKeyboardButton("📈 Test Alert", callback_data=f"test_sol_alert_{address}")],
            [
                InlineKeyboardButton("🔍 View Token", url=f"https://solscan.io/token/{address}"),
                InlineKeyboardButton("📊 Chart", url=f"https://dexscreener.com/solana/{address}")
            ]
        ]

        await update.message.reply_text(
            f"✅ Now tracking {name} ({symbol}) on Solana!\n\n"
            f"📝 Address: `{address}`\n"
            f"💵 Min alert value: ${min_usd}\n\n"
            f"You will receive alerts when swaps exceed the minimum value.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error tracking Solana token: {e}")
        await update.message.reply_text(f"❌ Error: Could not track token - {str(e)}")

# BSC token tracking handlers
async def handle_bnb_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the BSC address input"""
    address = update.message.text.strip().lower()

    # Validate BSC address format (same as Ethereum)
    if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
        await update.message.reply_text("❌ Invalid BSC address format. Must start with 0x followed by 40 hex characters. Please try again:")
        return BNB_TRACK_STATE

    # Store the address in user_data
    context.user_data["bnb_address"] = address

    # Ask for token name
    await update.message.reply_text("📝 Enter the token name (e.g., 'PancakeSwap'):")
    return BNB_TRACK_STATE + 1

async def handle_bnb_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the BSC token name input"""
    name = update.message.text.strip()

    # Store the name in user_data
    context.user_data["bnb_name"] = name

    # Ask for token symbol
    await update.message.reply_text("📝 Enter the token symbol (e.g., 'CAKE'):")
    return BNB_TRACK_STATE + 2

async def handle_bnb_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the BSC token symbol input"""
    symbol = update.message.text.strip().upper()

    # Store the symbol in user_data
    context.user_data["bnb_symbol"] = symbol

    # Ask for minimum USD value
    await update.message.reply_text("📝 Enter the minimum USD value to trigger alerts (default is 5.0):")
    return BNB_TRACK_STATE + 3

async def handle_bnb_min_usd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the BSC token minimum USD value input"""
    try:
        min_usd = float(update.message.text.strip())
        if min_usd <= 0:
            raise ValueError("Min USD must be greater than 0")
    except ValueError:
        # If conversion fails, use default
        min_usd = 5.0
        await update.message.reply_text("⚠️ Invalid value, using default of $5.0")

    # Get stored values
    address = context.user_data.get("bnb_address", "")
    name = context.user_data.get("bnb_name", "Unknown")
    symbol = context.user_data.get("bnb_symbol", "???")
    chat_id = update.effective_chat.id

    # Track the token
    await track_bnb_token(update, context, address, name, symbol, min_usd, chat_id)

    # Clear user data
    context.user_data.clear()

    return ConversationHandler.END

async def track_bnb_token(update: Update, context: ContextTypes.DEFAULT_TYPE, address, name, symbol, min_usd, chat_id):
    """Add a BSC token to tracking"""
    try:
        # Prepare token info
        token_info = {
            "address": address.lower(),
            "name": name,
            "symbol": symbol.upper(),
            "min_volume_usd": float(min_usd),
            "chain": "binance",
            "chat_id": chat_id,
            "added_at": transaction_utils.get_timestamp()
        }

        # Add to data manager
        dm = get_data_manager()
        tokens = dm.data.get("tracked_tokens", [])

        # Check if already tracking
        for token in tokens:
            if token.get("address", "").lower() == address.lower() and str(token.get("chat_id", "")) == str(chat_id):
                await update.message.reply_text(f"⚠️ Token {name} ({symbol}) is already being tracked in this chat.")
                return

        tokens.append(token_info)
        dm.data["tracked_tokens"] = tokens
        dm.save()

        # Save to JSON file
        transaction_utils.add_token_to_file(token_info)

        # Add to BNB monitor
        if bnb_monitor:
            bnb_monitor.add_token(address.lower(), name, symbol, chat_id, min_usd)
            await bnb_monitor.start_tracking(address.lower())

        keyboard = [
            [InlineKeyboardButton("📈 Test Alert", callback_data=f"test_bnb_alert_{address}")],
            [
                InlineKeyboardButton("🔍 View Token", url=f"https://bscscan.com/token/{address}"),
                InlineKeyboardButton("📊 Chart", url=f"https://dexscreener.com/bsc/{address}")
            ]
        ]

        await update.message.reply_text(
            f"✅ Now tracking {name} ({symbol}) on Binance Smart Chain!\n\n"
            f"📝 Address: `{address}`\n"
            f"💵 Min alert value: ${min_usd}\n\n"
            f"You will receive alerts when swaps exceed the minimum value.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error tracking BSC token: {e}")
        await update.message.reply_text(f"❌ Error: Could not track token - {str(e)}")

async def handle_untrack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle untrack callback queries"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "untrack_cancel":
        await query.edit_message_text("🛑 Token removal cancelled.")
        return ConversationHandler.END

    # Extract token address from callback data
    address = data.replace("untrack_", "")

    chat_id = update.effective_chat.id

    # Remove token from tracking
    dm = get_data_manager()
    tokens = dm.data.get("tracked_tokens", [])

    # Find token for this chat
    target_token = None
    for token in tokens:
        if token.get("address", "").lower() == address.lower() and str(token.get("chat_id", "")) == str(chat_id):
            target_token = token
            break

    if not target_token:
        await query.edit_message_text(f"❌ Token `{address}` is not being tracked in this chat.")
        return ConversationHandler.END

    # Remove from data manager
    tokens.remove(target_token)
    dm.data["tracked_tokens"] = tokens
    dm.save()

    # Remove from JSON file
    chain = target_token.get("chain", "ethereum")
    transaction_utils.remove_token_from_file(address, chat_id, chain)

    # Remove from monitor
    if chain == "ethereum" and eth_monitor:
        eth_monitor.remove_token(address, chat_id)
    elif chain == "solana" and sol_monitor:
        sol_monitor.remove_token(address, chat_id)
    elif chain == "binance" and bnb_monitor:
        bnb_monitor.remove_token(address, chat_id)

    await query.edit_message_text(f"✅ Token {target_token.get('name', address)} ({target_token.get('symbol', '???')}) has been removed from tracking.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation."""
    user = update.message.from_user
    logger.info(f"User {user.id} canceled the conversation.")
    await update.message.reply_text("❌ Operation cancelled.")

    # Clear user data
    context.user_data.clear()

    return ConversationHandler.END

def get_track_handler():
    """Return the ConversationHandler for tracking tokens"""
    return ConversationHandler(
        entry_points=[
            CommandHandler("track", track_command),
            CommandHandler("tracksol", tracksol_command),
            CommandHandler("trackbnb", trackbnb_command),
            CommandHandler("untrack", untrack_command),
        ],
        states={
            # Ethereum token states
            ETH_TRACK_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_eth_address),
                CommandHandler("cancel", cancel)
            ],
            ETH_TRACK_STATE + 1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_eth_name),
                CommandHandler("cancel", cancel)
            ],
            ETH_TRACK_STATE + 2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_eth_symbol),
                CommandHandler("cancel", cancel)
            ],
            ETH_TRACK_STATE + 3: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_eth_min_usd),
                CommandHandler("cancel", cancel)
            ],

            # Solana token states
            SOL_TRACK_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sol_address),
                CommandHandler("cancel", cancel)
            ],
            SOL_TRACK_STATE + 1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sol_name),
                CommandHandler("cancel", cancel)
            ],
            SOL_TRACK_STATE + 2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sol_symbol),
                CommandHandler("cancel", cancel)
            ],
            SOL_TRACK_STATE + 3: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sol_min_usd),
                CommandHandler("cancel", cancel)
            ],

            # BSC token states
            BNB_TRACK_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bnb_address),
                CommandHandler("cancel", cancel)
            ],
            BNB_TRACK_STATE + 1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bnb_name),
                CommandHandler("cancel", cancel)
            ],
            BNB_TRACK_STATE + 2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bnb_symbol),
                CommandHandler("cancel", cancel)
            ],
            BNB_TRACK_STATE + 3: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bnb_min_usd),
                CommandHandler("cancel", cancel)
            ],

            # Untrack token state
            UNTRACK_STATE: [
                CallbackQueryHandler(handle_untrack_callback, pattern=r"^untrack_")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="track_handler",
        persistent=False
    )

def get_track_handlers():
    """Return all track-related command handlers"""
    return [
        get_track_handler(),
        CommandHandler("mytokens", mytokens_command)
    ]
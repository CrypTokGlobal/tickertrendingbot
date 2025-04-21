import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters
from boost_manager import get_boost_manager

# Setup logging
logger = logging.getLogger(__name__)

# States for the conversation
SELECTING_TOKEN, SELECTING_PACKAGE, SELECTING_TOKEN, ENTERING_CHAT_LINK, ENTERING_EMOJIS, CONFIRMING_PAYMENT, SELECTING_DURATION, WAITING_PAYMENT = range(8)

# Callback data
SELECT_TOKEN = "select_token"
SELECT_DURATION = "select_duration"
ENTER_CHAT_LINK = "enter_chat_link"
CONFIRM_BOOST = "confirm_boost"
CANCEL_BOOST = "cancel_boost"
BOOST_TOKEN = "boost_token"
BOOST_CHAIN = "boost_chain"

# Duration options (in hours)
DURATION_OPTIONS = {
    "12h": 12,
    "24h": 24,
    "3d": 72,
    "7d": 168
}

# Active boost sessions
active_sessions = {}

async def start_boost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the boost process"""
    user_id = update.effective_user.id

    # Reset the session data
    context.user_data.clear()

    # Create keyboard with tokens user is tracking
    # In a real implementation, we would fetch these from the database
    # For now, we'll ask them to enter a token address

    keyboard = [
        [InlineKeyboardButton("🆕 Enter Token Address", callback_data=f"{SELECT_TOKEN}:manual")],
        [InlineKeyboardButton("❌ Cancel", callback_data=CANCEL_BOOST)]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    message = await update.message.reply_text(
        "🚀 *BOOST YOUR TOKEN* 🚀\n\n"
        "Get your token featured with a customized promotion button on all buy alerts!\n\n"
        "Please select or enter the token you want to boost:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

    # Store the message ID for later updates
    context.user_data['message_id'] = message.message_id

    return SELECTING_TOKEN

async def token_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle token selection"""
    query = update.callback_query
    await query.answer()

    # Extract the token information
    data = query.data.split(':')
    selection_type = data[0]

    if selection_type == CANCEL_BOOST:
        await query.edit_message_text("❌ Boost process cancelled.")
        return ConversationHandler.END

    if selection_type == SELECT_TOKEN and data[1] == "manual":
        await query.edit_message_text(
            "📝 Please enter the token contract address you want to boost:\n\n"
            "Example: 0x1234abcd... or C3DwDjT17gDvvCYC2nsdGHxDHVmQRdhKfpAdqQ29pump"
        )
        return SELECTING_TOKEN

    # If user entered a specific token
    context.user_data['token_address'] = data[1]

    # Display duration selection
    keyboard = []
    for label, hours in DURATION_OPTIONS.items():
        keyboard.append([InlineKeyboardButton(
            f"⏱️ {label} - {calculate_price(hours)} ETH", 
            callback_data=f"{SELECT_DURATION}:{hours}"
        )])

    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=CANCEL_BOOST)])

    await query.edit_message_text(
        "⏱️ *Select Boost Duration*\n\n"
        f"Token: `{context.user_data['token_address']}`\n\n"
        "Choose how long you want your token to be boosted:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

    return SELECTING_DURATION

async def handle_token_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle manually entered token address"""
    token_address = update.message.text.strip()

    # Basic validation (could be enhanced)
    if len(token_address) < 20:
        await update.message.reply_text(
            "⚠️ Invalid token address. Please enter a valid Ethereum or Solana contract address."
        )
        return SELECTING_TOKEN

    context.user_data['token_address'] = token_address

    # Delete user's message with the token to keep chat clean
    try:
        await update.message.delete()
    except Exception:
        pass

    # Display duration selection
    keyboard = []
    for label, hours in DURATION_OPTIONS.items():
        keyboard.append([InlineKeyboardButton(
            f"⏱️ {label} - {calculate_price(hours)} ETH", 
            callback_data=f"{SELECT_DURATION}:{hours}"
        )])

    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=CANCEL_BOOST)])

    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=context.user_data['message_id'],
        text=f"⏱️ *Select Boost Duration*\n\n"
        f"Token: `{token_address}`\n\n"
        "Choose how long you want your token to be boosted:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

    return SELECTING_DURATION

async def duration_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle duration selection"""
    query = update.callback_query
    await query.answer()

    data = query.data.split(':')
    selection_type = data[0]

    if selection_type == CANCEL_BOOST:
        await query.edit_message_text("❌ Boost process cancelled.")
        return ConversationHandler.END

    if selection_type == SELECT_DURATION:
        hours = int(data[1])
        chain = context.user_data.get('chain', 'ethereum')
        context.user_data['duration_hours'] = hours
        context.user_data['price'] = calculate_price(hours, chain)
        currency = "SOL" if chain.lower() == "solana" else "ETH"

        await query.edit_message_text(
            "🔗 *Enter Your Promotion Link*\n\n"
            f"Chain: {chain.upper()}\n"
            f"Token: `{context.user_data['token_address']}`\n"
            f"Duration: {hours} hours\n"
            f"Price: {context.user_data['price']} {currency}\n\n"
            "Please enter the Telegram group or channel link you want to promote:",
            parse_mode='Markdown'
        )

        return ENTERING_CHAT_LINK

async def handle_chat_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle entered chat link"""
    chat_link = update.message.text.strip()

    # Basic validation
    if not (chat_link.startswith('https://t.me/') or chat_link.startswith('http://t.me/')):
        await update.message.reply_text(
            "⚠️ Please enter a valid Telegram link (e.g., https://t.me/yourgroupname)"
        )
        return ENTERING_CHAT_LINK

    context.user_data['chat_link'] = chat_link

    # Delete user's message with the chat link to keep things clean
    try:
        await update.message.delete()
    except Exception:
        pass

    # Get chain info for display
    chain = context.user_data.get('chain', 'ethereum')
    currency = "SOL" if chain.lower() == "solana" else "ETH"

    # Create confirmation keyboard
    keyboard = [
        [InlineKeyboardButton("✅ Confirm & Pay", callback_data=CONFIRM_BOOST)],
        [InlineKeyboardButton("❌ Cancel", callback_data=CANCEL_BOOST)]
    ]

    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=context.user_data['message_id'],
        text="🔍 *Review Your Boost Order*\n\n"
        f"Chain: {chain.upper()}\n"
        f"Token: `{context.user_data['token_address']}`\n"
        f"Duration: {context.user_data['duration_hours']} hours\n"
        f"Promotion Link: {context.user_data['chat_link']}\n"
        f"Price: {context.user_data['price']} {currency}\n\n"
        "Please confirm your boost order:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

    return CONFIRMING_BOOST

async def confirm_boost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle boost confirmation"""
    query = update.callback_query
    await query.answer()

    if query.data == CANCEL_BOOST:
        await query.edit_message_text("❌ Boost process cancelled.")
        return ConversationHandler.END

    if query.data == CONFIRM_BOOST:
        user_id = update.effective_user.id
        chain = context.user_data.get('chain', 'ethereum').lower()

        # Select appropriate wallet address based on chain
        if chain == "ethereum":
            payment_address = "0x247cd53A34b1746C11944851247D7Dd802C1d703"  # ETH address
            currency = "ETH"
            explorer_url = "https://etherscan.io/tx/"
        else:
            payment_address = "DbqdUJmaPgLKkCEhebokxGTuXhzoS7D2SuWxhahi8BYn"  # SOL address
            currency = "SOL"
            explorer_url = "https://solscan.io/tx/"

        # Create a unique payment identifier
        payment_id = f"boost_{user_id}_{chain}_{int(time.time())}"

        # Store payment session
        active_sessions[payment_id] = {
            "user_id": user_id,
            "token_address": context.user_data['token_address'],
            "chain": chain,
            "duration_hours": context.user_data['duration_hours'],
            "chat_link": context.user_data['chat_link'],
            "price": context.user_data['price'],
            "currency": currency,
            "created_at": time.time(),
            "status": "pending"
        }

        # Create payment instructions message
        payment_msg = (
            "💰 *Payment Instructions*\n\n"
            f"Send exactly *{context.user_data['price']} {currency}* to:\n"
            f"`{payment_address}`\n\n"
            "📝 *Important Notes:*\n"
            "• Send from the wallet you want to manage this boost\n"
            "• Your boost will activate automatically once payment is confirmed\n"
            "• The transaction will appear in the bot's notification\n\n"
            "📤 *After sending payment:*\n"
            f"Forward your {chain.upper()} transaction hash here to confirm your boost"
        )

        # Update the message with payment instructions
        await query.edit_message_text(
            text=payment_msg,
            parse_mode='Markdown'
        )

        # Store the session in user data
        context.user_data['payment_id'] = payment_id
        context.user_data['explorer_url'] = explorer_url

        return WAITING_PAYMENT

async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process payment confirmation (transaction hash)"""
    tx_hash = update.message.text.strip()

    payment_id = context.user_data.get('payment_id')
    if not payment_id or payment_id not in active_sessions:
        await update.message.reply_text(
            "⚠️ Your boost session has expired. Please start again with /boost"
        )
        return ConversationHandler.END

    # Get session data including chain info
    session = active_sessions[payment_id]
    token_address = session['token_address']
    chain = session.get('chain', 'ethereum').lower()
    duration_hours = session['duration_hours']
    chat_link = session['chat_link']
    currency = session.get('currency', 'ETH')
    expected_amount = session['price']

    # Send a processing message
    processing_msg = await update.message.reply_text(
        "⏳ Verifying your transaction... Please wait a moment."
    )

    # Chain-specific validation
    payment_verified = False
    if chain == "ethereum":
        if not (tx_hash.startswith('0x') and len(tx_hash) == 66):
            await update.message.reply_text(
                "⚠️ Invalid transaction hash. Please provide a valid Ethereum transaction hash."
            )
            return WAITING_PAYMENT
        explorer_url = f"https://etherscan.io/tx/{tx_hash}"
        payment_verified = await verify_eth_transaction(tx_hash, expected_amount, "0x247cd53A34b1746C11944851247D7Dd802C1d703")

    else:  # solana
        if len(tx_hash) < 43 or len(tx_hash) > 88:
            await update.message.reply_text(
                "⚠️ Invalid transaction hash. Please provide a valid Solana transaction hash."
            )
            return WAITING_PAYMENT
        explorer_url = f"https://solscan.io/tx/{tx_hash}"
        payment_verified = await verify_sol_transaction(tx_hash, expected_amount, "DbqdUJmaPgLKkCEhebokxGTuXhzoS7D2SuWxhahi8BYn")


    # If payment verification failed
    if not payment_verified:
        await processing_msg.edit_text(
            "⚠️ Payment verification failed. Please ensure you sent the exact amount required.\n\n"
            f"Required amount: {expected_amount} {currency}\n"
            f"Recipient address: {'0x247cd53A34b1746C11944851247D7Dd802C1d703' if chain == 'ethereum' else 'DbqdUJmaPgLKkCEhebokxGTuXhzoS7D2SuWxhahi8BYn'}"
        )
        return WAITING_PAYMENT

    # Update the processing message to show verification succeeded
    await processing_msg.edit_text(
        "✅ Transaction verified successfully! Activating your boost..."
    )

    # Add the boost
    boost_manager = get_boost_manager()
    success = boost_manager.add_boost(
        token_address=token_address,
        chat_link=chat_link,
        duration_hours=duration_hours,
        boosted_by=str(update.effective_user.id),
        tx_hash=tx_hash,
        chain=chain
    )

    if success:
        # Update session status
        active_sessions[payment_id]['status'] = 'completed'

        # Send success message
        success_msg = (
            "🎉 *BOOST ACTIVATED SUCCESSFULLY!* 🎉\n\n"
            f"Chain: {chain.upper()}\n"
            f"Token: `{token_address}`\n"
            f"Duration: {duration_hours} hours\n"
            f"Promotion Link: {chat_link}\n"
            f"Transaction: [View on Explorer]({explorer_url})\n\n"
            "Your promotion button is now live and will appear on all buy alerts for this token!\n\n"
            "✅ Boost will expire automatically after the selected duration\n"
            "✅ Check boost status anytime with /my_boosts command"
        )

        await update.message.reply_text(
            success_msg,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    else:
        # Send error message if something went wrong
        await update.message.reply_text(
            "⚠️ There was an error activating your boost. Please contact support."
        )

    # Clean up
    if payment_id in active_sessions:
        del active_sessions[payment_id]

    return ConversationHandler.END

async def cancel_boost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the boost process"""
    user_id = update.effective_user.id

    # Clean up any active sessions for this user
    for session_id, session in list(active_sessions.items()):
        if session.get('user_id') == user_id:
            del active_sessions[session_id]

    await update.message.reply_text("❌ Boost process cancelled.")

    return ConversationHandler.END

async def my_boosts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's active boosts"""
    user_id = str(update.effective_user.id)
    boost_manager = get_boost_manager()

    # Get all active boosts
    all_boosts = boost_manager.list_active_boosts()

    # Filter boosts by this user
    user_boosts = {
        addr: info for addr, info in all_boosts.items()
        if info.get('boosted_by') == user_id
    }

    if not user_boosts:
        await update.message.reply_text(
            "You don't have any active token boosts.\n\n"
            "Start promoting your token with /boost!"
        )
        return

    # Build message with all user's boosts
    boosts_msg = "🚀 *YOUR ACTIVE BOOSTS* 🚀\n\n"

    for addr, info in user_boosts.items():
        expires_at = datetime.fromtimestamp(info.get('expires_at', 0))
        time_left = expires_at - datetime.now()
        days, seconds = time_left.days, time_left.seconds
        hours = days * 24 + seconds // 3600

        boosts_msg += (
            f"*Token:* `{addr}`\n"
            f"*Promoting:* {info.get('chat_link')}\n"
            f"*Expires:* {info.get('expires_at_readable')}\n"
            f"*Time left:* {hours} hours\n\n"
        )

    # Add button to create a new boost
    keyboard = [[InlineKeyboardButton("🆕 Create New Boost", callback_data="new_boost")]]

    await update.message.reply_text(
        boosts_msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_boost_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the 'Create New Boost' button from my_boosts command"""
    query = update.callback_query
    await query.answer()

    if query.data == "new_boost":
        # Start the boost conversation
        await query.message.delete()
        await start_boost(update, context)

def calculate_price(duration_hours: int, chain: str = "ethereum") -> float:
    """Calculate price based on duration and chain"""
    chain = chain.lower()

    if chain == "ethereum":
        # ETH pricing
        if duration_hours == 3:
            return 0.05
        elif duration_hours == 6:
            return 0.08
        elif duration_hours == 12:
            return 0.15
        elif duration_hours == 24:
            return 0.20
        elif duration_hours == 48:
            return 0.30
        else:
            return 0.05

    else:
        # SOL pricing
        if duration_hours == 3:
            return 0.40
        elif duration_hours == 6:
            return 0.75
        elif duration_hours == 12:
            return 1.00
        elif duration_hours == 24:
            return 2.00
        elif duration_hours == 48:
            return 3.00
        else:
            return 0.1


async def handle_boost_token_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle boost token button from alerts"""
    query = update.callback_query
    await query.answer()

    # Extract token data from callback
    data = query.data.split(':')
    if len(data) != 3:
        await query.message.reply_text("❌ Invalid boost request. Please try again.")
        return ConversationHandler.END

    _, chain, token_address = data

    # Store data in user context
    context.user_data['chain'] = chain
    context.user_data['token_address'] = token_address

    # Show chain options buttons
    keyboard = [
        [InlineKeyboardButton(f"💰 Confirm {chain.upper()} Token Boost", callback_data=f"{BOOST_CHAIN}:{chain}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=CANCEL_BOOST)]
    ]

    await query.message.reply_text(
        f"🚀 *BOOST YOUR {chain.upper()} TOKEN* 🚀\n\n"
        f"Token Address: `{token_address}`\n\n"
        "Click below to continue:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

    return SELECTING_DURATION

async def handle_boost_chain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle chain selection for boost"""
    query = update.callback_query
    await query.answer()

    data = query.data.split(':')
    if len(data) != 2:
        await query.message.reply_text("❌ Invalid selection. Please try again.")
        return ConversationHandler.END

    _, chain = data
    context.user_data['chain'] = chain

    # Display duration selection with chain-specific pricing
    keyboard = []
    durations = {"1h": 1, "3h": 3, "6h":6, "12h":12, "24h": 24, "48h":48}

    for label, hours in durations.items():
        price = calculate_price(hours, chain)
        currency = "SOL" if chain.lower() == "solana" else "ETH"
        keyboard.append([InlineKeyboardButton(
            f"⏱️ {label} - {price} {currency}", 
            callback_data=f"{SELECT_DURATION}:{hours}"
        )])

    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=CANCEL_BOOST)])

    await query.edit_message_text(
        "⏱️ *Select Boost Duration*\n\n"
        f"Chain: {chain.upper()}\n"
        f"Token: `{context.user_data.get('token_address')}`\n\n"
        "Choose how long you want your token to be boosted:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

    return SELECTING_DURATION


async def confirm_boost_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Telegram link submission after payment"""
    user_message = update.message.text

    # Check for Telegram link format
    if "t.me/" in user_message or "telegram.me/" in user_message:
        # Extract telegram link - first part of the message
        link_parts = user_message.split()
        telegram_link = link_parts[0]

        # Extract emojis if any (up to 3)
        emojis = ""
        for part in link_parts[1:]:
            # Simple check if part looks like an emoji
            if len(part) <= 4 and not part.isalnum():
                emojis += part + " "

        emojis = emojis.strip()

        # Get boost details from user_data
        network = context.user_data.get("chain") # Assuming chain is stored in user_data now
        duration = context.user_data.get("duration_hours")
        token_address = context.user_data.get("token_address", "")

        if not all([network, duration, token_address]):
            await update.message.reply_text(
                "❌ Boost details missing. Please start the boost process again with /boost command."
            )
            return

        # Process the boost payment (placeholder - needs actual implementation)
        from boost_manager import get_boost_manager
        boost_manager = get_boost_manager()

        success = await boost_manager.process_boost_payment(
            network=network,
            token_address=token_address,
            duration=duration,
            telegram_link=telegram_link,
            emojis=emojis
        )

        if success:
            # Format duration text
            duration_text = str(duration) + " hours" #Simplified duration formatting

            await update.message.reply_text(
                f"✅ Your boost has been activated!\n\n"
                f"🔗 Link: {telegram_link}\n"
                f"⏱️ Duration: {duration_text}\n"
                f"🪙 Token: {token_address[:8]}...{token_address[-6:]}\n\n"
                f"Your link will now appear on all relevant token buy alerts.\n"
                f"Use /my_boosts to check status anytime.",
                parse_mode=ParseMode.HTML
            )

            # Clear user_data
            context.user_data.clear()
        else:
            await update.message.reply_text(
                "❌ There was an issue processing your boost. Please contact an admin."
            )
    else:
        await update.message.reply_text(
            "Please provide a valid Telegram link starting with 't.me/' or 'telegram.me/'"
        )



# Define conversation states
SELECTING_TOKEN = 0
SELECTING_DURATION = 1
ENTERING_CHAT_LINK = 2
CONFIRMING_BOOST = 3
WAITING_PAYMENT = 4

def get_boost_handlers():
    """Return the handlers for the boost system"""

    # Create the conversation handler
    boost_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('boost', start_boost),
            CallbackQueryHandler(handle_boost_token_button, pattern=f"^{BOOST_TOKEN}")
        ],
        states={
            SELECTING_TOKEN: [
                CallbackQueryHandler(token_selected, pattern=f"^({SELECT_TOKEN}|{CANCEL_BOOST})"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_token_address)
            ],
            SELECTING_DURATION: [
                CallbackQueryHandler(handle_boost_chain, pattern=f"^{BOOST_CHAIN}"),
                CallbackQueryHandler(duration_selected, pattern=f"^({SELECT_DURATION}|{CANCEL_BOOST})")
            ],
            ENTERING_CHAT_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat_link)
            ],
            CONFIRMING_BOOST: [
                CallbackQueryHandler(confirm_boost, pattern=f"^({CONFIRM_BOOST}|{CANCEL_BOOST})")
            ],
            WAITING_PAYMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment_confirmation),
                CommandHandler('cancel', cancel_boost),
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'(t\.me|telegram\.me)'), confirm_boost_payment)

            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_boost)],
        per_message=False
    )

    return [
        boost_conv_handler,
        CommandHandler('my_boosts', my_boosts),
        CallbackQueryHandler(handle_boost_button, pattern="^new_boost$")
    ]

# Admin command to manually set a boost
async def admin_boost_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to manually boost a token"""
    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "Usage: /admin_boost <token_address> <duration_hours> <promo_url> [chain]"
            )
            return

        # Default to ethereum if chain not specified
        if len(args) >= 4:
            token_address, duration_hours, promo_url, chain = args[0], int(args[1]), args[2], args[3]
        else:
            token_address, duration_hours, promo_url = args[0], int(args[1]), args[2]
            chain = "ethereum"

        boost_manager = get_boost_manager()
        success = boost_manager.add_boost(
            token_address=token_address,
            chat_link=promo_url,
            duration_hours=duration_hours,
            boosted_by="admin",
            tx_hash=None,
            chain=chain
        )

        if success:
            await update.message.reply_text(
                f"✅ Boost manually activated for {token_address} on {chain} for {duration_hours}h!"
            )
        else:
            await update.message.reply_text("⚠️ Failed to activate boost.")
    except Exception as e:
        logger.error(f"Error in /admin_boost: {e}")
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

# Admin command to remove a boost
async def admin_unboost_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to remove a token boost"""
    try:
        if not context.args:
            await update.message.reply_text("Usage: /admin_unboost <token_address> [chain]")
            return

        # Default to ethereum if chain not specified
        if len(context.args) >= 2:
            token_address, chain = context.args[0], context.args[1]
        else:
            token_address = context.args[0]
            chain = "ethereum"

        boost_manager = get_boost_manager()
        success = boost_manager.remove_boost(token_address, chain)

        if success:
            await update.message.reply_text(f"✅ Boost removed for {token_address} on {chain}")
        else:
            await update.message.reply_text(f"❓ No active boost found for {token_address} on {chain}")
    except Exception as e:
        logger.error(f"Error in /admin_unboost: {e}")
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

# Admin command to list all boosts
async def admin_list_all_boosts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to list all active boosts"""
    try:
        boost_manager = get_boost_manager()
        active_boosts = boost_manager.list_active_boosts()

        if not active_boosts:
            await update.message.reply_text("No active boosts found.")
            return

        boost_msg = "📊 *ALL ACTIVE BOOSTS* 📊\n\n"

        for key, info in active_boosts.items():
            chain = info.get('chain', 'ethereum')
            token_address = key.split(':', 1)[1] if ':' in key else key
            boosted_by = info.get('boosted_by', 'Unknown')
            expires_at = info.get('expires_at_readable', 'Unknown')

            boost_msg += (
                f"*Chain:* {chain.upper()}\n"
                f"*Token:* `{token_address}`\n"
                f"*Promoting:* {info.get('chat_link', 'Unknown')}\n"
                f"*Boosted by:* {boosted_by}\n"
                f"*Expires:* {expires_at}\n\n"
            )

        await update.message.reply_text(
            boost_msg,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in /admin_list_boosts: {e}")
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

def get_admin_boost_handlers():
    """Return the admin handlers for the boost system"""
    return [
        CommandHandler('admin_boost', admin_boost_token),
        CommandHandler('admin_unboost', admin_unboost_token),
        CommandHandler('admin_list_boosts', admin_list_all_boosts)
    ]

async def verify_eth_transaction(tx_hash, expected_amount, to_address):
    """Verify an Ethereum transaction"""
    try:
        # In a real implementation, this would check:
        # 1. Transaction exists and is confirmed
        # 2. Value matches expected amount exactly
        # 3. To address matches our wallet

        logger.info(f"Verifying ETH transaction: {tx_hash}, expected: {expected_amount} ETH, to: {to_address}")

        # Here you would integrate with a blockchain provider like Etherscan API or Web3.py
        # For example:
        # from web3 import Web3
        # web3 = Web3(Web3.HTTPProvider('...'))
        # tx = web3.eth.get_transaction(tx_hash)
        # value_in_eth = web3.from_wei(tx.value, 'ether')
        # if tx.to.lower() != to_address.lower() or abs(value_in_eth - expected_amount) > 0.0001: return False

        # For demo purposes, we'll just return success
        return True
    except Exception as e:
        logger.error(f"Error verifying ETH transaction: {e}")
        return False

async def verify_sol_transaction(tx_hash, expected_amount, to_address):
    """Verify a Solana transaction"""
    try:
        # Similar to ETH, in real implementation this would:
        # 1. Check tx exists and confirmed
        # 2. Value matches expected amount
        # 3. To address matches our wallet

        logger.info(f"Verifying SOL transaction: {tx_hash}, expected: {expected_amount} SOL, to: {to_address}")

        # Here you would integrate with a Solana blockchain provider
        # For example:
        # from solana.rpc.async_api import AsyncClient
        # client = AsyncClient("https://api.mainnet-beta.solana.com")
        # tx = await client.get_transaction(tx_hash)
        # if tx['result']['transaction']['message']['accountKeys'][1] != to_address:
        #     return False

        # For demo purposes, we'll just return success
        return True
    except Exception as e:
        logger.error(f"Error verifying SOL transaction: {e}")
        return False
import logging
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global store for boosted links
boosted_links = []

async def handle_boost_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /boost_token command for submitting token and tx info"""
    # Check if we have enough arguments
    if len(context.args) < 5:
        await update.message.reply_text(
            "❌ Invalid format. Please use:\n\n"
            "/boost_token <network> <token_address> <duration> <tx_hash> <t.me/yourproject>"
        )
        return

    # Parse the arguments
    network = context.args[0].lower()
    token_address = context.args[1]
    duration = context.args[2]
    tx_hash = context.args[3]
    telegram_link = context.args[4]

    # Validate network
    if network not in ["ethereum", "solana", "bnb"]:
        await update.message.reply_text("❌ Invalid network. Choose ethereum, solana, or bnb.")
        return

    # Validate token address format (basic check)
    if network == "ethereum" or network == "bnb":
        if not re.match(r'^0x[a-fA-F0-9]{40}$', token_address):
            await update.message.reply_text("❌ Invalid Ethereum/BNB token address format.")
            return
    elif network == "solana":
        if not len(token_address) >= 32:
            await update.message.reply_text("❌ Invalid Solana token address format.")
            return

    # Validate duration
    try:
        duration_hrs = int(duration)
        if duration_hrs not in [3, 6, 12, 24, 48]:
            await update.message.reply_text("❌ Invalid duration. Choose from: 3, 6, 12, 24, or 48 hours.")
            return
    except ValueError:
        await update.message.reply_text("❌ Duration must be a number.")
        return

    # Validate transaction hash (basic check)
    if network == "ethereum" or network == "bnb":
        if not re.match(r'^0x[a-fA-F0-9]{64}$', tx_hash):
            await update.message.reply_text("❌ Invalid transaction hash format.")
            return
    elif network == "solana":
        if not len(tx_hash) >= 32:
            await update.message.reply_text("❌ Invalid Solana transaction hash format.")
            return

    # Validate Telegram link
    if not telegram_link.startswith("t.me/") and not telegram_link.startswith("https://t.me/"):
        await update.message.reply_text("❌ Invalid Telegram link. It should start with t.me/ or https://t.me/")
        return

    # TODO: Implement actual verification of transaction and payment processing
    # For now, we'll simulate successful verification

    # Add the boosted link to our list
    if not telegram_link.startswith("https://"):
        telegram_link = "https://" + telegram_link

    boosted_links.append(telegram_link)
    logger.info(f"Added new boosted link: {telegram_link}")

    # Store boost data in boost_manager
    try:
        from boost_manager import get_boost_manager
        boost_manager = get_boost_manager()

        # Add the boost to boost manager
        success = boost_manager.add_boost(
            token_address=token_address,
            chat_link=telegram_link,
            duration_hours=int(duration),
            boosted_by=str(update.effective_user.id),
            tx_hash=tx_hash,
            chain=network,
            custom_emojis="🚀🔥💰"  # Default emojis
        )

        if not success:
            logger.error(f"Failed to add boost to boost_manager for {token_address}")
    except Exception as e:
        logger.error(f"Error adding boost to manager: {e}")

    # Create a verifying message with inline keyboard
    keyboard = [
        [InlineKeyboardButton("🔍 View Transaction", url=f"https://{'etherscan.io/tx/' if network in ['ethereum', 'bnb'] else 'solscan.io/tx/'}{tx_hash}")]
    ]

    expiry_time = datetime.now() + timedelta(hours=int(duration))
    expiry_str = expiry_time.strftime("%Y-%m-%d %H:%M UTC")

    await update.message.reply_text(
        f"✅ Thank you! Your boost has been activated.\n\n"
        f"• Network: {network.upper()}\n"
        f"• Token: {token_address}\n"
        f"• Duration: {duration} hours\n"
        f"• Expires: {expiry_str}\n"
        f"• Promoting: {telegram_link}\n\n"
        "Your link will now appear in promotion slots under alerts.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # Log the submission
    logger.info(f"Boost activated: {network} token {token_address} for {duration} hours with tx {tx_hash}, link: {telegram_link}")

async def view_my_boosts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's active boosts"""
    try:
        from boost_manager import get_boost_manager
        boost_manager = get_boost_manager()

        user_id = str(update.effective_user.id)
        boosts = boost_manager.get_user_boosts(user_id)

        if not boosts:
            await update.message.reply_text(
                "You don't have any active boosts. Use /boost to promote your project!"
            )
            return

        message = "🚀 *YOUR ACTIVE BOOSTS* 🚀\n\n"

        for boost in boosts:
            chain = boost.get("chain", "ethereum").upper()
            token = boost.get("token_address", "Unknown")
            expires = boost.get("expires_at_readable", "Unknown")
            link = boost.get("chat_link", "Unknown")

            message += f"*Network:* {chain}\n"
            message += f"*Token:* `{token}`\n"
            message += f"*Expires:* {expires}\n"
            message += f"*Promoting:* {link}\n\n"

        keyboard = [[InlineKeyboardButton("🚀 New Boost", callback_data="boost")]]
        await update.message.reply_text(
            message, 
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in view_my_boosts: {e}")
        await update.message.reply_text("Error retrieving your boosts. Please try again later.")

def get_boosted_links():
    """Return the list of boosted links for use in alerts"""
    return boosted_links

def register_boost_handlers(application):
    """Register boost-related command handlers"""
    logger.info("Registering boost command handlers")
    application.add_handler(CommandHandler("boost_token", handle_boost_token_command))
    application.add_handler(CommandHandler("my_boosts", view_my_boosts))
    application.add_handler(CallbackQueryHandler(view_my_boosts, pattern="^view_my_boosts$"))

import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
import os

# Global dictionary to track boosted tokens
boosted_contracts = {}

logger = logging.getLogger(__name__)

# Import from eth_monitor to share boosted_contracts
try:
    from eth_monitor import boosted_contracts
except ImportError:
    # If not available, use local dictionary
    pass

async def boost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /boost command to display an interactive boost menu"""
    keyboard = [
        [
            InlineKeyboardButton("🔷 Ethereum Tokens", callback_data="boost_eth"),
            InlineKeyboardButton("◎ Solana Tokens", callback_data="boost_sol")
        ],
        [
            InlineKeyboardButton("ℹ️ How Boosting Works", callback_data="boost_info")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🚀 *Token Boost Menu*\n\n"
        "Boost your tokens to partner channels and increase visibility!\n"
        "Select which blockchain your token is on:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return


async def network_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle network selection for boost pricing"""
    query = update.callback_query
    await query.answer()

    network = query.data.split("_")[1]

    if network == "eth":
        pricing = "🟣 *Ethereum Boost Pricing*\n\n" \
                 "• 3 hours: 0.05 ETH\n" \
                 "• 6 hours: 0.08 ETH\n" \
                 "• 12 hours: 0.15 ETH\n" \
                 "• 24 hours: 0.20 ETH\n" \
                 "• 48 hours: 0.30 ETH"
    elif network == "sol":
        pricing = "🔵 *Solana Boost Pricing*\n\n" \
                 "• 3 hours: 0.40 SOL\n" \
                 "• 6 hours: 0.75 SOL\n" \
                 "• 12 hours: 1.00 SOL\n" \
                 "• 24 hours: 2.00 SOL\n" \
                 "• 48 hours: 3.00 SOL"
    else:
        pricing = "Pricing not available for this network."

    keyboard = [
        [InlineKeyboardButton("🚀 Boost Now", callback_data=f"boost_now_{network}")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_boost")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=pricing + "\n\nClick 'Boost Now' to proceed with payment.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def view_boosts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's active boosts"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    user_boosts = []

    for token, data in boosted_contracts.items():
        if data.get("boosted_by") == user_id and data.get("end_time") > datetime.now():
            remaining = data["end_time"] - datetime.now()
            hours = remaining.total_seconds() / 3600
            user_boosts.append({
                "token": token,
                "hours_left": round(hours, 1)
            })

    if user_boosts:
        message = "🚀 *Your Active Boosts:*\n\n"
        for boost in user_boosts:
            short_token = boost["token"][:8] + "..." + boost["token"][-4:]
            message += f"• `{short_token}`: {boost['hours_left']} hours remaining\n"
    else:
        message = "You don't have any active boosts."

    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_boost")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def boost_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information about boosting"""
    query = update.callback_query
    await query.answer()

    help_text = (
        "💡 *About Token Boosting*\n\n"
        "Boosting increases your token's visibility in several ways:\n\n"
        "1️⃣ Your token appears in alert footers across all alerts\n"
        "2️⃣ Priority listing in discovery features\n"
        "3️⃣ Enhanced branding in all your token's alerts\n"
        "4️⃣ 'Powered by tickertrending.com' attribution\n\n"
        "Boosts are time-based and begin immediately after payment confirmation."
    )

    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_boost")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=help_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def back_to_boost_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main boost menu"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🔷 Ethereum Tokens", callback_data="boost_eth"),
         InlineKeyboardButton("◎ Solana Tokens", callback_data="boost_sol")],
        [InlineKeyboardButton("ℹ️ How Boosting Works", callback_data="boost_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "🚀 *Boost your token's visibility!*\n\n"
        "Boosting your token increases its visibility across the TickerTrending network.\n\n"
        "Select a network to see pricing:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_boost_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle boost-related callbacks"""
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    if callback_data.startswith("boost_eth") or callback_data.startswith("boost_sol"):
        # Redirect to network callback
        await network_callback(update, context)
    elif callback_data == "boost_info" or callback_data == "boost_help":
        # Redirect to help callback
        await boost_help_callback(update, context)
    elif callback_data == "view_boosts":
        await view_boosts_callback(update, context)
    elif callback_data == "back_to_boost":
        await back_to_boost_callback(update, context)
    else:
        # Default message for unknown callbacks
        await query.edit_message_text("Unrecognized boost option. Please try again.")

def register_boost_handlers(application):
    """Register all handlers related to boosts"""
    # Add command handler for /boost
    application.add_handler(CommandHandler("boost", boost_command))

    # Add callback handlers for boost-related buttons
    application.add_handler(CallbackQueryHandler(network_callback, pattern="^network_"))
    application.add_handler(CallbackQueryHandler(view_boosts_callback, pattern="^view_boosts"))
    application.add_handler(CallbackQueryHandler(boost_help_callback, pattern="^boost_help"))
    application.add_handler(CallbackQueryHandler(back_to_boost_callback, pattern="^back_to_boost"))
    application.add_handler(CallbackQueryHandler(handle_boost_callback, pattern="^boost_"))
import logging
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode

from boost_manager import get_boost_manager
from boost_menu import verify_eth_transaction, verify_sol_transaction, BOOST_CONFIG

# Set up logging
logger = logging.getLogger(__name__)

async def boost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /boost_token command for simple token boosting"""
    usage_msg = (
        "Usage: `/boost_token <chain> <token_address> <hours> <tx_hash>`\n\n"
        "Available chains: `ethereum` or `solana`\n"
        "Examples:\n"
        "- `/boost_token ethereum 0xabc123... 24 0xtx123...`\n"
        "- `/boost_token solana So1ana123... 24 tx123...`\n\n"
        "💡 For interactive boosting, use `/boost`"
    )

    if len(context.args) < 4:
        await update.message.reply_text(usage_msg, parse_mode=ParseMode.MARKDOWN)
        return

    # Parse arguments
    chain = context.args[0].lower()
    token_address = context.args[1]

    # Validate chain
    if chain not in ["ethereum", "eth", "solana", "sol"]:
        await update.message.reply_text(
            "❌ Invalid chain. Please use `ethereum` or `solana`", 
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Normalize chain name
    if chain == "eth":
        chain = "ethereum"
    elif chain == "sol":
        chain = "solana"

    # Validate address format
    if chain == "ethereum" and (not token_address.startswith("0x") or len(token_address) != 42):
        await update.message.reply_text("❌ Invalid Ethereum address format")
        return
    elif chain == "solana" and (len(token_address) < 32 or len(token_address) > 44):
        await update.message.reply_text("❌ Invalid Solana address format")
        return

    # Parse hours and validate
    try:
        hours = int(context.args[2])
        if hours <= 0:
            raise ValueError("Hours must be positive")
    except ValueError:
        await update.message.reply_text("❌ Hours must be a positive number")
        return

    # Find matching package or closest match
    packages = BOOST_CONFIG.get(chain, {})
    matching_package = None
    closest_package = None
    closest_diff = float('inf')

    for pkg_id, pkg_info in packages.items():
        pkg_hours = pkg_info.get("hours", 0)
        if pkg_hours == hours:
            matching_package = pkg_id
            break

        diff = abs(pkg_hours - hours)
        if diff < closest_diff:
            closest_diff = diff
            closest_package = pkg_id

    if not matching_package:
        # Use closest package if exact match not found
        matching_package = closest_package

    if not matching_package:
        # Fallback if no packages found
        await update.message.reply_text(
            f"❌ No boost package found for {chain} with {hours} hours duration.\n"
            f"Use `/boost` to see available packages."
        )
        return

    # Get package price
    package_info = packages.get(matching_package, {})
    expected_price = package_info.get("price", 0)
    package_hours = package_info.get("hours", 24)

    # Get transaction hash
    tx_hash = context.args[3]

    # Get wallet address
    wallet_address = BOOST_CONFIG.get("wallet_addresses", {}).get(chain, "")

    # Show processing message
    processing_msg = await update.message.reply_text(
        "⏳ Verifying your transaction... This may take a moment."
    )

    # Verify transaction
    if chain == "ethereum":
        success, message = await verify_eth_transaction(tx_hash, expected_price, wallet_address)
    else:
        success, message = await verify_sol_transaction(tx_hash, expected_price, wallet_address)

    if not success:
        await processing_msg.edit_text(
            f"❌ {message}\n\n"
            f"Please ensure you sent exactly {expected_price} {'ETH' if chain == 'ethereum' else 'SOL'} to {wallet_address}"
        )
        return

    # Use community chat link from boost_config or a default
    chat_link = context.args[4] if len(context.args) > 4 else "https://t.me/YourProject"

    # Add the boost
    boost_manager = get_boost_manager()
    custom_emojis = "🚀🔥💰"  # default emojis

    success = boost_manager.add_boost(
        token_address=token_address,
        chat_link=chat_link,
        duration_hours=package_hours,
        boosted_by=str(update.effective_user.id),
        tx_hash=tx_hash,
        chain=chain,
        custom_emojis=custom_emojis
    )

    if success:
        # Format time display
        if package_hours < 24:
            duration_display = f"{package_hours} hours"
        elif package_hours == 24:
            duration_display = "1 day"
        else:
            days = package_hours // 24
            duration_display = f"{days} days"

        # Calculate expiry date
        expiry_date = datetime.now() + timedelta(hours=package_hours)

        # Send success message
        success_msg = (
            f"{custom_emojis} <b>BOOST ACTIVATED SUCCESSFULLY!</b> {custom_emojis}\n\n"
            f"<b>Network:</b> {chain.upper()}\n"
            f"<b>Token:</b> <code>{token_address}</code>\n"
            f"<b>Duration:</b> {duration_display}\n"
            f"<b>Expires:</b> {expiry_date.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            "<b>Your promotion is now live!</b> Your token will appear on all buy alerts across our network.\n\n"
            "Use /my_boosts anytime to check your active promotions!"
        )

        # Create buttons to view transaction
        explorer_base = "https://etherscan.io/tx/" if chain == "ethereum" else "https://solscan.io/tx/"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 View Transaction", url=f"{explorer_base}{tx_hash}")],
            [InlineKeyboardButton("📈 View My Boosts", callback_data="view_my_boosts")]
        ])

        await processing_msg.edit_text(
            success_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

        # Log successful boost
        logger.info(f"NEW BOOST: {chain} token {token_address} boosted by {update.effective_user.id} for {package_hours}h - TX: {tx_hash}")
    else:
        await processing_msg.edit_text(
            "❌ There was an error activating your boost. Please contact support or try again."
        )

async def my_boosts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all active boosts for the current user"""
    boost_manager = get_boost_manager()
    user_id = str(update.effective_user.id)

    # Get boosts for this user
    boosts = boost_manager.get_user_boosts(user_id)

    if not boosts:
        await update.message.reply_text(
            "You don't have any active boosts.\n\n"
            "Use /boost to boost a token!"
        )
        return

    # Create message with all boosts
    msg = "<b>🚀 Your Active Token Boosts:</b>\n\n"

    for boost in boosts:
        token = boost.get("token_address", "Unknown")
        chain = boost.get("chain", "ethereum").upper()

        # Calculate remaining time
        start_time = boost.get("start_time", 0)
        duration_hours = boost.get("duration_hours", 24)
        expiry_time = start_time + (duration_hours * 3600)
        now = datetime.now().timestamp()

        if expiry_time <= now:
            status = "❌ Expired"
        else:
            hours_left = int((expiry_time - now) / 3600)
            status = f"✅ Active ({hours_left}h remaining)"

        # Add boost to message
        msg += f"<b>Token:</b> <code>{token}</code>\n"
        msg += f"<b>Chain:</b> {chain}\n"
        msg += f"<b>Status:</b> {status}\n"

        # Add explorer link based on chain
        if chain == "ETHEREUM":
            explorer = f"https://etherscan.io/token/{token}"
            msg += f"<b>Link:</b> <a href='{explorer}'>View on Etherscan</a>\n"
        else:
            explorer = f"https://solscan.io/token/{token}"
            msg += f"<b>Link:</b> <a href='{explorer}'>View on Solscan</a>\n"

        msg += "\n"

    # Add option to boost more tokens
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Boost Another Token", callback_data="boost_menu")]
    ])

    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

def get_boost_handler_commands():
    """Return all boost handler commands"""
    return [
        CommandHandler("boost_token", boost_command),
        CommandHandler("my_boosts", my_boosts_command)
    ]
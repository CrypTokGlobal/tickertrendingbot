import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from eth_monitor import get_instance as get_eth_monitor

logger = logging.getLogger(__name__)

async def quick_track_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple command to directly track an Ethereum token by address with optional name, symbol and min_usd"""
    chat_id = update.effective_chat.id

    # Parse command arguments
    if not context.args:
        await update.message.reply_text(
            "Usage: `/track <contract_address> [name] [symbol] [min_usd]`\n\n"
            "Examples:\n"
            "• `/track 0x1234abcdef...` - Track with default name/symbol\n"
            "• `/track 0x1234abcdef... MyToken MTK 10` - Track with name, symbol, and $10 minimum",
            parse_mode="Markdown"
        )
        return

    # Get the address (required)
    address = context.args[0].strip()

    # Basic validation
    if not address.startswith("0x") or len(address) != 42:
        await update.message.reply_text(
            "❌ That doesn't look like a valid Ethereum contract address.\n\n"
            "It should start with `0x` and be exactly 42 characters long.",
            parse_mode="Markdown"
        )
        return

    # Get optional parameters (name, symbol, min_usd)
    name = context.args[1] if len(context.args) > 1 else "Tracked Token"
    symbol = context.args[2] if len(context.args) > 2 else "TKN"

    # Parse min_usd if provided
    try:
        min_usd = float(context.args[3]) if len(context.args) > 3 else 10.0
        if min_usd < 0:
            min_usd = 10.0  # Default if negative value
    except (ValueError, TypeError):
        min_usd = 10.0  # Default if parse error

    try:
        # Get the monitor instance through the application's bot
        monitor = get_eth_monitor(context.bot)
        success = monitor.track_contract(
            address=address, 
            name=name, 
            symbol=symbol, 
            chat_id=chat_id,
            min_usd=min_usd
        )

        if success:
            # Add buttons for chart and test
            etherscan_url = f"https://etherscan.io/token/{address}"
            dextools_url = f"https://dexscreener.com/ethereum/{address}"
            keyboard = [
                [InlineKeyboardButton("📊 View Chart", url=dextools_url),
                 InlineKeyboardButton("🔍 Etherscan", url=etherscan_url)],
                [InlineKeyboardButton("🧪 Test Alert", callback_data=f"test_alert_{address}_eth")],
                [InlineKeyboardButton("✨ Customize Token", callback_data=f"customize_{address}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✅ Now tracking *{name}* (*{symbol}*) on Ethereum\n\n"
                f"📋 *Details:*\n"
                f"• Address: `{address}`\n"
                f"• Minimum alert value: ${min_usd}\n"
                f"• Tracking in: This chat\n\n"
                f"🔔 You'll receive alerts when buys are detected for this token.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

            # Inform about other chain support
            await update.message.reply_text(
                "📢 *Note:* For Solana tokens, use `/tracksol <address> [name] [symbol] [min_usd]`.\n"
                "For a guided setup with more options, use `/track_step`.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ Failed to track contract: `{address}`\n\n"
                f"This could be due to an invalid contract or internal error.",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Error tracking contract: {e}")
        await update.message.reply_text(
            f"❌ Error tracking token: {str(e)}\n\n"
            f"Please try again or contact support if the issue persists."
        )

async def test_alert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle test alert button callback"""
    query = update.callback_query
    await query.answer("Preparing test alert...")

    try:
        # Extract token address from callback data
        callback_data = query.data
        parts = callback_data.split("_")

        if len(parts) < 3:
            await query.message.reply_text("⚠️ Invalid test alert data")
            return

        # Extract address and optional chain (defaults to ethereum)
        token_address = parts[2]
        chain = parts[3] if len(parts) > 3 else "ethereum"
        chat_id = update.effective_chat.id

        # Send appropriate test alert based on chain
        success = False

        if chain.lower() in ["ethereum", "eth"]:
            from eth_monitor import test_eth_alert
            success = await test_eth_alert(chat_id, token_address)
        elif chain.lower() in ["solana", "sol"]:
            from solana_monitor import test_sol_alert
            success = await test_sol_alert(chat_id, token_address)
        else:
            await query.message.reply_text(f"⚠️ Unsupported chain: {chain}")
            return

        if success:
            await query.message.reply_text("✅ Test alert sent successfully!")
        else:
            await query.message.reply_text("❌ Failed to send test alert. Please try again later.")
    except Exception as e:
        logger.error(f"Error sending test alert: {e}")
        await query.message.reply_text(f"❌ Error: {str(e)}")

def register_handlers(application):
    """Register all handlers related to quick tracking"""
    # Add command handler for /track
    application.add_handler(CommandHandler("track", quick_track_handler))

    # Add callback handler for test alerts
    application.add_handler(CallbackQueryHandler(test_alert_callback, pattern="^test_alert_"))

    logger.info("✅ Quick track handlers registered")
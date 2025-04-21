
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from solana_monitor import get_instance as get_sol_monitor

logger = logging.getLogger(__name__)

async def quick_track_sol_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple command to directly track a Solana token by address with optional name, symbol and min_usd"""
    chat_id = update.effective_chat.id

    # Parse command arguments
    if not context.args:
        await update.message.reply_text(
            "Usage: `/tracksol <address> [name] [symbol] [min_usd]`\n\n"
            "Examples:\n"
            "• `/tracksol EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` - Track with default name/symbol\n"
            "• `/tracksol EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v USDC USDC 10` - Track with name, symbol, and $10 minimum",
            parse_mode="Markdown"
        )
        return

    # Get the address (required)
    address = context.args[0].strip()

    # Basic validation - Solana addresses are typically base58 encoded and ~32-44 chars
    if len(address) < 32 or len(address) > 44:
        await update.message.reply_text(
            "❌ That doesn't look like a valid Solana address.\n\n"
            "Solana addresses are typically 32-44 characters long.",
            parse_mode="Markdown"
        )
        return

    # Get optional parameters (name, symbol, min_usd)
    name = context.args[1] if len(context.args) > 1 else "Tracked Token"
    symbol = context.args[2] if len(context.args) > 2 else "SOL"

    # Parse min_usd if provided
    try:
        min_usd = float(context.args[3]) if len(context.args) > 3 else 10.0
        if min_usd < 0:
            min_usd = 10.0  # Default if negative value
    except (ValueError, TypeError):
        min_usd = 10.0  # Default if parse error

    try:
        # Get the Solana monitor instance
        sol_monitor = get_sol_monitor(context.bot)
        
        # Add token to monitor
        success = sol_monitor.add_token(
            address=address, 
            name=name, 
            symbol=symbol, 
            group_id=chat_id
        )
        
        # Also save to data manager for persistence
        try:
            from data_manager import add_tracked_token
            add_tracked_token(chat_id, address, name, symbol, min_usd, "solana")
            logger.info(f"💾 Saved Solana token {symbol} to data manager")
        except Exception as e:
            logger.error(f"Failed to save Solana token to data manager: {e}")

        # Add buttons for chart and test
        chart_url = f"https://dexscreener.com/solana/{address}"
        solscan_url = f"https://solscan.io/token/{address}"
        keyboard = [
            [InlineKeyboardButton("📊 View Chart", url=chart_url),
             InlineKeyboardButton("🔍 Solscan", url=solscan_url)],
            [InlineKeyboardButton("🧪 Test Alert", callback_data=f"test_alert_{address}_sol")],
            [InlineKeyboardButton("✨ Customize Token", callback_data=f"customize_{address}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Now tracking *{name}* (*{symbol}*) on Solana\n\n"
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
            "📢 *Note:* For Ethereum tokens, use `/track <address> [name] [symbol] [min_usd]`.\n"
            "For a guided setup with more options, use `/track_step`.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error tracking Solana token: {e}")
        await update.message.reply_text(
            f"❌ Error tracking token: {str(e)}\n\n"
            f"Please try again or contact support if the issue persists."
        )

def register_handlers(application):
    """Register all handlers related to quick Solana tracking"""
    # Add command handler for /tracksol
    application.add_handler(CommandHandler("tracksol", quick_track_sol_handler))
    
    logger.info("✅ Quick Solana track handlers registered")

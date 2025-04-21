import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from data_manager import get_data_manager

# Set up logging
logger = logging.getLogger(__name__)

async def handle_back_to_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to help button press"""
    query = update.callback_query
    await query.answer()

    # Re-display help menu
    text = (
        "🚀 <b>Welcome to <u>TickerTrending Bot</u></b>\n\n"
        "This bot helps <b>track</b> and <b>boost</b> crypto tokens across Telegram.\n\n"
        "🧰 <b>Here's what you can do:</b>\n"
        "• <code>/track</code> – Add ETH token\n"
        "• <code>/tracksol</code> – Add SOL token\n"
        "• <code>/untrack</code> – Remove token\n"
        "• <code>/boost</code> – Promote your token\n"
        "• <code>/customize_token</code> – Add token image, links, emojis\n"
        "• <code>/example_alert</code> – Preview your alert\n"
        "• <code>/stats</code> – Group analytics\n\n"
        "🔗 <i>Powered by <a href='https://tickertrending.com'>TickerTrending.com</a></i>"
    )

    keyboard = [
        [
            InlineKeyboardButton("📈 Track Token", callback_data="track"),
            InlineKeyboardButton("❌ Untrack Token", callback_data="untrack"),
        ],
        [
            InlineKeyboardButton("🚀 Boost Project", callback_data="boost"),
            InlineKeyboardButton("🎨 Customize Alerts", callback_data="customize"),
        ],
        [
            InlineKeyboardButton("📊 View Stats", callback_data="stats"),
            InlineKeyboardButton("🧪 Test Alert", callback_data="example_alert"),
        ],
        [
            InlineKeyboardButton("📄 Contracts Tracked", callback_data="contracts_tracked"),
            InlineKeyboardButton("📘 Full Guide", url="https://tickertrending.com/guide"),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        # If editing fails, send a new message
        logger.error(f"Error handling back button: {e}")
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )

def get_help_callback_handlers():
    """Return all callback handlers for help menu navigation"""
    return [
        CallbackQueryHandler(handle_back_to_help, pattern="^back_to_help$"),
    ]


import logging
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information with beautiful UI"""
    keyboard = [
        [
            InlineKeyboardButton("📈 Track Token", callback_data="track_token"),
            InlineKeyboardButton("❌ Untrack Token", callback_data="untrack_token")
        ],
        [
            InlineKeyboardButton("🚀 Boost Token", callback_data="boost_token"), #This line is changed
            InlineKeyboardButton("🎨 Customize Alerts", callback_data="customize_alerts")
        ],
        [
            InlineKeyboardButton("📊 View Stats", callback_data="view_stats"),
            InlineKeyboardButton("🧪 Test Alert", callback_data="test_alert")
        ],
        [
            InlineKeyboardButton("📋 Tracked Tokens", callback_data="contracts_tracked"),
            InlineKeyboardButton("📚 Full Guide", url="https://tickertrending.com/guide")
        ],
        [
            InlineKeyboardButton("✅ Bot Status Check", callback_data="bot_status_check")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    help_text = (
        "🚀 <b>Welcome to TickerTrending Bot</b>\n\n"
        "This bot helps <b>track</b> and <b>boost</b> crypto tokens across Telegram.\n\n"
        "🧰 <b>Here's what you can do:</b>\n"
        "• <code>/track</code> – Add ETH token\n"
        "• <code>/tracksol</code> – Add SOL token\n"
        "• <code>/untrack</code> – Remove token\n"
        "• <code>/boost</code> – Promote your token\n"
        "• <code>/customize</code> – Add token image, links, emojis\n"
        "• <code>/example_alert</code> – Preview your alert\n"
        "• <code>/stats</code> – Group analytics\n\n"
        "🔗 <i>Powered by</i> <a href='https://tickertrending.com'>TickerTrending.com</a>"
    )

    await update.message.reply_text(
        text=help_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

async def handle_track_token_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle track token button click"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("🟣 Ethereum", callback_data="track_eth"),
            InlineKeyboardButton("🔵 Solana", callback_data="track_sol")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="help_menu")]
    ]

    await query.edit_message_text(
        text="Select a blockchain to track a token:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_untrack_token_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle untrack token button click"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        text="To untrack a token, use the command:\n\n/untrack <token_address>\n\nFor example: /untrack 0x1234...",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help_menu")]])
    )

async def handle_boost_token_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle boost project button click"""
    query = update.callback_query
    await query.answer()

    # Create a rich UI for boosting with all four networks
    keyboard = [
        [
            InlineKeyboardButton("🟣 Ethereum", callback_data="network_eth"),
            InlineKeyboardButton("🔵 Solana", callback_data="network_sol"),
        ],
        [
            InlineKeyboardButton("🟡 BNB", callback_data="network_bnb"),
            InlineKeyboardButton("🟢 Base", callback_data="network_base"),
        ],
        [
            InlineKeyboardButton("ℹ️ How Boosting Works", callback_data="how_boost_works"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="help_menu")]
    ]

    boost_text = (
        "🚀 <b>Boost Your Token's Visibility</b>\n\n"
        "Supercharge your token's reach by boosting it to our partner channels and communities.\n\n"
        "• <b>Increased Exposure</b> across multiple channels\n"
        "• <b>Higher Visibility</b> to potential buyers\n"
        "• <b>Professional Presentation</b> with your branding\n\n"
        "Select which blockchain your token is on:"
    )

    await query.edit_message_text(
        text=boost_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def handle_customize_alerts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle customize alerts button click"""
    query = update.callback_query
    await query.answer()

    template_text = (
        "🎨 <b>Customize Your Token Alerts</b>\n\n"
        "Make your alerts stand out with custom branding:\n\n"
        "• 🖼️ <b>Token Logo</b> - Add your project's logo\n"
        "• 🔗 <b>Website Link</b> - Drive traffic to your site\n"
        "• 💬 <b>Telegram Group</b> - Grow your community\n"
        "• 🐦 <b>Twitter</b> - Connect social media\n"
        "• 😎 <b>Custom Emojis</b> - Add personality\n\n"
        "Use <code>/customize</code> followed by your token address to begin."
    )

    await query.edit_message_text(
        text=template_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help_menu")]])
    )

async def handle_view_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle view stats button click"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        text="📊 <b>Token Statistics</b>\n\nTo view detailed stats about your tracked tokens, use:\n<code>/status</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help_menu")]])
    )

async def handle_test_alert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle test alert button click"""
    query = update.callback_query
    await query.answer()

    # Get tracked tokens for this chat
    from data_manager import get_data_manager
    dm = get_data_manager()
    chat_id = update.effective_chat.id
    tokens = []
    if "tracked_tokens" in dm.data:
        tokens = [t for t in dm.data["tracked_tokens"] if str(t.get("chat_id", "")) == str(chat_id)]

    if not tokens:
        await query.edit_message_text(
            text="⚠️ You don't have any tracked tokens.\n\nPlease track a token first using /track or /tracksol.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help_menu")]])
        )
        return

    # Create buttons for each tracked token
    keyboard = []
    for token in tokens:
        symbol = token.get("symbol", "???")
        address = token.get("address", "")
        network = token.get("network", "ethereum")

        if network == "ethereum":
            callback_data = f"test_alert_{address}"
            emoji = "🟣"
        elif network == "solana":
            callback_data = f"test_sol_alert_{address}"
            emoji = "🔵"
        else:
            callback_data = f"test_bnb_alert_{address}"
            emoji = "🟡"

        keyboard.append([InlineKeyboardButton(
            f"{emoji} Test {symbol} Alert", 
            callback_data=callback_data
        )])

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="help_menu")])

    await query.edit_message_text(
        text="Select a token to generate a test alert:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_contracts_tracked_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle contracts tracked button click"""
    query = update.callback_query
    await query.answer()

    # Get tracked tokens for this chat
    from data_manager import get_data_manager
    dm = get_data_manager()
    chat_id = update.effective_chat.id
    tokens = []
    if "tracked_tokens" in dm.data:
        tokens = [t for t in dm.data["tracked_tokens"] if str(t.get("chat_id", "")) == str(chat_id)]

    if not tokens:
        await query.edit_message_text(
            text="You aren't tracking any tokens yet.\n\nUse /track or /tracksol to add tokens.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help_menu")]])
        )
        return

    # Build message with token list
    message = "🔍 <b>Your Tracked Tokens:</b>\n\n"

    for token in tokens:
        network = token.get('network', 'ethereum')
        network_emoji = "🟣" if network == "ethereum" else "🔵" if network == "solana" else "🟡"

        # Format address for display
        address = token.get('address', '')
        if len(address) > 20:
            display_address = f"{address[:8]}...{address[-6:]}"
        else:
            display_address = address

        min_volume = token.get('min_volume_usd', 10.0)

        message += (
            f"{network_emoji} <b>{token.get('name', '')}</b> ({token.get('symbol', '')})\n"
            f"    Address: <code>{display_address}</code>\n"
            f"    Min Volume: ${min_volume} USD\n\n"
        )

    # Add buttons to manage tokens
    keyboard = [
        [
            InlineKeyboardButton("📈 Add Token", callback_data="track_token"),
            InlineKeyboardButton("❌ Remove Token", callback_data="untrack_token")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="help_menu")]
    ]

    await query.edit_message_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_bot_status_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot status check button click"""
    query = update.callback_query
    await query.answer()

    # Get dashboard status
    try:
        from dashboard import bot_status

        uptime = "Unknown"
        try:
            from datetime import datetime
            start_time = datetime.fromisoformat(bot_status["start_time"])
            uptime_seconds = (datetime.now() - start_time).total_seconds()
            uptime = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m"
        except Exception as e:
            logger.error(f"Error calculating uptime: {e}")

        # Get the Replit URL (will work if running on Replit)
        replit_slug = os.environ.get('REPL_SLUG', '')
        replit_owner = os.environ.get('REPL_OWNER', '')

        if replit_slug and replit_owner:
            dashboard_url = f"https://{replit_slug}.{replit_owner}.repl.co/status"
        else:
            dashboard_url = "http://0.0.0.0:8080/status"

        status_text = (
            f"✅ <b>Bot Status: Online</b>\n"
            f"⏱ Uptime: {uptime}\n"
            f"📊 Tracked Tokens: {sum(len(contracts) for contracts in bot_status.get('tracked_contracts', {}).values())}\n"
            f"📨 Alerts Sent: {bot_status.get('alerts_sent', 0)}\n"
            f"👥 Active Chats: {bot_status.get('telegram_chats', 0)}\n\n"
            f"<a href='{dashboard_url}'>View Full Dashboard</a>"
        )

        keyboard = [
            [InlineKeyboardButton("🌐 Open Dashboard", url=dashboard_url)],
            [InlineKeyboardButton("🔙 Back", callback_data="help_menu")]
        ]
    except:
        # Fallback if dashboard isn't available
        status_text = "✅ <b>Bot Status: Online</b>\n\nDashboard statistics are currently unavailable."
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="help_menu")]]

    await query.edit_message_text(
        text=status_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

async def handle_back_to_help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to help menu button click"""
    query = update.callback_query
    await query.answer()

    # Create help menu directly instead of calling help_command
    keyboard = [
        [
            InlineKeyboardButton("📈 Track Token", callback_data="track_token"),
            InlineKeyboardButton("❌ Untrack Token", callback_data="untrack_token")
        ],
        [
            InlineKeyboardButton("🚀 Boost Token", callback_data="boost_token"),
            InlineKeyboardButton("🎨 Customize Alerts", callback_data="customize_alerts")
        ],
        [
            InlineKeyboardButton("📊 View Stats", callback_data="view_stats"),
            InlineKeyboardButton("🧪 Test Alert", callback_data="test_alert")
        ],
        [
            InlineKeyboardButton("📋 Tracked Tokens", callback_data="contracts_tracked"),
            InlineKeyboardButton("📚 Full Guide", url="https://tickertrending.com/guide")
        ],
        [
            InlineKeyboardButton("✅ Bot Status Check", callback_data="bot_status_check")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    help_text = (
        "🚀 <b>Welcome to TickerTrending Bot</b>\n\n"
        "This bot helps <b>track</b> and <b>boost</b> crypto tokens across Telegram.\n\n"
        "🧰 <b>Here's what you can do:</b>\n"
        "• <code>/track</code> – Add ETH token\n"
        "• <code>/tracksol</code> – Add SOL token\n"
        "• <code>/untrack</code> – Remove token\n"
        "• <code>/boost</code> – Promote your token\n"
        "• <code>/customize</code> – Add token image, links, emojis\n"
        "• <code>/example_alert</code> – Preview your alert\n"
        "• <code>/stats</code> – Group analytics\n\n"
        "🔗 <i>Powered by</i> <a href='https://tickertrending.com'>TickerTrending.com</a>"
    )

    try:
        await query.edit_message_text(
            text=help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error handling back button: {e}")
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=help_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show dashboard link"""
    # Get the Replit URL (will work if running on Replit)
    replit_slug = os.environ.get('REPL_SLUG', '')
    replit_owner = os.environ.get('REPL_OWNER', '')

    if replit_slug and replit_owner:
        dashboard_url = f"https://{replit_slug}.{replit_owner}.repl.co/status"
    else:
        dashboard_url = "http://0.0.0.0:8080/status"

    keyboard = [[InlineKeyboardButton("🌐 Open Dashboard", url=dashboard_url)]]

    await update.message.reply_html(
        f"📊 <b>Bot Dashboard</b>\n\n"
        f"Access the dashboard to view bot statistics, tracked tokens, and more.\n\n"
        f"<a href='{dashboard_url}'>Click here to open the dashboard</a>",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def get_help_handlers():
    """Return all help-related command and callback handlers"""
    return [
        CommandHandler("help", help_command),
        CommandHandler("dashboard", dashboard_command),
        CallbackQueryHandler(handle_track_token_callback, pattern="^track_token$"),
        CallbackQueryHandler(handle_untrack_token_callback, pattern="^untrack_token$"),
        CallbackQueryHandler(handle_boost_token_callback, pattern="^boost_token$"),
        CallbackQueryHandler(handle_customize_alerts_callback, pattern="^customize_alerts$"),
        CallbackQueryHandler(handle_view_stats_callback, pattern="^view_stats$"),
        CallbackQueryHandler(handle_test_alert_callback, pattern="^test_alert$"),
        CallbackQueryHandler(handle_contracts_tracked_callback, pattern="^contracts_tracked$"),
        CallbackQueryHandler(handle_bot_status_check, pattern="^bot_status_check$"),
        CallbackQueryHandler(handle_back_to_help_menu, pattern="^help_menu$"),
    ]
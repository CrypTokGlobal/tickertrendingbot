import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from data_manager import get_tokens_by_network

# Set up logging
logger = logging.getLogger(__name__)

def get_main_menu_keyboard():
    """Return the main menu keyboard markup"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔖 Track Token", callback_data="track_token"),
            InlineKeyboardButton("❌ Untrack Token", callback_data="untrack_token")
        ],
        [
            InlineKeyboardButton("🚀 Boost Project", callback_data="boost_token"),
            InlineKeyboardButton("🎨 Customize Alerts", callback_data="customize_alerts")
        ],
        [
            InlineKeyboardButton("📊 View Stats", callback_data="view_stats"),
            InlineKeyboardButton("✏️ Test Alert", callback_data="test_alert")
        ],
        [
            InlineKeyboardButton("🔗 Contracts Tracking", callback_data="contracts_tracking"),
            InlineKeyboardButton("📚 Full Guide", url="https://tickertrending.com/guide")
        ],
        [
            InlineKeyboardButton("✅ Bot Status Check", callback_data="bot_status_check")
        ]
    ])

def get_track_network_keyboard():
    """Return keyboard for selecting blockchain network to track"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟣 Ethereum", callback_data="track_eth"),
            InlineKeyboardButton("🔵 Solana", callback_data="track_sol")
        ],
        [
            InlineKeyboardButton("🟡 BNB", callback_data="track_bnb"),
            InlineKeyboardButton("🟢 Base", callback_data="track_base")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="help_menu")]
    ])

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()

    data = query.data
    logger.info(f"Button callback received: {data}")

    # Test alert handling
    if data.startswith("test_alert_") or data.startswith("test_sol_alert_") or data.startswith("test_bnb_alert_"):
        await handle_test_token_alert(update, context)
        return

    # Main menu and navigation
    if data == "help_menu" or data == "back_to_main":
        try:
            await query.edit_message_text(
                text="🚀 <b>Welcome to <u>TickerTrending Bot</u></b>\n\n"
                "This bot helps <b>track</b> and <b>boost</b> crypto tokens across Telegram.\n\n"
                "🧰 <b>Here's what you can do:</b>\n"
                "• <code>/track</code> – Add ETH token\n"
                "• <code>/tracksol</code> – Add SOL token\n"
                "• <code>/untrack</code> – Remove token\n"
                "• <code>/boost</code> – Promote your token\n"
                "• <code>/customize_token</code> – Add token image, links, emojis\n"
                "• <code>/example_alert</code> – Preview your alert\n"
                "• <code>/stats</code> – Group analytics\n\n"
                "🔗 <i>Powered by <a href='https://tickertrending.com'>TickerTrending.com</a></i>",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Error going back to main menu: {e}")
            if update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⚠️ There was an error. Let's start fresh.",
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="HTML"
                )
        return

    # Track token flow
    elif data == "track_token":
        await query.edit_message_text(
            text="Select a blockchain to track a token:",
            reply_markup=get_track_network_keyboard()
        )
        return

    # Untrack token flow
    elif data == "untrack_token":
        await query.edit_message_text(
            text="To untrack a token, use the command:\n\n/untrack <token_address>\n\nFor example: /untrack 0x1234...",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help_menu")]])
        )
        return

    # Boost project flow
    elif data == "boost_token":
        from boost_menu import handle_boost_selection
        await handle_boost_selection(update, context)
        return

    # Customize alerts flow
    elif data == "customize_alerts":
        template_text = (
            "🎨 Let's customize how your token alerts will appear!\n\n"
            "You can provide information in two ways:\n"
            "1️⃣ Answer questions step-by-step\n"
            "2️⃣ Paste all information at once using this template:\n\n"
            "Name: YourToken\n"
            "Symbol: TOK\n"
            "Contract: 0x1234... or Sol1...\n"
            "Telegram: https://t.me/yourgroup\n"
            "Website: https://yourtoken.com\n"
            "Twitter: https://twitter.com/yourtoken\n"
            "Image: https://yourtoken.com/logo.png\n"
            "Emojis: 🚀💎✨\n\n"
            "What's the name of your token? (e.g. 'PumpToken')"
        )

        await query.edit_message_text(
            text=template_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help_menu")]])
        )
        return

    # View stats flow
    elif data == "view_stats":
        eth_tokens = get_tokens_by_network("eth")
        sol_tokens = get_tokens_by_network("sol")

        stats_text = "📊 **Tracked Tokens:**\n\n"
        if eth_tokens:
            stats_text += "**Ethereum:**\n"
            for token in eth_tokens:
                stats_text += f"- {token['name']} ({token['symbol']}): {token['address']}\n"
        else:
            stats_text += "No Ethereum tokens tracked.\n"

        if sol_tokens:
            stats_text += "\n**Solana:**\n"
            for token in sol_tokens:
                stats_text += f"- {token['name']} ({token['symbol']}): {token['address']}\n"
        else:
            stats_text += "No Solana tokens tracked.\n"

        await query.edit_message_text(
            text=stats_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help_menu")]])
        )
        return

    # Test alert flow
    elif data == "test_alert":
        await query.edit_message_text(
            text="⚙️ To test alert notifications for your token, use: /example_alert <token_address>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help_menu")]])
        )
        return

    # Contracts tracking flow
    elif data == "contracts_tracking":
        tracking_info = (
            "🔍 <b>Blockchain Contract Tracking</b>\n\n"
            "<b>Ethereum Network:</b>\n"
            "• Tracks UniswapV2 & V3 swaps in real-time\n"
            "• Detects buys under your set threshold\n"
            "• Alerts include full tx data and links\n\n"
            "<b>Solana Network:</b>\n"
            "• Tracks Raydium, Jupiter & Orca swaps\n"
            "• Near-instant trade detection\n"
            "• Full transaction details with USD value"
        )

        await query.edit_message_text(
            text=tracking_info,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help_menu")]])
        )
        return

    # Bot status check flow
    elif data == "bot_status_check":
        from help_handler import handle_bot_status_check
        await handle_bot_status_check(update, context)
        return

    # Network selection handlers
    elif data == "track_eth":
        # Handle tracking ETH token
        await query.edit_message_text(
            text="To track an Ethereum token, use command:\n\n/track 0xADDRESS TokenName SYMBOL 5\n\nFor example:\n/track 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984 Uniswap UNI 10",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="track_token")]])
        )
        return

    elif data == "track_sol":
        # Handle tracking SOL token
        await query.edit_message_text(
            text="To track a Solana token, use command:\n\n/tracksol ADDRESS TokenName SYMBOL 5\n\nFor example:\n/tracksol EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v USDC USDC 10",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="track_token")]])
        )
        return

    # Handle any unimplemented button presses
    else:
        await query.edit_message_text(
            f"🚧 The feature for <b>{data}</b> is under construction.\n\n"
            "Stay tuned! 🚀",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help_menu")]])
        )
        return

def get_button_handlers():
    """Return all button handler for Telegram callback queries"""
    return [
        CallbackQueryHandler(button_handler)
    ]
def register_button_handlers(application):
    """Register all button handlers with the application"""
    logger.info("Registering button handlers")
    for handler in get_button_handlers():
        application.add_handler(handler)

async def handle_test_token_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a test alert for a specific token"""
    query = update.callback_query
    await query.answer("Generating test alert...")

    try:
        # Extract token address from callback data
        data = query.data

        if data.startswith("test_alert_"):
            address = data.replace("test_alert_", "")
            network = "ethereum"
        elif data.startswith("test_sol_alert_"):
            address = data.replace("test_sol_alert_", "")
            network = "solana"
        elif data.startswith("test_bnb_alert_"):
            address = data.replace("test_bnb_alert_", "")
            network = "binance"
        else:
            await query.edit_message_text("❌ Invalid token identifier")
            return

        # Get token info from data manager
        from data_manager import get_data_manager
        dm = get_data_manager()
        tokens = dm.data.get("tracked_tokens", [])
        chat_id = query.message.chat_id

        # Find token for this chat
        target_token = None
        for token in tokens:
            if token.get("address", "").lower() == address.lower() and str(token.get("chat_id", "")) == str(chat_id) and token.get("network", "") == network:
                target_token = token
                break

        if not target_token:
            await query.edit_message_text(f"❌ Token `{address}` is not being tracked in this chat.")
            return

        # Generate test alert based on network
        if network == "ethereum":
            from eth_monitor import test_eth_alert
            await test_eth_alert(chat_id, target_token)
        elif network == "solana":
            # Handle solana test alert
            from utils import send_solana_test_alert
            if "send_solana_test_alert" in dir():
                await send_solana_test_alert(context.bot, chat_id, target_token)
            else:
                # Fallback
                await query.edit_message_text("Solana test alerts not yet implemented. Coming soon!")
                return
        elif network == "binance":
            # Handle binance test alert
            from utils import send_bsc_test_alert
            if "send_bsc_test_alert" in dir():
                await send_bsc_test_alert(context.bot, chat_id, target_token)
            else:
                # Fallback
                await query.edit_message_text("BSC test alerts not yet implemented. Coming soon!")
                return

        # Show success message with back button
        await query.edit_message_text(
            f"✅ Test alert sent for {target_token.get('name', '')} ({target_token.get('symbol', '')})",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help_menu")]])
        )

    except Exception as e:
        logger.error(f"Error generating test alert: {e}")
        await query.edit_message_text(
            f"❌ Error generating test alert: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help_menu")]])
        )
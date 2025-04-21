import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# Set up logging
logger = logging.getLogger(__name__)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    data = query.data

    # First, acknowledge the button press
    await query.answer()

    # Handle test alert button
    if data == "test_alert":
        from eth_monitor import get_instance
        monitor = get_instance(context.bot)
        if monitor:
            await query.edit_message_text("🚀 Sending test alert...")
            # Use the dashboard test alert endpoint
            import requests
            try:
                response = requests.get("http://0.0.0.0:8001/test_alert")
                if response.status_code == 200:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id, 
                        text="✅ Test alert sent successfully!"
                    )
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id, 
                        text=f"❌ Failed to send test alert: {response.text}"
                    )
            except Exception as e:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text=f"❌ Error sending test alert: {str(e)}"
                )
    # Handle other button presses
    elif data.startswith("track_"):
        # Pass to appropriate tracking handler
        parts = data.split("_")
        if len(parts) > 1:
            chain = parts[1]
            if chain == "eth":
                await query.edit_message_text("🟣 Please send the Ethereum token contract address you'd like to track.")
            elif chain == "sol":
                await query.edit_message_text("🔵 Please send the Solana token contract address you'd like to track.")
            elif chain == "bnb":
                await query.edit_message_text("🟡 Please send the BNB token contract address you'd like to track.")
    else:
        # Default behavior - just show what was pressed
        await query.edit_message_text(text=f"Selected option: {query.data}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alias for callback_handler for backward compatibility"""
    return await callback_handler(update, context)

def get_callback_handlers():
    """Return the callback query handler"""
    return [CallbackQueryHandler(callback_handler)]

async def handle_network_sol_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle network_sol callback from UI buttons"""
    query = update.callback_query
    await query.answer()

    # Redirect to the boost selection handler
    from boost_menu import handle_boost_selection
    await handle_boost_selection(update, context)

async def handle_network_eth_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle network_eth callback from UI buttons"""
    query = update.callback_query
    await query.answer()

    # Redirect to the boost selection handler
    from boost_menu import handle_boost_selection
    await handle_boost_selection(update, context)

async def handle_how_boost_works_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle how_boost_works callback from UI buttons"""
    query = update.callback_query
    await query.answer()

    # Redirect to the boost info handler
    from boost_menu import show_how_boost_works
    await show_how_boost_works(update, context)

async def handle_boost_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle boost_back callback from UI buttons"""
    query = update.callback_query
    await query.answer()
    
    # Redirect to the boost menu
    from boost_menu import handle_boost_back
    await handle_boost_back(update, context)

def get_callback_handlers():
    """Return all callback handlers for UI interactions"""
    callback_handlers = [
        # Network selection handlers (these should be processed first)
        CallbackQueryHandler(handle_network_sol_callback, pattern="^network_sol$"),
        CallbackQueryHandler(handle_network_eth_callback, pattern="^network_eth$"),
        CallbackQueryHandler(handle_how_boost_works_callback, pattern="^how_boost_works$"),
        CallbackQueryHandler(handle_boost_back_callback, pattern="^boost_back$"),
    ]

    return callback_handlers
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

async def handle_track_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle track button press"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("🔵 Solana Token", callback_data="add_sol_token"),
            InlineKeyboardButton("🟣 Ethereum Token", callback_data="add_eth_token")
        ],
        [
            InlineKeyboardButton("🔙 Back to Help", callback_data="back_to_help")
        ]
    ]

    await query.edit_message_text(
        "Choose a blockchain network to track a token:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_untrack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle untrack button press"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "To untrack a token, use this command:\n\n"
        "<code>/untrack tokenAddress</code>\n\n"
        "Example: <code>/untrack 0x1234...5678</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back to Help", callback_data="back_to_help")
        ]])
    )

async def handle_boost_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle boost button press"""
    query = update.callback_query
    await query.answer()

    # Redirect to boost handler
    from utils import handle_boost_button
    await handle_boost_button(update, context)

async def handle_customize_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle customize button press"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🎨 <b>Customize Your Token Alerts</b>\n\n"
        "You can add:\n"
        "• Custom token logo\n"
        "• Website link\n"
        "• Telegram group\n"
        "• Twitter profile\n"
        "• Custom emojis\n\n"
        "Use /customize_token to start customizing.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back to Help", callback_data="back_to_help")
        ]])
    )

async def handle_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stats button press"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📊 <b>Token Stats</b>\n\n"
        "Use /stats to view analytics for your tokens including:\n"
        "• Total buy transactions\n"
        "• 24h volume\n"
        "• Price movement\n"
        "• Holder count",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back to Help", callback_data="back_to_help")
        ]])
    )

async def handle_example_alert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle example alert button press"""
    query = update.callback_query
    await query.answer()

    # Create a sample token for the example
    sample_token = {
        "address": "0x1234567890abcdef1234567890abcdef12345678",
        "name": "Sample Token",
        "symbol": "SMPL",
        "network": "ethereum"
    }

    # Send example alert for the token
    from utils import send_eth_test_alert
    await send_eth_test_alert(context.bot, update.effective_chat.id, sample_token)

    # Show back button
    await query.edit_message_text(
        "👆 That's an example alert! Use /customize_token to change how your alerts look.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back to Help", callback_data="back_to_help")
        ]])
    )

async def handle_contracts_tracked_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle contracts tracked button press"""
    query = update.callback_query
    await query.answer()

    # Get the tracked tokens for this chat
    from data_manager import list_tracked_tokens
    chat_id = update.effective_chat.id
    tokens = list_tracked_tokens(chat_id)

    if not tokens:
        await query.edit_message_text(
            "You aren't tracking any tokens yet.\n\n"
            "Use /track or /tracksol to add tokens.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Help", callback_data="back_to_help")
            ]])
        )
        return

    # Build message with token list
    message = "🔍 <b>Your Tracked Tokens:</b>\n\n"

    for token in tokens:
        network = token.get('network', 'ethereum')
        network_emoji = "🟣" if network == "ethereum" else "🔵"

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

    await query.edit_message_text(
        message,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back to Help", callback_data="back_to_help")
        ]])
    )

async def handle_back_to_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back button press"""
    query = update.callback_query
    await query.answer()

    # Re-display help menu
    from help_handler import help_command
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
        logging.error(f"Error handling back button: {e}")
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )

def get_callback_handlers():
    """Return all callback handlers for help menu buttons"""
    return [
        CallbackQueryHandler(handle_track_callback, pattern="^track$"),
        CallbackQueryHandler(handle_untrack_callback, pattern="^untrack$"),
        CallbackQueryHandler(handle_boost_callback, pattern="^boost$"),
        CallbackQueryHandler(handle_customize_callback, pattern="^customize$"),
        CallbackQueryHandler(handle_stats_callback, pattern="^stats$"),
        CallbackQueryHandler(handle_example_alert_callback, pattern="^example_alert$"),
        CallbackQueryHandler(handle_contracts_tracked_callback, pattern="^contracts_tracked$"),
        CallbackQueryHandler(handle_back_to_help, pattern="^back_to_help$"),
    ]

async def test_alert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a test alert for a token"""
    query = update.callback_query
    await query.answer("Generating test alert...")

    try:
        # Extract token address from callback data
        data = query.data

        if data.startswith("test_alert_"):
            address = data.replace("test_alert_", "")
            chain = "ethereum"
        elif data.startswith("test_sol_alert_"):
            address = data.replace("test_sol_alert_", "")
            chain = "solana"
        elif data.startswith("test_bnb_alert_"):
            address = data.replace("test_bnb_alert_", "")
            chain = "binance"
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
            if token.get("address", "").lower() == address.lower() and str(token.get("chat_id", "")) == str(chat_id) and token.get("chain", "") == chain:
                target_token = token
                break

        if not target_token:
            await query.edit_message_text(f"❌ Token `{address}` is not being tracked in this chat.")
            return

        # Generate test alert based on chain
        if chain == "ethereum":
            from eth_monitor import send_eth_alert
            await send_eth_alert(
                bot=context.bot,
                chat_id=chat_id,
                symbol=target_token.get("symbol", "???"),
                amount=1.5,
                tx_hash="0xexample" + address[-8:],
                token_info=target_token,
                usd_value=3000,
                dex_name="Uniswap (Test Alert)"
            )
        elif chain == "solana":
            from solana_monitor import send_solana_alert
            await send_solana_alert(
                bot=context.bot,
                token_info=target_token,
                chain="solana",
                value_token=2.5,
                value_usd=150,
                tx_hash="example" + address[-8:],
                dex_name="Raydium (Test Alert)"
            )
        elif chain == "binance":
            from bsc_monitor import send_bnb_alert
            await send_bnb_alert(
                bot=context.bot,
                chat_id=chat_id,
                symbol=target_token.get("symbol", "???"),
                amount=1.5,
                tx_hash="0xexample" + address[-8:],
                token_info=target_token,
                usd_value=3000,
                dex_name="PancakeSwap (Test Alert)"
            )

        # Update the original message
        await query.edit_message_text(
            f"✅ Test alert sent for {target_token.get('name', '')} ({target_token.get('symbol', '')})",
            reply_markup=query.message.reply_markup
        )

    except Exception as e:
        logging.error(f"Error generating test alert: {e}")
        await query.edit_message_text(f"❌ Error generating test alert: {str(e)}")

    # Handle in the callback_manager
    await callback_manager.handle_callback(update, context)
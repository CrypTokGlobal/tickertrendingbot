import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.constants import ParseMode

# Set up logging
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome new users with an engaging start message and UI"""
    user = update.effective_user

    # Premium welcome message with rich formatting
    welcome_text = (
        f"🚀 <b>Welcome to BuyBot Alert, {user.first_name}!</b>\n\n"
        f"I'm your personal crypto monitoring assistant, designed to help you track and boost tokens across multiple blockchains.\n\n"
        f"<b>🔍 What I can do for you:</b>\n"
        f"• Monitor token transactions in real-time\n"
        f"• Send custom alerts when significant buys happen\n"
        f"• Promote your project to partner channels\n"
        f"• Track tokens across ETH, SOL and more\n\n"
        f"<i>Get started by selecting an option below:</i>"
    )

    # Create an attractive, user-friendly keyboard layout
    keyboard = [
        [
            InlineKeyboardButton("🔎 Start Tracking", callback_data="start_tracking"),
            InlineKeyboardButton("📊 Dashboard", callback_data="open_dashboard")
        ],
        [
            InlineKeyboardButton("🚀 Boost Token", callback_data="boost_token"),
            InlineKeyboardButton("🎮 Quick Tour", callback_data="quick_tour")
        ],
        [
            InlineKeyboardButton("🛠️ Commands List", callback_data="view_commands"),
            InlineKeyboardButton("❓ Help Center", callback_data="help_menu")
        ],
        [
            InlineKeyboardButton("🌐 Visit Website", url="https://tickertrending.com")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Handle the logo image path
    import os
    logo_path = "attached_assets/buybot_logo.jpg"

    # Ensure the directory exists
    os.makedirs("attached_assets", exist_ok=True)

    # If you don't have the correct logo file saved yet, create it from the existing file in your project
    if not os.path.exists(logo_path):
        try:
            # Try to copy from the previous chat uploaded image if it exists
            import shutil
            if os.path.exists("attached_assets/IMAGE 2025-04-20 20:15:03_1745195098952.jpg"):
                shutil.copy("attached_assets/IMAGE 2025-04-20 20:15:03_1745195098952.jpg", logo_path)
            else:
                # Use any existing image as fallback
                for filename in os.listdir("attached_assets"):
                    if filename.endswith((".jpg", ".jpeg", ".png")) and "buybot" in filename.lower():
                        shutil.copy(f"attached_assets/{filename}", logo_path)
                        break
        except Exception as e:
            logger.error(f"Error preparing logo image: {e}")

    # Send the image with caption and inline keyboard
    try:
        with open(logo_path, "rb") as logo_file:
            await update.message.reply_photo(
                photo=logo_file,
                caption=welcome_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Failed to send image: {e}")
        # Fallback to text-only message if image sending fails
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

async def handle_start_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Start Tracking button click"""
    query = update.callback_query
    await query.answer()

    # Create network selection buttons with full options matching boost menu
    keyboard = [
        [
            InlineKeyboardButton("🟣 Ethereum", callback_data="track_eth"),
            InlineKeyboardButton("🔵 Solana", callback_data="track_sol")
        ],
        [
            InlineKeyboardButton("🟡 BNB", callback_data="track_bnb"),
            InlineKeyboardButton("🟢 Base", callback_data="track_base")
        ],
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")
        ]
    ]

    tracking_text = (
        "🔍 <b>Choose a Network to Track</b>\n\n"
        "Select which blockchain you want to monitor tokens on.\n"
        "Each network offers real-time tracking of significant transactions."
    )

    await query.edit_message_text(
        tracking_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Dashboard button click"""
    query = update.callback_query
    await query.answer()

    # Get Replit URL
    import os
    replit_slug = os.environ.get('REPL_SLUG', '')
    replit_owner = os.environ.get('REPL_OWNER', '')

    if replit_slug and replit_owner:
        dashboard_url = f"https://{replit_slug}.{replit_owner}.repl.co/status"
    else:
        dashboard_url = "http://0.0.0.0:8080/status"

    dashboard_text = (
        "📊 <b>Performance Dashboard</b>\n\n"
        "Get real-time stats about your tracked tokens, alerts, and system status.\n\n"
        "• View all tracked tokens\n"
        "• Check system performance\n"
        "• Monitor alert history\n"
        "• See active blockchain connections"
    )

    keyboard = [
        [InlineKeyboardButton("🌐 Open Dashboard", url=dashboard_url)],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
    ]

    await query.edit_message_text(
        dashboard_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def handle_quick_tour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Quick Tour button click"""
    query = update.callback_query
    await query.answer()

    tour_text = (
        "🎮 <b>Quick Tour - Getting Started</b>\n\n"
        "<b>Step 1:</b> Track a token using /track followed by address\n"
        "<b>Step 2:</b> Customize your alerts with /customize\n"
        "<b>Step 3:</b> Get real-time notifications on significant buys\n"
        "<b>Step 4:</b> Boost your token for maximum visibility\n\n"
        "You can view a complete guide with examples by selecting the button below."
    )

    keyboard = [
        [InlineKeyboardButton("📚 Full User Guide", url="https://tickertrending.com/guide")],
        [InlineKeyboardButton("▶️ Next: Basic Commands", callback_data="tour_commands")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
    ]

    await query.edit_message_text(
        tour_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def handle_commands_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Command List button click"""
    query = update.callback_query
    await query.answer()

    commands_text = (
        "🛠️ <b>Essential Commands</b>\n\n"
        "<code>/track</code> - Track Ethereum token\n"
        "<code>/tracksol</code> - Track Solana token\n"
        "<code>/untrack</code> - Stop tracking a token\n"
        "<code>/boost</code> - Promote your token\n"
        "<code>/customize</code> - Personalize alerts\n"
        "<code>/status</code> - Check system status\n"
        "<code>/help</code> - View detailed help\n\n"
        "For a complete list of commands, check COMMANDS.md on our GitHub repository."
    )

    keyboard = [
        [InlineKeyboardButton("📋 Full Commands List", callback_data="full_commands")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")]
    ]

    await query.edit_message_text(
        commands_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def handle_full_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Full Commands List button click"""
    query = update.callback_query
    await query.answer()

    # Read from COMMANDS.md
    try:
        with open("COMMANDS.md", "r") as file:
            content = file.read()
            # Just take the first part to avoid message too long
            if len(content) > 1000:
                content = content[:1000] + "...\n\nUse the button below to see all commands."
    except:
        content = "Could not load commands file."

    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="view_commands")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_start")]
    ]

    await query.edit_message_text(
        f"📋 <b>Commands Reference</b>\n\n<pre>{content}</pre>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def handle_tour_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the next step in the tour"""
    query = update.callback_query
    await query.answer()

    tour_commands_text = (
        "🛠️ <b>Basic Commands - Quick Tour</b>\n\n"
        "• <code>/track 0x1234...abcd TokenName TKN</code>\n"
        "  Track any Ethereum token\n\n"
        "• <code>/tracksol Addr1234 TokenName TKN</code>\n"
        "  Track any Solana token\n\n"
        "• <code>/example_alert</code>\n"
        "  See what alerts look like\n\n"
        "• <code>/boost</code>\n"
        "  Promote your token to our network"
    )

    keyboard = [
        [InlineKeyboardButton("◀️ Previous", callback_data="quick_tour")],
        [InlineKeyboardButton("▶️ Next: Customization", callback_data="tour_custom")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_start")]
    ]

    await query.edit_message_text(
        tour_commands_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def handle_tour_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the customization part of the tour"""
    query = update.callback_query
    await query.answer()

    tour_custom_text = (
        "🎨 <b>Customizing Alerts - Quick Tour</b>\n\n"
        "Make your alerts stand out with branding:\n\n"
        "• Add your token logo\n"
        "• Include website and social links\n"
        "• Choose custom emojis\n"
        "• Add animated GIFs\n\n"
        "Use <code>/customize</code> followed by your token address to begin personalizing your alerts."
    )

    keyboard = [
        [InlineKeyboardButton("◀️ Previous", callback_data="tour_commands")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_start")]
    ]

    await query.edit_message_text(
        tour_custom_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def handle_back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Back to Menu button click"""
    query = update.callback_query
    await query.answer()

    # Just call the start command logic again
    user = update.effective_user
    welcome_text = (
        f"🚀 <b>Welcome to TickerTrending Bot, {user.first_name}!</b>\n\n"
        f"I'm your personal crypto monitoring assistant, designed to help you track and boost tokens across multiple blockchains.\n\n"
        f"<b>🔍 What I can do for you:</b>\n"
        f"• Monitor token transactions in real-time\n"
        f"• Send custom alerts when significant buys happen\n"
        f"• Promote your project to partner channels\n"
        f"• Track tokens across ETH, SOL and more\n\n"
        f"<i>Get started by selecting an option below:</i>"
    )

    keyboard = [
        [
            InlineKeyboardButton("🔎 Start Tracking", callback_data="start_tracking"),
            InlineKeyboardButton("📊 Dashboard", callback_data="open_dashboard")
        ],
        [
            InlineKeyboardButton("🚀 Boost Token", callback_data="boost_token"),
            InlineKeyboardButton("🎮 Quick Tour", callback_data="quick_tour")
        ],
        [
            InlineKeyboardButton("🛠️ Commands List", callback_data="view_commands"),
            InlineKeyboardButton("❓ Help Center", callback_data="help_menu")
        ],
        [
            InlineKeyboardButton("🌐 Visit Website", url="https://tickertrending.com")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

async def handle_boost_token_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Boost Token button click"""
    query = update.callback_query
    await query.answer()

    # Create rich UI for boosting
    keyboard = [
        [
            InlineKeyboardButton("🟣 Ethereum", callback_data="network_eth"),
            InlineKeyboardButton("🔵 Solana", callback_data="network_sol")
        ],
        [
            InlineKeyboardButton("🟡 BNB", callback_data="network_bnb"),
            InlineKeyboardButton("🟢 Base", callback_data="network_base")
        ],
        [
            InlineKeyboardButton("ℹ️ How Boosting Works", callback_data="how_boost_works")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
    ]

    boost_text = (
        "🚀 <b>Token Boost Packages</b>\n\n"
        "Boost your token to appear on the trending page and across our partner channels.\n\n"
        "• <b>Increased Visibility</b> to potential investors\n"
        "• <b>Higher Ranking</b> in alerts and notifications\n"
        "• <b>Professional Presentation</b> with your branding\n\n"
        "Select which blockchain your token is on:"
    )

    await query.edit_message_text(
        text=boost_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


def get_start_handlers():
    """Return all start-related command and callback handlers"""
    return [
        CommandHandler("start", start_command),
        CallbackQueryHandler(handle_start_tracking, pattern="^start_tracking$"),
        CallbackQueryHandler(handle_dashboard, pattern="^open_dashboard$"),
        CallbackQueryHandler(handle_quick_tour, pattern="^quick_tour$"),
        CallbackQueryHandler(handle_commands_view, pattern="^view_commands$"),
        CallbackQueryHandler(handle_tour_commands, pattern="^tour_commands$"),
        CallbackQueryHandler(handle_tour_custom, pattern="^tour_custom$"),
        CallbackQueryHandler(handle_full_commands, pattern="^full_commands$"),
        CallbackQueryHandler(handle_back_to_start, pattern="^back_to_start$"),
        CallbackQueryHandler(handle_boost_token_button, pattern="^boost_token$")
    ]
import logging
import re
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, 
    MessageHandler, filters, CallbackQueryHandler
)
from telegram.constants import ParseMode
from utils import send_alert, build_alert_message, build_inline_buttons
import time
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

# Define conversation states
NAME, SYMBOL, CONTRACT, TELEGRAM, WEBSITE, TWITTER, IMAGE, EMOJIS, MEDIA, CONFIRM = range(10)

# Redis key pattern for saved customizations
CUSTOM_TOKEN_KEY = "custom_token:{}"

# Helper functions
def validate_url(url):
    """Basic URL validation"""
    # Allow simplified responses for testing
    if url.lower() in ['skip', 'none', 'n/a']:
        return True

    pattern = r'^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)$'
    return re.match(pattern, url) is not None

def validate_contract(address, chain=None):
    """Validate contract address format"""
    # Normalize the address
    address = address.strip()

    if chain == "ethereum":
        return re.match(r'^0x[a-fA-F0-9]{40}$', address) is not None
    elif chain == "solana":
        # Solana addresses are typically base58 encoded and around 32-44 chars
        return re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address) is not None
    else:
        # Try to guess the chain from the format
        is_eth = re.match(r'^0x[a-fA-F0-9]{40}$', address) is not None
        is_sol = re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address) is not None

        # For demonstration purposes, also allow shortened addresses
        if address.startswith("0x") and len(address) >= 8:
            logger.info(f"Demo mode: Accepting shortened ETH address: {address}")
            is_eth = True
        elif len(address) >= 8 and not address.startswith("0x"):
            logger.info(f"Demo mode: Accepting shortened SOL address: {address}")
            is_sol = True

        return is_eth or is_sol

def save_token_customization(token_address, data):
    """Save token customization data to Redis or file-based storage and update customization_handler"""
    try:
        from data_manager import get_data_manager
        dm = get_data_manager()

        # Initialize token customizations if not exists
        if "token_customizations" not in dm.data:
            dm.data["token_customizations"] = {}

        # Normalize address
        token_address = token_address.lower() if token_address.startswith("0x") else token_address

        # Save customization
        dm.data["token_customizations"][token_address] = data
        dm._save_data()
        logger.info(f"✅ Saved customization for token {token_address}")

        # Also update the customization_handler's global dict
        from customization_handler import token_customizations, save_customizations

        # Convert data to the format used by customization_handler
        token_customizations[token_address] = {
            "name": data.get("name", ""),
            "symbol": data.get("symbol", ""),
            "image": data.get("image", ""),
            "emojis": data.get("emojis", "🚀"),
            "links": {
                "telegram": data.get("telegram", ""),
                "website": data.get("website", ""),
                "twitter": data.get("twitter", "")
            }
        }

        # Save to the customizations.json file
        save_customizations()

        # Log the full data for debugging
        logger.info(f"Customization data: {data}")
        return True
    except Exception as e:
        logger.error(f"Error saving token customization: {e}")
        return False

def get_token_customization(token_address):
    """Get token customization data"""
    try:
        from data_manager import get_data_manager
        dm = get_data_manager()

        # Normalize address
        token_address = token_address.lower() if token_address.startswith("0x") else token_address

        return dm.data.get("token_customizations", {}).get(token_address, {})
    except Exception as e:
        logger.error(f"Error getting token customization: {e}")
        return {}

# Conversation handlers
async def start_customization(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the token customization flow"""
    user = update.effective_user

    # Check if command has arguments (token address)
    token_address = None
    if context.args and len(context.args) > 0:
        token_address = context.args[0]
        if validate_contract(token_address):
            context.user_data["token_address"] = token_address

            # Get existing customization if any
            existing = get_token_customization(token_address)
            if existing:
                context.user_data["customization"] = existing

                # Show preview of existing customization
                await update.message.reply_text(
                    f"⚙️ Editing customization for token: `{token_address}`\n\n"
                    f"Current settings:\n"
                    f"• Name: {existing.get('name', 'Not set')}\n"
                    f"• Symbol: {existing.get('symbol', 'Not set')}\n"
                    f"• Telegram: {existing.get('telegram', 'Not set')}\n"
                    f"• Website: {existing.get('website', 'Not set')}\n"
                    f"• Twitter: {existing.get('twitter', 'Not set')}\n"
                    f"• Emojis: {existing.get('emojis', '🚀')}\n\n"
                    f"Let's update these settings. First, what's the token's name?",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    f"⚙️ Creating customization for token: `{token_address}`\n\n"
                    f"First, what's the token's name?",
                    parse_mode=ParseMode.MARKDOWN
                )

            return NAME
        else:
            await update.message.reply_text("⚠️ Invalid token address format. Please provide a valid Ethereum or Solana token address.")

    # If no token address provided, ask for it
    await update.message.reply_text(
        "🔧 *Token Alert Customizer*\n\n"
        "Customize how your token appears in buy alerts!\n\n"
        "Please enter the token contract address:",
        parse_mode=ParseMode.MARKDOWN
    )
    return CONTRACT

async def handle_contract(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle token contract address input"""
    token_address = update.message.text.strip()

    if not validate_contract(token_address):
        await update.message.reply_text(
            "⚠️ Invalid token address format. Please provide a valid Ethereum or Solana token address."
        )
        return CONTRACT

    # Store token address
    context.user_data["token_address"] = token_address

    # Get existing customization if any
    existing = get_token_customization(token_address)
    if existing:
        context.user_data["customization"] = existing

        # Show preview of existing customization
        await update.message.reply_text(
            f"⚙️ Editing customization for token: `{token_address}`\n\n"
            f"Current settings:\n"
            f"• Name: {existing.get('name', 'Not set')}\n"
            f"• Symbol: {existing.get('symbol', 'Not set')}\n"
            f"• Telegram: {existing.get('telegram', 'Not set')}\n"
            f"• Website: {existing.get('website', 'Not set')}\n"
            f"• Twitter: {existing.get('twitter', 'Not set')}\n"
            f"• Emojis: {existing.get('emojis', '🚀')}\n\n"
            f"Let's update these settings. First, what's the token's name?",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"⚙️ Creating customization for token: `{token_address}`\n\n"
            f"First, what's the token's name?",
            parse_mode=ParseMode.MARKDOWN
        )

    return NAME

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle token name input"""
    name = update.message.text.strip()

    # Validate name
    if len(name) > 50:
        await update.message.reply_text("⚠️ Name is too long (max 50 characters). Please enter a shorter name.")
        return NAME

    # Store name
    context.user_data.setdefault("customization", {})["name"] = name

    await update.message.reply_text(
        f"✅ Name set to: *{name}*\n\n"
        f"Now, what's the token's symbol/ticker?",
        parse_mode=ParseMode.MARKDOWN
    )
    return SYMBOL

async def handle_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle token symbol input"""
    symbol = update.message.text.strip().upper()

    # Validate symbol
    if len(symbol) > 10:
        await update.message.reply_text("⚠️ Symbol is too long (max 10 characters). Please enter a shorter symbol.")
        return SYMBOL

    # Store symbol
    context.user_data.setdefault("customization", {})["symbol"] = symbol

    await update.message.reply_text(
        f"✅ Symbol set to: *{symbol}*\n\n"
        f"Now, enter your Telegram group/channel link (or type 'skip'):",
        parse_mode=ParseMode.MARKDOWN
    )
    return TELEGRAM

async def handle_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Telegram link input"""
    telegram = update.message.text.strip()

    # Check if skipped
    if telegram.lower() in ['skip', 'none', 'n/a']:
        telegram = ""
    else:
        # Validate Telegram link
        if not telegram.startswith('https://t.me/'):
            await update.message.reply_text(
                "⚠️ Invalid Telegram link format. It should start with 'https://t.me/'\n"
                "Please enter a valid link or type 'skip'."
            )
            return TELEGRAM

    # Store Telegram link
    context.user_data.setdefault("customization", {})["telegram"] = telegram

    telegram_msg = f"✅ Telegram link set to: {telegram}" if telegram else "⏩ Telegram link skipped"

    await update.message.reply_text(
        f"{telegram_msg}\n\n"
        f"Now, enter your project website URL (or type 'skip'):",
        parse_mode=ParseMode.MARKDOWN
    )
    return WEBSITE

async def handle_website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle website URL input"""
    website = update.message.text.strip()

    # Check if skipped
    if website.lower() in ['skip', 'none', 'n/a']:
        website = ""
    else:
        # Validate website URL
        if not validate_url(website):
            await update.message.reply_text(
                "⚠️ Invalid website URL format.\n"
                "Please enter a valid URL starting with http:// or https:// or type 'skip'."
            )
            return WEBSITE

    # Store website URL
    context.user_data.setdefault("customization", {})["website"] = website

    website_msg = f"✅ Website set to: {website}" if website else "⏩ Website skipped"

    await update.message.reply_text(
        f"{website_msg}\n\n"
        f"Now, enter your Twitter/X profile URL (or type 'skip'):",
        parse_mode=ParseMode.MARKDOWN
    )
    return TWITTER

async def handle_twitter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Twitter/X profile URL input"""
    twitter = update.message.text.strip()

    # Check if skipped
    if twitter.lower() in ['skip', 'none', 'n/a']:
        twitter = ""
    else:
        # Validate Twitter URL
        if not (twitter.startswith('https://twitter.com/') or twitter.startswith('https://x.com/')):
            await update.message.reply_text(
                "⚠️ Invalid Twitter/X URL format. It should start with 'https://twitter.com/' or 'https://x.com/'\n"
                "Please enter a valid URL or type 'skip'."
            )
            return TWITTER

    # Store Twitter URL
    context.user_data.setdefault("customization", {})["twitter"] = twitter

    twitter_msg = f"✅ Twitter/X set to: {twitter}" if twitter else "⏩ Twitter/X skipped"

    await update.message.reply_text(
        f"{twitter_msg}\n\n"
        f"Now, enter a logo image URL for your token (or type 'skip'):",
        parse_mode=ParseMode.MARKDOWN
    )
    return IMAGE

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image URL input"""
    image = update.message.text.strip()

    # Check if skipped
    if image.lower() in ['skip', 'none', 'n/a']:
        image = ""
    else:
        # Validate image URL
        if not validate_url(image):
            await update.message.reply_text(
                "⚠️ Invalid image URL format.\n"
                "Please enter a valid URL starting with http:// or https:// or type 'skip'."
            )
            return IMAGE

    # Store image URL
    context.user_data.setdefault("customization", {})["image"] = image

    image_msg = f"✅ Logo image set to: {image}" if image else "⏩ Logo image skipped"

    await update.message.reply_text(
        f"{image_msg}\n\n"
        f"Finally, enter up to 5 emojis to use in alerts (default: 🚀):",
        parse_mode=ParseMode.MARKDOWN
    )
    return EMOJIS

async def handle_emojis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle emoji input"""
    emojis = update.message.text.strip()

    # Default to rocket emoji if empty
    if not emojis or emojis.lower() in ['skip', 'none', 'n/a']:
        emojis = "🚀"

    # Limit to 5 emojis
    emojis = "".join([c for c in emojis if ord(c) > 127])[:10]

    # If no valid emojis were found, default to rocket
    if not emojis:
        emojis = "🚀"

    # Store emojis
    context.user_data.setdefault("customization", {})["emojis"] = emojis

    # Ask for media upload
    await update.message.reply_text(
        "🖼️ Now, you can upload a custom media for your token alerts!\n\n"
        "Send me an image or GIF to use in alerts, or type 'skip' to continue without media.\n\n"
        "👉 This image/GIF will appear with every alert for this token."
    )

    return MEDIA

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle media (image or GIF) upload"""
    customization = context.user_data.setdefault("customization", {})
    token_address = context.user_data["token_address"]

    # Check if user wants to skip
    if update.message and update.message.text and update.message.text.strip().lower() in ['skip', 'none', 'n/a']:
        await update.message.reply_text("⏩ Media upload skipped.")
        customization["media"] = None

    # Handle photo (image)
    elif update.message and update.message.photo:
        try:
            # Get the largest photo size
            photo = update.message.photo[-1]
            file_id = photo.file_id
            customization["media"] = {
                "type": "photo",
                "file_id": file_id
            }
            await update.message.reply_text("✅ Image saved! This will be used in your token alerts.")
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            await update.message.reply_text("❌ Error processing image. Please try again or type 'skip'.")
            return MEDIA

    # Handle document (GIF or other files)
    elif update.message and update.message.document:
        doc = update.message.document
        mime_type = doc.mime_type or ""

        # Check if it's a GIF or image
        if mime_type.startswith('image/') or mime_type == 'image/gif' or doc.file_name.lower().endswith(('.gif', '.jpg', '.jpeg', '.png')):
            file_id = doc.file_id
            customization["media"] = {
                "type": "document",
                "file_id": file_id,
                "mime_type": mime_type
            }
            await update.message.reply_text("✅ Media saved! This will be used in your token alerts.")
        else:
            await update.message.reply_text(
                "❌ Unsupported file type. Please send an image or GIF, or type 'skip' to continue without media."
            )
            return MEDIA

    # Handle animation (Telegram GIF)
    elif update.message and update.message.animation:
        animation = update.message.animation
        file_id = animation.file_id
        customization["media"] = {
            "type": "animation",
            "file_id": file_id
        }
        await update.message.reply_text("✅ GIF saved! This will be used in your token alerts.")

    # Handle sticker
    elif update.message and update.message.sticker:
        sticker = update.message.sticker
        file_id = sticker.file_id
        customization["media"] = {
            "type": "sticker",
            "file_id": file_id
        }
        await update.message.reply_text("✅ Sticker saved! This will be used in your token alerts.")

    # If none of the above, request proper media format
    else:
        if update.message:
            await update.message.reply_text(
                "❌ Please send an image, GIF, or sticker, or type 'skip' to continue without media."
            )
        else:
            # Fallback in case we get a CallbackQuery update
            await update.callback_query.message.reply_text(
                "❌ Please send an image, GIF, or sticker, or type 'skip' to continue without media."
            )
        return MEDIA

    # Generate preview message
    name = customization.get("name", "Token Name")
    symbol = customization.get("symbol", "TKN")
    telegram = customization.get("telegram", "")
    website = customization.get("website", "")
    twitter = customization.get("twitter", "")
    emoji_set = customization.get("emojis", "🚀")
    image_url = customization.get("image", "")
    media = customization.get("media", None)

    # Create buttons for preview
    buttons = []

    if telegram:
        buttons.append([InlineKeyboardButton("💬 Telegram", url=telegram)])

    if website:
        buttons.append([InlineKeyboardButton("🌐 Website", url=website)])

    if twitter:
        buttons.append([InlineKeyboardButton("🐦 Twitter/X", url=twitter)])

    # Add chart and buy buttons for completeness
    chart_url = f"https://dexscreener.com/solana/{token_address}" if not token_address.startswith("0x") else f"https://dexscreener.com/ethereum/{token_address}"
    buy_url = f"https://raydium.io/swap/?inputCurrency=SOL&outputCurrency={token_address}" if not token_address.startswith("0x") else f"https://app.uniswap.org/#/swap?outputCurrency={token_address}"

    buttons.append([InlineKeyboardButton("📊 Chart", url=chart_url)])
    buttons.append([InlineKeyboardButton("💰 Buy Now", url=buy_url)])

    # Create preview message
    preview = (
        f"{emoji_set} *{name}* ({symbol}) {emoji_set}\n\n"
        f"🟢 Someone just bought for $1,000 (1.5 SOL)\n\n"
        f"📈 24h Change: +15%\n"
        f"💰 24h Volume: $250,000\n"
        f"💎 Market Cap: $5,000,000\n\n"
        f"🧑‍🚀 Holders: 1,200\n"
        f"⏱ Created: 7 days ago\n\n"
        f"*This is how your alert will look!*"
    )

    if image_url:
        preview = f"![{name} Logo]({image_url})\n\n" + preview

    # Show preview message about media if present
    media_message = ""
    if media:
        media_type = media.get("type", "")
        if media_type == "photo":
            media_message = "\n\n📸 *Custom image will be shown with alerts*"
        elif media_type == "animation" or (media_type == "document" and "gif" in media.get("mime_type", "")):
            media_message = "\n\n🎬 *Custom GIF will be shown with alerts*"
        elif media_type == "sticker":
            media_message = "\n\n🎭 *Custom sticker will be shown with alerts*"

        # Also send a preview of the media if possible
        try:
            if media_type == "photo":
                await update.message.reply_photo(media["file_id"], caption="👆 This image will appear with your token alerts")
            elif media_type == "animation":
                await update.message.reply_animation(media["file_id"], caption="👆 This GIF will appear with your token alerts")
            elif media_type == "document":
                await update.message.reply_document(media["file_id"], caption="👆 This media will appear with your token alerts")
            elif media_type == "sticker":
                await update.message.reply_sticker(media["file_id"])
                await update.message.reply_text("👆 This sticker will appear with your token alerts")
        except Exception as e:
            logger.error(f"Error previewing media: {e}")
            await update.message.reply_text("⚠️ Media preview failed, but your media is still saved and will appear with alerts.")

    preview += media_message

    # Show preview and confirmation buttons
    confirm_keyboard = [
        [InlineKeyboardButton("✅ Save", callback_data="confirm_customization")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_customization")]
    ]

    # First send preview alert
    await update.message.reply_text(
        preview,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN
    )

    # Then send confirmation buttons
    await update.message.reply_text(
        "👆 This is a preview of how your alerts will look.\n\n"
        "Would you like to save these settings?",
        reply_markup=InlineKeyboardMarkup(confirm_keyboard)
    )

    return CONFIRM

async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirmation button"""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_customization":
        # Save customization
        token_address = context.user_data.get("token_address")
        customization = context.user_data.get("customization", {})

        if not token_address:
            await query.edit_message_text("❌ Error: No token address found. Please start over.")
            return ConversationHandler.END

        # Add timestamp
        customization["updated_at"] = datetime.now().isoformat()

        # Save to storage
        success = save_token_customization(token_address, customization)

        if success:
            await query.edit_message_text(
                f"✅ Your token alert customization has been saved!\n\n"
                f"Token: `{token_address}`\n"
                f"Name: {customization.get('name')}\n"
                f"Symbol: {customization.get('symbol')}\n\n"
                f"Your custom alert style will now be used for all buy notifications for this token.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(
                "❌ There was an error saving your customization. Please try again later."
            )
    else:
        await query.edit_message_text("❌ Customization cancelled.")

    # Clear user data
    context.user_data.clear()

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the customization process"""
    if update.message:
        await update.message.reply_text("❌ Token customization cancelled.")

    # Clear user data
    context.user_data.clear()

    return ConversationHandler.END

# Get the main conversation handler
def get_token_customization_handler():
    """Get the token customization conversation handler"""
    return ConversationHandler(
        entry_points=[CommandHandler("customize_token", start_customization)],
        states={
            CONTRACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contract)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_symbol)],
            TELEGRAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram)],
            WEBSITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_website)],
            TWITTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_twitter)],
            IMAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_image)],
            EMOJIS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_emojis)],
            MEDIA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_media),
                MessageHandler(filters.PHOTO | filters.Document.ALL | filters.ANIMATION | filters.Sticker.ALL, handle_media)
            ],
            CONFIRM: [CallbackQueryHandler(handle_confirm, pattern="^(confirm|cancel)_customization$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="token_customization",
        persistent=False
    )

# Get additional handlers
def get_customization_handlers():
    """Get additional handlers related to token customization"""
    return []
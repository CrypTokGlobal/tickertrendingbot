
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from owner_manager import strictly_owner, reset_admins, ensure_owner

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@strictly_owner
async def handle_emergency_reset_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Emergency command to reset all admin access (owner only)"""
    success = reset_admins()
    if success:
        await update.message.reply_text("🔄 Admin list has been reset. Only you (the owner) now have access.")
    else:
        await update.message.reply_text("❌ Failed to reset admin list. Please check logs.")

async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command and auto-assign owner if needed"""
    user_id = update.effective_user.id
    # Try to auto-assign as owner if no owner exists
    became_owner = ensure_owner(user_id)
    
    if became_owner:
        await update.message.reply_text(
            "🔐 Welcome! Since this is the first run, you have been assigned as the bot owner.\n"
            "You now have access to all admin commands."
        )
    else:
        await update.message.reply_text(
            "👋 Welcome to the Crypto Alert Bot!\n"
            "Use /help to see available commands."
        )

def get_admin_handlers():
    """Return all admin-related command handlers"""
    return [
        CommandHandler("emergency_reset_admins", handle_emergency_reset_admins),
        CommandHandler("start", handle_start_command)
    ]


import logging
import os
import sys
import psutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from owner_manager import is_authorized, add_admin, remove_admin, get_owner_id, get_admin_list
from auth_decorators import owner_only, strictly_owner
from chat_tracker import get_all_chats

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@owner_only
async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart the bot"""
    await update.message.reply_text("🔄 Restarting bot...")
    logger.info(f"Bot restart initiated by user {update.effective_user.id}")
    # Execute a hard restart
    os.execl(sys.executable, sys.executable, *sys.argv)

@owner_only
async def kill_dupes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kill duplicate bot processes"""
    current_pid = os.getpid()
    killed = 0

    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            # Skip the current process
            if proc.info['pid'] == current_pid:
                continue
                
            # Check if it's a Python process running this script
            cmd = proc.info['cmdline'] if proc.info['cmdline'] else []
            if len(cmd) >= 2 and 'python' in cmd[0] and 'main.py' in cmd[1]:
                try:
                    os.kill(proc.info['pid'], 15)  # SIGTERM
                    killed += 1
                    logger.info(f"Killed duplicate process: {proc.info['pid']}")
                except Exception as e:
                    logger.error(f"Failed to kill process {proc.info['pid']}: {e}")

        await update.message.reply_text(f"✅ Killed {killed} duplicate bot processes")

    except Exception as e:
        logger.error(f"Error killing duplicates: {e}")
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

@strictly_owner
async def allow_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a user to the admin list"""
    if not context.args:
        await update.message.reply_text("Usage: /allow username_or_userid")
        return

    identifier = context.args[0]
    added = add_admin(identifier)

    if added:
        await update.message.reply_text(f"✅ {identifier} added to admin list.")
    else:
        await update.message.reply_text(f"ℹ️ {identifier} is already an admin.")

@strictly_owner
async def deny_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a user from the admin list"""
    if not context.args:
        await update.message.reply_text("Usage: /deny username_or_userid")
        return

    identifier = context.args[0]
    removed = remove_admin(identifier)

    if removed:
        await update.message.reply_text(f"✅ {identifier} removed from admin list.")
    else:
        await update.message.reply_text(f"ℹ️ {identifier} is not in the admin list.")

@owner_only
async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all admins"""
    admins = get_admin_list()
    owner = get_owner_id()

    if not admins:
        message = f"👑 Owner: {owner}\n\n❌ No additional admins."
    else:
        message = f"👑 Owner: {owner}\n\n🛡️ Admins:\n"
        for admin in admins:
            message += f"• {admin}\n"

    await update.message.reply_text(message)

@owner_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display admin panel with privileged operations"""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Restart Bot", callback_data="admin_restart"),
            InlineKeyboardButton("🗑️ Kill Duplicates", callback_data="admin_kill_dupes")
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton("📢 New Broadcast", callback_data="admin_new_broadcast")
        ]
    ]

    await update.message.reply_text(
        "🛠️ <b>Admin Control Panel</b>\n\n"
        "Select an operation from the menu below:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

@owner_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message to all active chats"""
    if not context.args:
        await update.message.reply_text("Usage: /broadcast Your message here")
        return

    message = "📢 <b>Broadcast:</b>\n" + " ".join(context.args)
    sent, failed = 0, 0

    # First send a status message
    status_msg = await update.message.reply_text("💬 Broadcasting message to all chats...")

    # Get all chats
    all_chats = get_all_chats()
    total = len(all_chats)

    # Add buttons to the broadcast message if desired
    keyboard = None
    if "-button" in message:
        # Example: /broadcast Visit our website -button Visit Website https://example.com
        parts = message.split("-button")
        message = parts[0]  # The actual message

        buttons = []
        current_row = []

        # Process button definitions
        for i in range(1, len(parts)):
            button_def = parts[i].strip().split(" ", 2)
            if len(button_def) >= 3:
                button_text = button_def[0] + " " + button_def[1]
                button_url = button_def[2]
                current_row.append(InlineKeyboardButton(button_text, url=button_url))

                # Add 2 buttons per row
                if len(current_row) == 2:
                    buttons.append(current_row)
                    current_row = []

        # Add any remaining buttons
        if current_row:
            buttons.append(current_row)

        if buttons:
            keyboard = InlineKeyboardMarkup(buttons)

    # Send to all chats
    for chat_id in all_chats:
        try:
            if keyboard:
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text=message, 
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text=message, 
                    parse_mode="HTML"
                )
            sent += 1
            # Update status every 10 messages
            if sent % 10 == 0:
                await status_msg.edit_text(f"💬 Broadcast progress: {sent}/{total}")
        except Exception as e:
            logger.error(f"Failed to send broadcast to {chat_id}: {e}")
            failed += 1

    await status_msg.edit_text(f"✅ Broadcast complete:\n"
                              f"• Sent to {sent} chats\n"
                              f"• Failed in {failed} chats")


def get_admin_handlers():
    """Return all admin command handlers"""
    return [
        CommandHandler("restart", restart_command),
        CommandHandler("kill_dupes", kill_dupes),
        CommandHandler("broadcast", broadcast),
        CommandHandler("admin", admin_panel),
        CommandHandler("allow", allow_admin),
        CommandHandler("deny", deny_admin),
        CommandHandler("admins", list_admins),
    ]

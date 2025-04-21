
import logging
from telegram.ext import CallbackQueryHandler

# Import handlers from callback_handler
from callback_handler import callback_handler, test_alert_callback
from button_handler import button_handler
from boost_menu import handle_boost_selection, show_how_boost_works, handle_boost_back

logger = logging.getLogger(__name__)

def get_all_callback_handlers():
    """
    Consolidate all callback handlers from different modules into a single list.
    This ensures all callbacks are registered properly without duplication.
    """
    return [
        # Boost-related callbacks (highest priority)
        CallbackQueryHandler(handle_boost_back, pattern="^boost_back$"),
        CallbackQueryHandler(show_how_boost_works, pattern="^how_boost_works$"),
        CallbackQueryHandler(handle_boost_selection, pattern="^network_"),
        CallbackQueryHandler(handle_boost_selection, pattern="^boostpkg"),
        
        # Help menu callbacks
        CallbackQueryHandler(button_handler, pattern="^help_menu$"),
        CallbackQueryHandler(button_handler, pattern="^back_to_main$"),
        CallbackQueryHandler(button_handler, pattern="^track_token$"),
        CallbackQueryHandler(button_handler, pattern="^untrack_token$"),
        CallbackQueryHandler(button_handler, pattern="^boost_token$"),
        CallbackQueryHandler(button_handler, pattern="^customize_alerts$"),
        CallbackQueryHandler(button_handler, pattern="^view_stats$"),
        CallbackQueryHandler(button_handler, pattern="^test_alert$"),
        CallbackQueryHandler(button_handler, pattern="^contracts_tracking$"),
        CallbackQueryHandler(button_handler, pattern="^bot_status_check$"),
        
        # Track network selection
        CallbackQueryHandler(button_handler, pattern="^track_eth$"),
        CallbackQueryHandler(button_handler, pattern="^track_sol$"),
        
        # Test alert callbacks
        CallbackQueryHandler(test_alert_callback, pattern="^test_alert_"),
        CallbackQueryHandler(test_alert_callback, pattern="^test_sol_alert_"),
        CallbackQueryHandler(test_alert_callback, pattern="^test_bnb_alert_"),

        # Catch-all for other patterns - should be last
        CallbackQueryHandler(callback_handler)
    ]

def register_all_callbacks(application):
    """Register all callback handlers with the application"""
    logger.info("Registering callback handlers")
    # Register every callback handler from the consolidated list
    all_handlers = get_all_callback_handlers()
    
    for handler in all_handlers:
        application.add_handler(handler)

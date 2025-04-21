import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up dynamic logging level
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
BOT_TOKEN = TELEGRAM_BOT_TOKEN  # Ensure backward compatibility
logger.info(f"Bot token found: {'✅ Yes' if TELEGRAM_BOT_TOKEN else '❌ No'}")
if TELEGRAM_BOT_TOKEN:
    logger.info(f"Token length: {len(TELEGRAM_BOT_TOKEN)}")
else:
    logger.error("⚠️ No bot token found! Please set TELEGRAM_BOT_TOKEN in .env file.")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID", "") # Retained from original

# Ethereum Configuration
INFURA_URL = os.getenv("INFURA_URL", "https://mainnet.infura.io/v3/43791f462ee74d2ca29fa238b07a0758")
INFURA_API_KEY = os.getenv("INFURA_API_KEY", "43791f462ee74d2ca29fa238b07a0758")
ETHEREUM_API_KEY = os.getenv("ETHEREUM_API_KEY")
FALLBACK_RPC = os.getenv("FALLBACK_RPC", "https://rpc.ankr.com/eth") # Retained from original
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "") # Retained from original

# Solana Configuration
SOLANA_RPC = os.getenv("SOLANA_RPC", "https://api.mainnet-beta.solana.com") # Retained from original
SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY")

# Binance Smart Chain Configuration
BSC_RPC = os.getenv("BSC_RPC", "https://bsc-dataseed.binance.org/") # Retained from original
BSC_NODE_URL = os.getenv("BSC_NODE_URL", "https://bsc-dataseed1.binance.org")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")

# Debug Settings
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local.db")  # fallback SQLite for local dev
PGDATABASE = os.getenv("PGDATABASE")
PGHOST = os.getenv("PGHOST")

# Promotion configuration
PROMOTION_WALLET_ADDRESS = os.getenv("PROMOTION_WALLET_ADDRESS")

# API port configurations
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8001"))
HEALTH_CHECK_PORT = int(os.getenv("HEALTH_CHECK_PORT", "8080"))

# Default minimum transaction value in USD to trigger an alert. Retained from original, but could be moved.
DEFAULT_MIN_VALUE_USD = float(os.getenv("DEFAULT_MIN_VALUE_USD", "10.0"))

# Minimum transaction value in USD to trigger alerts. Retained from original, but could be moved.
MIN_TRANSACTION_VALUE_USD = float(os.getenv("MIN_TRANSACTION_VALUE_USD", "5.0"))

# Rate limiting for alerts. Retained from original, but could be moved.
MAX_ALERTS_PER_HOUR = int(os.getenv("MAX_ALERTS_PER_HOUR", "10"))

# Payment system settings. Retained from original, but could be moved.
PAYMENT_ENABLED = os.getenv("PAYMENT_ENABLED", "false").lower() == "true"


# Admin chat IDs for reporting (modified to use ADMIN_CHAT_ID from edited code and original logic)
ADMIN_CHAT_IDS = [OWNER_CHAT_ID] if OWNER_CHAT_ID else []
admin_list_str = os.getenv("ADMIN_CHAT_IDS", "")
if admin_list_str:
    try:
        # Add additional admin IDs if they exist
        admin_ids = [id.strip() for id in admin_list_str.split(",")]
        for admin_id in admin_ids:
            if admin_id and admin_id not in ADMIN_CHAT_IDS:
                ADMIN_CHAT_IDS.append(admin_id)
    except Exception as e:
        logger.error(f"Error parsing admin chat IDs: {e}")


def validate_config():
    """Validate that essential configuration values are present."""
    missing = []

    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not ADMIN_CHAT_ID:
        missing.append("ADMIN_CHAT_ID")
    if not INFURA_URL:
        missing.append("INFURA_URL")
    if not FALLBACK_RPC:
        missing.append("FALLBACK_RPC")
    
    # SQLite fallback means DATABASE_URL is technically optional now
    if not DATABASE_URL.startswith("sqlite"):
        if not DATABASE_URL:
            logger.warning("DATABASE_URL not set - using SQLite fallback")
        if not PGDATABASE and "postgres" in DATABASE_URL:
            missing.append("PGDATABASE")

    if missing:
        missing_vars = ", ".join(missing)
        logger.warning(f"⚠️ WARNING: Missing essential environment variables: {missing_vars}")
        logger.warning("Please add them to your .env file or Replit Secrets")
        return False
    
    logger.info("✅ Configuration validated successfully")
    return True

# Call validation on import
config_valid = validate_config()

# Add TOKEN for backwards compatibility
TOKEN = TELEGRAM_BOT_TOKEN

# Export variables
__all__ = ['TELEGRAM_BOT_TOKEN', 'TOKEN', 'INFURA_URL', 'FALLBACK_RPC', 'ETHERSCAN_API_KEY', 'SOLANA_RPC', 'BSC_RPC', 'DEFAULT_MIN_VALUE_USD', 'DEBUG_MODE', 'TEST_MODE', 'OWNER_CHAT_ID', 'ADMIN_CHAT_IDS', 'DASHBOARD_PORT', 'HEALTH_CHECK_PORT', 'MIN_TRANSACTION_VALUE_USD', 'MAX_ALERTS_PER_HOUR', 'PAYMENT_ENABLED', 'INFURA_API_KEY', 'ETHEREUM_API_KEY', 'SOLSCAN_API_KEY', 'DATABASE_URL', 'PGDATABASE', 'PGHOST', 'PROMOTION_WALLET_ADDRESS']
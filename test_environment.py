
import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("environment_check")

def check_environment():
    """Check if all required environment variables are set"""
    load_dotenv()
    
    # Critical variables
    print("🔍 Checking critical environment variables...")
    
    token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found! Bot cannot function without it.")
        print("   💡 Add it to your Replit Secrets (key: TELEGRAM_BOT_TOKEN)")
        return False
    else:
        logger.info(f"✅ Bot token found (length: {len(token)})")
    
    # Check for Ethereum/BSC monitoring
    infura_url = os.getenv('INFURA_URL')
    if not infura_url:
        logger.warning("⚠️ INFURA_URL not found. Ethereum monitoring will not work.")
        print("   💡 Add it to your Replit Secrets if you want to track Ethereum tokens")
    else:
        logger.info("✅ Infura URL found")
    
    # Check for Solana monitoring
    solana_rpc = os.getenv('SOLANA_RPC_URL')
    if not solana_rpc:
        logger.warning("⚠️ SOLANA_RPC_URL not found. Solana monitoring will not work.")
        print("   💡 Add it to your Replit Secrets if you want to track Solana tokens")
    else:
        logger.info("✅ Solana RPC URL found")
    
    # Check for BSC monitoring
    bsc_node = os.getenv('BSC_NODE_URL')
    if not bsc_node:
        logger.warning("⚠️ BSC_NODE_URL not found. BSC monitoring will not work.")
        print("   💡 Add it to your Replit Secrets if you want to track BSC tokens")
    else:
        logger.info("✅ BSC Node URL found")
    
    # Check Python dependencies
    try:
        import telegram
        logger.info("✅ python-telegram-bot installed")
    except ImportError:
        logger.error("❌ python-telegram-bot not installed")
        print("   💡 Run: pip install python-telegram-bot")
        return False
    
    try:
        import web3
        logger.info("✅ web3 installed")
    except ImportError:
        logger.warning("⚠️ web3 not installed (required for Ethereum/BSC monitoring)")
        print("   💡 Run: pip install web3")
    
    # Result
    print("\n✅ Environment check completed")
    print("🚀 The bot should be able to start if required variables are set")
    return True

if __name__ == "__main__":
    print("🔧 Checking environment configuration...")
    if check_environment():
        print("✅ Environment check passed")
        sys.exit(0)
    else:
        print("❌ Environment check failed - see warnings above")
        # Exit with non-zero but don't stop Replit workflow
        sys.exit(0)

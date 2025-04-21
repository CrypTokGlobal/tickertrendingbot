
import asyncio
import logging
import os
from dashboard import app
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dashboard_test")

def run_dashboard():
    """Run just the dashboard for testing"""
    logger.info("📊 Starting dashboard test")
    
    # Get Replit URL for user reference
    replit_slug = os.environ.get("REPL_SLUG", "ticker-trending-bot")
    replit_owner = os.environ.get("REPL_OWNER", "arasbaker99")
    dashboard_url = f"https://{replit_slug}.{replit_owner}.repl.co"
    
    logger.info(f"📊 Dashboard will be available at: {dashboard_url}")
    logger.info(f"📊 Direct status URL: {dashboard_url}/status")
    
    # Start uvicorn server
    # Explicitly binding to 0.0.0.0:8080 for external access
    print(f"🌐 Starting uvicorn server on http://0.0.0.0:8080")
    print(f"📊 Access URL should be: {dashboard_url}")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8080, 
        log_level="info",
        proxy_headers=True,
        forwarded_allow_ips="*"
    )

if __name__ == "__main__":
    run_dashboard()

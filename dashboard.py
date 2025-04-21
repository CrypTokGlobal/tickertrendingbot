import logging
import threading
import datetime
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global status tracker
bot_status = {
    "start_time": datetime.datetime.now().isoformat(),
    "tracked_contracts": {"ethereum": set(), "solana": set(), "binance": set()},
    "alerts_sent": 0,
    "telegram_chats": 0,
    "health": "running",
    "last_update": datetime.datetime.now().isoformat(),
    "last_alert": "",
    "active": True,
    "recent_alerts": []  # Store recent alerts for API endpoint
}

# Create FastAPI app
app = FastAPI(
    title="TickerTrending Bot Dashboard",
    description="Monitor your Telegram bot's status and performance",
    version="1.0"
)

# Create a directory for templates if it doesn't exist
os.makedirs("templates", exist_ok=True)

# Create a simple HTML template
with open("templates/status.html", "w") as f:
    f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>TickerTrending Bot Status</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; }
        .card { margin-bottom: 20px; }
        .status-badge { font-size: 1.2em; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">TickerTrending Bot Status Dashboard</h1>

        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">Bot Status</h5>
                <span class="badge bg-success status-badge">{{status.health}}</span>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Uptime:</strong> {{uptime}}</p>
                        <p><strong>Alerts Sent:</strong> {{status.alerts_sent}}</p>
                        <p><strong>Active Chats:</strong> {{status.telegram_chats}}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>Ethereum Tokens:</strong> {{eth_tokens}}</p>
                        <p><strong>Solana Tokens:</strong> {{sol_tokens}}</p>
                        <p><strong>Last Update:</strong> {{last_update_time}}</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Tracked Tokens</h5>
            </div>
            <div class="card-body">
                <ul class="nav nav-tabs" id="myTab" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="ethereum-tab" data-bs-toggle="tab" data-bs-target="#ethereum" type="button" role="tab" aria-controls="ethereum" aria-selected="true">Ethereum</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="solana-tab" data-bs-toggle="tab" data-bs-target="#solana" type="button" role="tab" aria-controls="solana" aria-selected="false">Solana</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="binance-tab" data-bs-toggle="tab" data-bs-target="#binance" type="button" role="tab" aria-controls="binance" aria-selected="false">Binance</button>
                    </li>
                </ul>
                <div class="tab-content" id="myTabContent">
                    <div class="tab-pane fade show active" id="ethereum" role="tabpanel" aria-labelledby="ethereum-tab">
                        <table class="table mt-3">
                            <thead>
                                <tr>
                                    <th>Token Address</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for token in eth_address_list %}
                                <tr>
                                    <td><code>{{token[:8]}}...{{token[-6:]}}</code></td>
                                </tr>
                                {% else %}
                                <tr>
                                    <td class="text-center">No Ethereum tokens tracked</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                    <div class="tab-pane fade" id="solana" role="tabpanel" aria-labelledby="solana-tab">
                        <table class="table mt-3">
                            <thead>
                                <tr>
                                    <th>Token Address</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for token in sol_address_list %}
                                <tr>
                                    <td><code>{{token[:8]}}...{{token[-6:]}}</code></td>
                                </tr>
                                {% else %}
                                <tr>
                                    <td class="text-center">No Solana tokens tracked</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                    <div class="tab-pane fade" id="binance" role="tabpanel" aria-labelledby="binance-tab">
                        <table class="table mt-3">
                            <thead>
                                <tr>
                                    <th>Token Address</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for token in bnb_address_list %}
                                <tr>
                                    <td><code>{{token[:8]}}...{{token[-6:]}}</code></td>
                                </tr>
                                {% else %}
                                <tr>
                                    <td class="text-center">No Binance tokens tracked</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Latest Alert</h5>
            </div>
            <div class="card-body">
                <div class="alert-box">
                    {% if status.last_alert %}
                        {{ status.last_alert }}
                    {% else %}
                        No alerts sent yet
                    {% endif %}
                </div>
            </div>
        </div>

        <a href="/test_alert" target="_blank" class="btn btn-success mt-3">Send Test Alert</a>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Auto-refresh the page every 60 seconds
        setTimeout(function() {
            location.reload();
        }, 60000);
    </script>
</body>
</html>
    """)

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Allow CORS for better access
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(url="/status")

# Add explicit handler for the base URL without path
@app.get("", response_class=RedirectResponse)
async def empty_path():
    return RedirectResponse(url="/status")

@app.get("/redirect", response_class=HTMLResponse)
async def redirect_to_status():
    """Redirect to status page"""
    html_content = """
    <html>
        <head>
            <meta http-equiv="refresh" content="0;url=/status" />
            <title>Redirecting...</title>
        </head>
        <body>
            <p>Redirecting to dashboard...</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/status")
async def status_json():
    """Return bot status as JSON"""
    try:
        # Convert sets to lists for JSON serialization
        serializable_status = {
            "active": bot_status.get("active", False),
            "uptime_seconds": (datetime.datetime.now() - datetime.datetime.fromisoformat(bot_status.get("start_time", datetime.datetime.now().isoformat()))).total_seconds(),
            "tracked_contracts": {
                "ethereum": list(bot_status.get("tracked_contracts", {}).get("ethereum", set())),
                "solana": list(bot_status.get("tracked_contracts", {}).get("solana", set())),
                "binance": list(bot_status.get("tracked_contracts", {}).get("binance", set()))
            },
            "total_contracts": sum(len(contracts) for contracts in bot_status.get("tracked_contracts", {}).values()),
            "alerts_sent": bot_status.get("alerts_sent", 0),
            "last_alert": bot_status.get("last_alert", ""),
            "telegram_chats": bot_status.get("telegram_chats", 0)
        }
        return serializable_status
    except Exception as e:
        import logging
        logging.error(f"Error in status_json: {e}")
        return {"error": str(e), "active": False}

@app.get("/alerts/live")
async def get_live_alerts():
    """Return a list of recent Ethereum alerts"""
    # If we have real alerts, use them
    if bot_status["recent_alerts"]:
        return {"alerts": bot_status["recent_alerts"]}

    # Otherwise return sample data
    return {
        "alerts": [
            {
                "timestamp": "2025-04-19T04:10:00Z",
                "network": "ethereum",
                "token_name": "ExampleToken",
                "token_symbol": "EXMPL",
                "contract_address": "0x1234567890abcdef1234567890abcdef12345678",
                "amount_usd": 1500,
                "tx_hash": "0xabc123...",
                "chat_id": "-1002520194744"
            },
            {
                "timestamp": "2025-04-19T04:15:00Z",
                "network": "ethereum",
                "token_name": "DeFi Cat",
                "token_symbol": "DCAT",
                "contract_address": "0xdeadcafedeadcafedeadcafedeadcafedead1234",
                "amount_usd": 420,
                "tx_hash": "0xdef456...",
                "chat_id": "-1002520194744"
            }
        ]
    }

@app.get("/group/{chat_id}/contracts")
async def get_group_contracts(chat_id: str):
    """Return a list of Ethereum contracts monitored for a specific group"""
    try:
        # Try to get tracked tokens for this chat from data_manager
        from data_manager import get_data_manager
        dm = get_data_manager()
        all_tokens = dm.data.get("tracked_tokens", [])

        # Filter tokens for this specific chat
        chat_tokens = [t for t in all_tokens if str(t.get("chat_id", "")) == chat_id]

        # Extract contract addresses
        contract_addresses = [t.get("address", "").lower() for t in chat_tokens if t.get("address")]

        return {
            "chat_id": chat_id,
            "contracts": contract_addresses,
            "token_count": len(contract_addresses)
        }
    except Exception as e:
        return {
            "chat_id": chat_id,
            "contracts": [],
            "error": str(e)
        }

@app.get("/test_alert")
async def test_alert():
    """Send a test alert to the admin chat ID"""
    try:
        # Import necessary modules
        import os
        from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
        from telegram.constants import ParseMode

        # Get admin chat ID from environment
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")

        # Get bot instance from environment variables
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
        if not bot_token:
            return {"success": False, "message": "No bot token configured"}

        bot = Bot(token=bot_token)

        # Try to get token data from monitor instance if available
        token_address = "0x1234567890abcdef1234567890abcdef12345678"
        token_name = "Test Token"
        token_symbol = "TEST"

        if not admin_chat_id:
            return {"success": False, "message": "No ADMIN_CHAT_ID configured in environment variables"}

        # Test message
        message = f"🧪 <b>TEST ALERT</b>\n\n"
        message += f"🚀 <b>Test Token (TEST)</b> 🚀\n\n"
        message += f"💰 Someone just bought for <b>$1,000</b> (0.5 ETH)\n\n"
        message += f"🔗 <a href='https://etherscan.io/tx/0xtest'>View Transaction</a>\n\n"
        message += f"<i>This is a test alert from the dashboard</i>"

        # Create keyboard buttons
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Chart", url="https://dexscreener.com/ethereum/0x1234567890abcdef1234567890abcdef12345678"),
                InlineKeyboardButton("💸 Buy Now", url="https://app.uniswap.org/#/swap?outputCurrency=0x1234567890abcdef1234567890abcdef12345678")
            ],
            [
                InlineKeyboardButton("🌐 Website", url="https://example.com"),
                InlineKeyboardButton("💬 Telegram", url="https://t.me/test")
            ]
        ])

        # Send alert
        await bot.send_message(
            chat_id=admin_chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

        # Update dashboard stats
        increment_alerts()
        set_last_alert(message)

        return {"success": True, "message": f"Test alert sent to chat {admin_chat_id}"}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return {
            "success": False,
            "message": f"Error sending test alert: {str(e)}",
            "details": error_details
        }

@app.get("/status", response_class=HTMLResponse)
async def status_page(request: Request):
    """Render HTML status page"""
    # Calculate uptime
    start_time = datetime.datetime.fromisoformat(bot_status["start_time"])
    uptime_seconds = (datetime.datetime.now() - start_time).total_seconds()
    uptime = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m"

    # Count tokens and convert sets to lists for template
    eth_tokens = len(bot_status["tracked_contracts"]["ethereum"])
    sol_tokens = len(bot_status["tracked_contracts"]["solana"])
    bnb_tokens = len(bot_status["tracked_contracts"]["binance"])

    eth_address_list = list(bot_status["tracked_contracts"]["ethereum"])
    sol_address_list = list(bot_status["tracked_contracts"]["solana"])
    bnb_address_list = list(bot_status["tracked_contracts"]["binance"])

    # Format last update time
    last_update = datetime.datetime.fromisoformat(bot_status["last_update"])
    last_update_time = last_update.strftime("%Y-%m-%d %H:%M:%S")

    return templates.TemplateResponse(
        "status.html", 
        {
            "request": request, 
            "status": bot_status,
            "uptime": uptime,
            "eth_tokens": eth_tokens,
            "sol_tokens": sol_tokens,
            "bnb_tokens": bnb_tokens,
            "eth_address_list": eth_address_list,
            "sol_address_list": sol_address_list,
            "bnb_address_list": bnb_address_list,
            "last_update_time": last_update_time
        }
    )

def update_status(key, value):
    """Update a specific key in the status tracker"""
    bot_status[key] = value
    bot_status["last_update"] = datetime.datetime.now().isoformat()

def add_tracked_contract(address, blockchain="ethereum"):
    """Add a tracked contract to the status"""
    if blockchain in bot_status["tracked_contracts"]:
        # Normalize the address format
        norm_address = address.lower() if blockchain == "ethereum" else address
        bot_status["tracked_contracts"][blockchain].add(norm_address)

def untrack_contract(address, blockchain="ethereum"):
    """Remove a tracked contract from the status"""
    if blockchain in bot_status["tracked_contracts"]:
        # Normalize the address format
        norm_address = address.lower() if blockchain == "ethereum" else address
        if norm_address in bot_status["tracked_contracts"][blockchain]:
            bot_status["tracked_contracts"][blockchain].remove(norm_address)

def increment_alerts():
    """Increment the alerts sent counter"""
    bot_status["alerts_sent"] += 1
    bot_status["last_update"] = datetime.datetime.now().isoformat()

def set_last_alert(alert_text):
    """Set the last alert text"""
    bot_status["last_alert"] = alert_text
    bot_status["last_update"] = datetime.datetime.now().isoformat()

def store_alert(alert_data):
    """Store a recent alert in the dashboard data"""
    # Make sure alert has a timestamp
    if "timestamp" not in alert_data:
        alert_data["timestamp"] = datetime.datetime.now().isoformat()

    # Add to recent alerts list (keep most recent 20)
    bot_status["recent_alerts"].insert(0, alert_data)
    bot_status["recent_alerts"] = bot_status["recent_alerts"][:20]

    # Also update last_alert and increment count
    bot_status["last_alert"] = f"Alert: {alert_data.get('token_symbol', '???')} ${alert_data.get('amount_usd', 0)}"
    increment_alerts()

def update_chat_count(count):
    """Update the telegram chat count"""
    bot_status["telegram_chats"] = count
    bot_status["last_update"] = datetime.datetime.now().isoformat()

def set_monitor_instance(instance):
    """Set the global monitor instance for dashboard statistics"""
    global monitor_instance
    monitor_instance = instance
    logger.info("✅ Monitor instance set in dashboard")

def start_dashboard_server(port=8080):
    """Start the dashboard server in a background thread"""
    logger.info(f"Starting dashboard server on port {port}")

    # Get Replit URL for user reference
    replit_slug = os.environ.get("REPL_SLUG", "ticker-trending-bot")
    replit_owner = os.environ.get("REPL_OWNER", "arasbaker99")
    dashboard_url = f"https://{replit_slug}.{replit_owner}.repl.co"

    logger.info(f"📊 Dashboard will be available at: {dashboard_url}")
    logger.info(f"📊 Direct status URL: {dashboard_url}/status")

    def run_server():
        # Use 0.0.0.0 to make it accessible outside the container
        # Force port 8080 for Replit compatibility
        import nest_asyncio
        import asyncio
        nest_asyncio.apply()
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        port = 8080  # Force port 8080 instead of using environment variable
        print(f"🌐 Starting uvicorn server on http://0.0.0.0:{port}")
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=port, 
            log_level="info",
            proxy_headers=True,
            forwarded_allow_ips="*"
        )

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    logger.info(f"✅ Dashboard started in background thread on port {port}")
    logger.info(f"✅ Access URL: {dashboard_url}")

    return thread

def start_dashboard_thread():
    """Start the dashboard in a background thread"""
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()
    logger.info("✅ Dashboard started in background thread")
    return dashboard_thread

def run_dashboard(port=8080):
    """Run the dashboard server"""
    try:
        # Try the preferred port first
        logger.info(f"Starting dashboard server on port {port}")
        config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)
        server.run()
    except OSError as e:
        # If preferred port is in use, try alternatives
        logger.warning(f"⚠️ Port {port} is in use. Error: {e}")
        for alt_port in [8000, 8001, 8002, 3000]:
            try:
                logger.info(f"Trying alternative port {alt_port}")
                config = uvicorn.Config(app, host="0.0.0.0", port=alt_port, log_level="info")
                server = uvicorn.Server(config)
                server.run()
                break
            except OSError:
                continue
        else:
            logger.error("❌ Could not find an available port for the dashboard")
    except Exception as e:
        logger.error(f"Error starting dashboard: {e}")
def run_server(app, port=8080):
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    return server
    
def run_dashboard_sync(port=8080):
    """Non-threaded dashboard server starter that returns a server object"""
    import uvicorn
    # Make sure we use 0.0.0.0 to be accessible outside the container
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    # Log dashboard URL for convenience
    import os
    replit_slug = os.environ.get("REPL_SLUG", "workspace")
    replit_owner = os.environ.get("REPL_OWNER", "user")
    dashboard_url = f"https://{replit_slug}.{replit_owner}.repl.co/status"
    print(f"📊 Dashboard is running! Access at: {dashboard_url}")
    return server

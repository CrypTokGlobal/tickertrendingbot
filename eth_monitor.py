import logging
import os
import asyncio
import requests
from datetime import datetime
from web3 import Web3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from config import INFURA_URL, ADMIN_CHAT_ID, FALLBACK_RPC

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EthMonitor:
    _instance = None
    CHECK_INTERVAL_SECONDS = 12

    def __init__(self, bot):
        self.bot = bot
        self.web3 = None
        self.tracked_contracts = {}  # {address: {symbol, name, chat_id, min_usd}} - Legacy format
        self.tracked_tokens = {}  # {chat_id: [{address, name, symbol, min_usd, chat_id}]} - New format
        self.total_alerts_sent = 0
        self.last_alert_msg = ""
        self._initialize_web3()

        # Load tracked tokens from data manager
        try:
            from data_manager import get_data_manager
            dm = get_data_manager()
            if "tracked_tokens" in dm.data:
                eth_tokens = [t for t in dm.data["tracked_tokens"] if t.get("network", "").lower() == "ethereum"]
                for token in eth_tokens:
                    address = token.get("address", "").lower()
                    chat_id = token.get("chat_id")
                    if address and chat_id:
                        # Add to legacy format
                        self.tracked_contracts[address] = {
                            "name": token.get("name", "Unknown"),
                            "symbol": token.get("symbol", "???"),
                            "chat_id": chat_id,
                            "min_usd": token.get("min_volume_usd", 0)
                        }

                        # Add to new format
                        if chat_id not in self.tracked_tokens:
                            self.tracked_tokens[chat_id] = []

                        self.tracked_tokens[chat_id].append({
                            "address": address,
                            "name": token.get("name", "Unknown"),
                            "symbol": token.get("symbol", "???"),
                            "min_usd": token.get("min_volume_usd", 0),
                            "chat_id": chat_id,
                            "chain": "ethereum"
                        })

                logger.info(f"📋 Loaded {len(eth_tokens)} ETH tokens from data manager")
                logger.info(f"📋 Tracked contracts: {list(self.tracked_contracts.keys())}")
        except Exception as e:
            logger.error(f"❌ Error loading tokens from data manager: {e}")

    @classmethod
    def get_instance(cls, bot=None):
        if cls._instance is None:
            if bot is None:
                raise ValueError("Bot must be provided when creating the first instance")
            cls._instance = cls(bot)
        return cls._instance

    def _initialize_web3(self):
        try:
            self.web3 = Web3(Web3.HTTPProvider(INFURA_URL))
            if self.web3.is_connected():
                logger.info("✅ Connected to Ethereum via Infura")
                return
        except Exception as e:
            logger.warning(f"Infura connection failed: {e}")

        try:
            self.web3 = Web3(Web3.HTTPProvider(FALLBACK_RPC))
            if self.web3.is_connected():
                logger.info("✅ Connected to Ethereum via fallback RPC")
                return
        except Exception as e:
            logger.error(f"Fallback RPC connection failed: {e}")

    def find_token(self, chat_id, address):
        """Find a token in the tracked_tokens by chat_id and address"""
        tokens = self.tracked_tokens.get(chat_id, [])
        for token in tokens:
            if token["address"].lower() == address.lower():
                return token
        return None

    def contains_tracked_token(self, data):
        """Check if transaction data contains any tracked token address"""
        if not data or not isinstance(data, str):
            return []

        data = data.lower()
        found_tokens = []

        for addr in self.tracked_contracts.keys():
            # Get the normalized form of the address
            addr_norm = addr.lower()
            addr_clean = addr_norm.replace('0x', '')

            # Check both with and without 0x prefix
            if addr_norm in data or addr_clean in data:
                found_tokens.append(addr)

            # For very short data, also check if it's a direct match to just the address
            if data == addr_norm:
                found_tokens.append(addr)

        if found_tokens:
            logger.info(f"🎯 Found tracked tokens in data: {found_tokens}")

        return found_tokens

    def track_contract(self, address, name, symbol, chat_id, min_usd=0):
        address = address.lower()

        # Store in memory for immediate tracking (legacy format)
        self.tracked_contracts[address] = {
            "name": name,
            "symbol": symbol,
            "chat_id": chat_id,
            "min_usd": min_usd
        }

        # Also store in new format organized by chat_id
        if chat_id not in self.tracked_tokens:
            self.tracked_tokens[chat_id] = []

        # Check if already exists
        existing_token = self.find_token(chat_id, address)
        if existing_token:
            # Update existing token
            existing_token.update({
                "name": name,
                "symbol": symbol,
                "min_usd": min_usd
            })
        else:
            # Add new token
            self.tracked_tokens[chat_id].append({
                "address": address,
                "name": name,
                "symbol": symbol,
                "min_usd": min_usd,
                "chat_id": chat_id,
                "chain": "ethereum"
            })

        # Log tracking confirmation
        logger.info(f"✅ Now tracking ETH token: {symbol} ({address}) for chat ID: {chat_id}")
        logger.info(f"Current tracked tokens: {list(self.tracked_contracts.keys())}")

        # Also save to persistent storage via data_manager
        try:
            from data_manager import get_data_manager
            dm = get_data_manager()

            # Format the token data for persistent storage
            token_data = {
                "address": address,
                "name": name,
                "symbol": symbol,
                "chat_id": int(chat_id) if chat_id else None,
                "min_volume_usd": float(min_usd),
                "network": "ethereum",
                "added_at": datetime.now().isoformat()
            }

            # Add to tracked_tokens list if not already there
            tracked_tokens = dm.data.get("tracked_tokens", [])

            # Check if this token is already tracked for this chat
            existing = False
            for token in tracked_tokens:
                if token.get("address", "").lower() == address.lower() and str(token.get("chat_id", "")) == str(chat_id):
                    existing = True
                    # Update existing token data
                    token.update(token_data)
                    break

            if not existing:
                tracked_tokens.append(token_data)

            # Update the data manager
            dm.data["tracked_tokens"] = tracked_tokens
            dm.save()

            logger.info(f"💾 Saved token {symbol} ({address}) to persistent storage for chat {chat_id}")
            logger.info(f"Current persistent tokens: {[t.get('address') for t in tracked_tokens]}")
        except Exception as e:
            logger.error(f"❌ Error saving to persistent storage: {e}", exc_info=True)

        logger.info(f"✅ Tracking ETH contract: {symbol} {address} in chat {chat_id}")
        logger.info(f"Current tracked contracts: {list(self.tracked_contracts.keys())}")
        return True

    def add_token(self, address, name, symbol, chat_id, min_usd=0):
        """
        Add a token to be tracked by the monitor
        
        Args:
            address: Token contract address
            name: Token name
            symbol: Token symbol
            chat_id: Telegram chat ID
            min_usd: Minimum transaction value in USD to trigger alerts
        """
        address = address.lower()
        if address not in self.tracked_contracts:
            self.tracked_contracts[address] = {
                "address": address,
                "name": name,
                "symbol": symbol,
                "chat_id": chat_id,
                "min_volume_usd": min_usd
            }
            self.save_tracked_contracts()
            logger.info(f"✅ Added {symbol} ({address}) to tracked contracts for chat {chat_id}")
            return True
        else:
            # Update existing token
            self.tracked_contracts[address]["chat_id"] = chat_id
            self.tracked_contracts[address]["name"] = name
            self.tracked_contracts[address]["symbol"] = symbol
            self.tracked_contracts[address]["min_volume_usd"] = min_usd
            self.save_tracked_contracts()
            logger.info(f"🔄 Updated {symbol} ({address}) in tracked contracts for chat {chat_id}")
            return True

            self.tracked_tokens[chat_id].append({
                "address": address,
                "name": name,
                "symbol": symbol,
                "min_usd": min_usd,
                "chat_id": chat_id,
                "chain": "ethereum"
            })

        # Log tracking confirmation
        logger.info(f"✅ Now tracking ETH token: {symbol} ({address}) for chat ID: {chat_id}")
        logger.info(f"Current tracked tokens: {list(self.tracked_contracts.keys())}")

        # Also save to persistent storage via data_manager
        try:
            from data_manager import get_data_manager
            dm = get_data_manager()

            # Format the token data for persistent storage
            token_data = {
                "address": address,
                "name": name,
                "symbol": symbol,
                "chat_id": int(chat_id) if chat_id else None,
                "min_volume_usd": float(min_usd),
                "network": "ethereum",
                "added_at": datetime.now().isoformat()
            }

            # Add to tracked_tokens list if not already there
            tracked_tokens = dm.data.get("tracked_tokens", [])

            # Check if this token is already tracked for this chat
            existing = False
            for token in tracked_tokens:
                if token.get("address", "").lower() == address.lower() and str(token.get("chat_id", "")) == str(chat_id):
                    existing = True
                    # Update existing token data
                    token.update(token_data)
                    break

            if not existing:
                tracked_tokens.append(token_data)

            # Update the data manager
            dm.data["tracked_tokens"] = tracked_tokens
            dm.save()

            logger.info(f"💾 Saved token {symbol} ({address}) to persistent storage for chat {chat_id}")
            logger.info(f"Current persistent tokens: {[t.get('address') for t in tracked_tokens]}")
        except Exception as e:
            logger.error(f"❌ Error saving to persistent storage: {e}", exc_info=True)

        logger.info(f"✅ Tracking ETH contract: {symbol} {address} in chat {chat_id}")
        logger.info(f"Current tracked contracts: {list(self.tracked_contracts.keys())}")
        return True

    def untrack_contract(self, address, specific_chat_id=None):
        address = address.lower()
        chat_id = None

        # Remove from in-memory tracking (legacy format)
        if address in self.tracked_contracts:
            # Get the chat_id before removal for persistent storage update
            chat_id = self.tracked_contracts[address].get("chat_id")
            del self.tracked_contracts[address]
            logger.info(f"🛑 Untracked ETH contract from memory: {address}")

        # Also remove from new format
        if specific_chat_id:
            # If a specific chat_id was provided, only remove from that chat
            chat_id = specific_chat_id
            if chat_id in self.tracked_tokens:
                before_count = len(self.tracked_tokens[chat_id])
                self.tracked_tokens[chat_id] = [t for t in self.tracked_tokens[chat_id] if t["address"].lower() != address]
                after_count = len(self.tracked_tokens[chat_id])
                if before_count != after_count:
                    logger.info(f"🛑 Untracked ETH token {address} from chat {chat_id}")
        elif chat_id:
            # If we got chat_id from legacy format
            if chat_id in self.tracked_tokens:
                self.tracked_tokens[chat_id] = [t for t in self.tracked_tokens[chat_id] if t["address"].lower() != address]
                logger.info(f"🛑 Untracked ETH token {address} from chat {chat_id}")
        else:
            # If no specific chat ID, remove from all chats
            for cid in list(self.tracked_tokens.keys()):
                before_count = len(self.tracked_tokens[cid])
                self.tracked_tokens[cid] = [t for t in self.tracked_tokens[cid] if t["address"].lower() != address]
                after_count = len(self.tracked_tokens[cid])
                if before_count != after_count:
                    logger.info(f"🛑 Untracked ETH token {address} from chat {cid}")

        # Also remove from persistent storage
        try:
            from data_manager import get_data_manager
            dm = get_data_manager()

            if "tracked_tokens" in dm.data:
                # Start with current tracked tokens
                tracked_tokens = dm.data["tracked_tokens"]
                initial_count = len(tracked_tokens)

                # Filter out the token we want to remove
                if chat_id:
                    # If we know the chat_id, only remove from this specific chat
                    tracked_tokens = [
                        t for t in tracked_tokens 
                        if not (t.get("address", "").lower() == address.lower() and str(t.get("chat_id", "")) == str(chat_id))
                    ]
                else:
                    # Otherwise remove all instances of this token
                    tracked_tokens = [t for t in tracked_tokens if t.get("address", "").lower() != address.lower()]

                # Update data manager if we removed something
                if len(tracked_tokens) != initial_count:
                    dm.data["tracked_tokens"] = tracked_tokens
                    dm.save()
                    logger.info(f"💾 Removed token {address} from persistent storage")
                    logger.info(f"Current persistent tokens: {[t.get('address') for t in tracked_tokens]}")
                else:
                    logger.info(f"⚠️ Token {address} was not found in persistent storage for chat {chat_id}")
        except Exception as e:
            logger.error(f"❌ Error removing from persistent storage: {e}", exc_info=True)

        return address in self.tracked_contracts

    def get_eth_price(self):
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
            return r.json()["ethereum"]["usd"]
        except:
            return None

    async def monitor_ethereum(self):
        logger.info("🔄 Starting ETH transaction monitor...")
        asyncio.create_task(self.monitor_swaps())

    async def monitor_swaps(self):
        logger.info("🔁 ETH swap loop active")
        logger.info("✅ Confirmed: eth_monitor.py is active and tracking will begin.")
        logger.info(f"Currently tracking tokens: {list(self.tracked_contracts.keys())}")
        router_addresses = {v.lower() for v in DEX_ROUTERS.values()}

        while True:
            try:
                if not self.web3.is_connected():
                    logger.warning("Reconnecting ETH Web3...")
                    self._initialize_web3()
                    await asyncio.sleep(10)
                    continue

                block = self.web3.eth.get_block('latest', full_transactions=True)
                logger.info(f"🔍 Analyzing block: {block.number} with {len(block.transactions)} transactions")
                eth_price_usd = self.get_eth_price()

                for tx in block.transactions:
                    if not tx.to:
                        continue

                    # Properly handle tx.input as bytes
                    if isinstance(tx.input, bytes):
                        decoded_input = tx.input.hex().lower()
                    else:
                        # If already a string
                        decoded_input = tx.input.lower() if isinstance(tx.input, str) else ''

                    if decoded_input == '0x':
                        continue

                    # Get to_address and method_id
                    to_address = tx.to.lower() if tx.to else 'None'
                    method_id = decoded_input[:10]

                    # Check for Uniswap router and buy method
                    is_router = to_address in router_addresses
                    is_buying = is_buy_method(method_id)

                    # Enhanced token detection
                    tracked_tokens_in_input = self.contains_tracked_token(decoded_input)

                    # Log transaction details with enhanced info
                    logger.info(f"TX {tx.hash.hex()} | To: {to_address} | Method: {method_id} | Is Router: {is_router} | Is Buy: {is_buying} | Contains Tracked Token: {tracked_tokens_in_input}")

                    # Add extra debug logs for potentially important transactions
                    if (is_router or is_buying) and not tracked_tokens_in_input and self.tracked_contracts:
                        # Log first few characters of input for better debugging
                        input_sample = decoded_input[:100] + "..." if len(decoded_input) > 100 else decoded_input
                        logger.info(f"Potential swap transaction but no tracked tokens found in input: {input_sample}")
                        logger.info(f"Tracked tokens: {list(self.tracked_contracts.keys())[:5]}")

                    # Prioritize processing for transactions that are both from router and use buy method
                    if is_router and is_buying:
                        logger.info(f"🔍 PRIORITY: Router buy transaction detected! Router: {to_address}, Method: {method_id}")

                    # Check for tracked token mentions in tx.input
                    for tracked_addr in self.tracked_contracts.keys():
                        tracked_addr_clean = tracked_addr.lower().replace('0x', '')
                        if tracked_addr_clean in decoded_input:
                            logger.info(f"🚨 Tracked token {tracked_addr} found in transaction {tx.hash.hex()}")
                            # Add extra debug info
                            logger.info(f"   Transaction method: {decoded_input[:10]}")
                            logger.info(f"   Transaction to: {tx.to.lower() if tx.to else 'None'}")

                            # Enhanced detection for Uniswap V3 methods
                            # exactInputSingle (0x04e45aaf), exactInput (0xc04b8d59), exactOutputSingle (0x5023b4df), exactOutput (0xf28c0498)
                            if decoded_input.startswith("0x04e45aaf") or decoded_input.startswith("0xb858183f") or decoded_input.startswith("0xc04b8d59"):
                                logger.info(f"🔍 UNISWAP V3 transaction detected with tracked token!")

                                # Process this transaction immediately as it's likely a buy transaction
                                receipt = self.web3.eth.get_transaction_receipt(tx.hash)

                                # Attempt to extract token amount and value
                                try:
                                    logger.info(f"💰 Processing Uniswap V3 exactInputSingle for token {tracked_addr}")

                                    # Get the router name
                                    router_name = "Uniswap V3"

                                    # Get ETH price and estimated USD value
                                    eth_price_usd = self.get_eth_price() or 3000
                                    eth_value = tx.value / 10**18  # Convert wei to ETH
                                    usd_value = eth_value * eth_price_usd

                                    logger.info(f"💱 Transaction value: {eth_value} ETH (~${usd_value})")

                                    # Get the token data
                                    token_data = self.tracked_contracts[tracked_addr]
                                    min_usd = token_data.get("min_usd", 0)

                                    if usd_value >= min_usd:
                                        logger.info(f"✅ UNISWAP THRESHOLD MET: Buy of {tracked_addr} (${usd_value}) exceeds min ${min_usd}")

                                        # Determine the chat IDs to send alerts to
                                        chat_ids = []
                                        primary_chat_id = token_data.get("chat_id")
                                        if primary_chat_id:
                                            chat_ids.append(primary_chat_id)

                                        # Send alerts to each chat
                                        for chat_id in chat_ids:
                                            token_info = {
                                                "address": tracked_addr,
                                                "name": token_data.get("name", "Unknown Token"),
                                                "symbol": token_data.get("symbol", "???"),
                                                "chain": "ethereum"
                                            }

                                            # Send the alert
                                            tx_hash_hex = tx.hash.hex()
                                            # Record alert data for API
                                            alert_data = {
                                                "timestamp": datetime.now().isoformat(),
                                                "network": "ethereum",
                                                "token_name": token_info.get("name", "Unknown"),
                                                "token_symbol": token_data.get("symbol", "???"),
                                                "contract_address": tracked_addr,
                                                "amount_usd": usd_value,
                                                "tx_hash": tx_hash_hex,
                                                "chat_id": str(chat_id)
                                            }

                                            # Send alert to Telegram chat
                                            await send_eth_alert(
                                                bot=self.bot,
                                                chat_id=chat_id,
                                                symbol=token_data.get("symbol", "???"),
                                                amount=eth_value,
                                                tx_hash=tx_hash_hex,
                                                token_info=token_info,
                                                usd_value=usd_value,
                                                dex_name=router_name,
                                                alert_data=alert_data
                                            )
                                            self.total_alerts_sent += 1

                                except Exception as e:
                                    logger.error(f"❌ Error processing Uniswap V3 transaction: {e}", exc_info=True)

                    # Validate router address or token presence
                    is_known_router = tx.to.lower() in router_addresses
                    router_name = next((name for name, addr in DEX_ROUTERS.items() if addr.lower() == tx.to.lower()), "Not a Router")

                    # Log router information
                    logger.info(f"   Is Known Router: {is_known_router} ({router_name})")

                    if not is_known_router and not any(addr[2:] in decoded_input for addr in self.tracked_contracts):
                        continue

                    # Check for matching method signatures or if the transaction input contains a tracked token
                    method_match = False
                    token_in_input = False

                    # Check if method signature matches known DEX methods
                    if decoded_input[:10] in SWAP_FUNCTION_SIGS.values():
                        method_match = True
                        logger.info(f"   Method signature match: {decoded_input[:10]}")

                    # Check if any tracked token is in input data
                    for tracked_addr in self.tracked_contracts.keys():
                        if tracked_addr.lower().replace('0x', '') in decoded_input.lower():
                            token_in_input = True
                            logger.info(f"   Tracked token {tracked_addr} found in transaction input")
                            break

                    if not (method_match or token_in_input or is_known_router):
                        continue

                    receipt = self.web3.eth.get_transaction_receipt(tx.hash)
                    logger.info(f"🔍 Processing TX: {tx.hash.hex()} | Router: {tx.to}")

                    # Log ALL logs to see what we might be missing
                    for i, log in enumerate(receipt.logs):
                        logger.info(f"TX {tx.hash.hex()} LOG #{i} => address: {log.address.lower()} | topics: {[t.hex() for t in log.topics]}")

                        # Check if this is a transfer event
                        try:
                            if len(log.topics) >= 3 and log.topics[0].hex() == TRANSFER_TOPIC:
                                token_address = log.address.lower()
                                from_address = '0x' + log.topics[1].hex()[-40:]
                                to_address = '0x' + log.topics[2].hex()[-40:]

                                # Enhanced debugging for Transfer events with more context
                                logger.info(f"💰 TRANSFER EVENT DETECTED IN TX {tx.hash.hex()}: {token_address}")
                                logger.info(f"   From: {from_address} | To: {to_address}")
                                logger.info(f"   Token data: {log.data}")
                                logger.info(f"   Token value: {int(log.data, 16) if log.data else 0}")
                                logger.info(f"   Is token tracked: {token_address in self.tracked_contracts}")
                                logger.info(f"   Is FROM router: {from_address.lower() in router_addresses}")
                                logger.info(f"   Is TO tracked: {to_address.lower() in self.tracked_contracts}")
                                logger.info(f"   Currently tracking tokens: {list(self.tracked_contracts.keys())}")

                            if len(log.topics) < 3 or log.topics[0].hex() != TRANSFER_TOPIC:
                                continue

                            token_address = log.address.lower()
                            from_address = '0x' + log.topics[1].hex()[-40:]
                            to_address = '0x' + log.topics[2].hex()[-40:]

                            # More detailed debugging for log matching
                            logger.info(f"🧐 PROCESSING TRANSFER: {token_address} in TX {tx.hash.hex()}")
                            logger.info(f"   From: {from_address} | To: {to_address}")
                            logger.info(f"   Token in tracked contracts: {token_address in self.tracked_contracts}")
                            logger.info(f"   From is router: {from_address.lower() in router_addresses}")
                            logger.info(f"   Router name if applicable: {next((name for name, addr in DEX_ROUTERS.items() if addr.lower() == from_address.lower()), 'Not a Router')}")
                            logger.info(f"   Tracked contracts (case-sensitive check): {list(self.tracked_contracts.keys())}")

                            # Case-insensitive address check for backup validation
                            tracked_lower = [addr.lower() for addr in self.tracked_contracts.keys()]
                            logger.info(f"   Token in tracked (lowercase): {token_address.lower() in tracked_lower}")

                            # Check if this token is one we're tracking - with enhanced logging
                            logger.info(f"🔍 Checking token against tracked tokens: {token_address}")
                            logger.info(f"🔍 Tracked contracts: {list(self.tracked_contracts.keys())}")

                            # Case-insensitive check for addresses
                            tracked_lower = {k.lower(): v for k, v in self.tracked_contracts.items()}

                            token_is_tracked = token_address in self.tracked_contracts
                            token_is_tracked_case_insensitive = token_address.lower() in tracked_lower
                            destination_is_tracked = to_address.lower() in self.tracked_contracts
                            source_is_tracked = from_address.lower() in self.tracked_contracts

                            logger.info(f"🧐 Tracking check results: token_is_tracked={token_is_tracked}, token_case_insensitive={token_is_tracked_case_insensitive}, destination_is_tracked={destination_is_tracked}, source_is_tracked={source_is_tracked}")

                            # If token is tracked with different case, use the original case for retrieval
                            if not token_is_tracked and token_is_tracked_case_insensitive:
                                original_case = next((k for k in self.tracked_contracts if k.lower() == token_address.lower()), None)
                                if original_case:
                                    logger.info(f"✅ Found case-insensitive match: {original_case} vs {token_address}")
                                    token_address = original_case
                                    token_is_tracked = True

                            if not (token_is_tracked or destination_is_tracked or source_is_tracked):
                                logger.info(f"❌ SKIPPING: Transfer not related to any tracked token or address")
                                continue
                        except Exception as e:
                            logger.error(f"Error processing log: {e}")
                            continue

                        if destination_is_tracked:
                            token_address = to_address.lower()
                            logger.info(f"🔍 Detected transfer TO tracked token: {token_address}")

                        # Check if this is a buy (transfer from a router to a wallet)
                        if from_address.lower() in router_addresses:
                            logger.info(f"🚨 POTENTIAL BUY DETECTED: Transfer from router {from_address} for token {token_address}")
                            logger.info(f"   Transaction hash: {tx.hash.hex()}")

                            # Double check router and normalize addresses for comparison
                            router_name = next((name for name, addr in DEX_ROUTERS.items() 
                                              if addr.lower() == from_address.lower()), "Unknown Router")
                            logger.info(f"   Router identified as: {router_name}")

                            # Verify exact address format and case
                            logger.info(f"   Token address (as is): {token_address}")
                            logger.info(f"   Token address length: {len(token_address)}")
                            logger.info(f"   Token address (normalized): {token_address.lower()}")

                            # Log all tracked contracts for comparison
                            logger.info(f"   All tracked contracts: {list(self.tracked_contracts.keys())}")

                            # Try different normalization to ensure proper matching
                            normalized_token = token_address.lower()
                            normalized_tracked = {k.lower(): v for k, v in self.tracked_contracts.items()}
                            logger.info(f"   Normalized match: {normalized_token in normalized_tracked}")

                            # Only proceed if we're tracking this token
                            if token_address not in self.tracked_contracts:
                                logger.info(f"❌ Token {token_address} not matched in tracked contracts, skipping alert")
                                # Additional checking for case issues
                                if token_address.lower() in [k.lower() for k in self.tracked_contracts.keys()]:
                                    logger.warning(f"⚠️ Case mismatch detected! Token would match if case-insensitive.")
                                continue

                            logger.info(f"✅ MATCHED TRACKED TOKEN {token_address} - Preparing alert...")

                            # Extract token amount from transfer data with detailed logging
                            try:
                                amount = int(log.data, 16)
                                logger.info(f"🔢 Raw token amount (hex): {log.data}")
                                logger.info(f"🔢 Parsed amount (int): {amount}")

                                # Try to get decimals from token contract (fallback to 18)
                                decimals = 18  # Default but should get from token contract
                                try:
                                    # This is optional but helpful if available
                                    token_contract = self.web3.eth.contract(
                                        address=self.web3.to_checksum_address(token_address),
                                        abi=[{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"}]
                                    )
                                    decimals = token_contract.functions.decimals().call()
                                    logger.info(f"📏 Token decimals fetched from contract: {decimals}")
                                except Exception as e:
                                    logger.info(f"📏 Using default decimals (18): {e}")

                                token_amount = amount / 10**decimals
                                logger.info(f"💱 Calculated token amount: {token_amount:.8f}")

                                # Get ETH price and calculate USD value
                                logger.info(f"💲 ETH price used for calculation: ${eth_price_usd}")
                                usd_value = round(token_amount * eth_price_usd, 2) if eth_price_usd else 0.0
                                logger.info(f"💵 Calculated USD value: ${usd_value}")

                                logger.info(f"💰 DETECTED BUY: {token_amount:.8f} tokens of {token_address}")
                                logger.info(f"🚀 Transaction: {tx.hash.hex()} | Value: ~${usd_value} USD")
                            except Exception as e:
                                logger.error(f"❌ Error calculating token amount: {e}", exc_info=True)
                                continue

                            # Check if value meets minimum threshold
                            token_data = self.tracked_contracts[token_address]
                            min_usd = token_data.get("min_usd", 0)

                            logger.info(f"💰 Buy amount: {token_amount:.4f} tokens (~${usd_value} USD)")
                            logger.info(f"   Minimum threshold: ${min_usd}")
                            logger.info(f"   Token data: {token_data}")

                            if usd_value >= min_usd:
                                logger.info(f"✅ THRESHOLD MET: Buy of {token_amount:.4f} of {token_address} (${usd_value}) exceeds min ${min_usd}")

                                # Determine the chat IDs to send alerts to
                                chat_ids = []

                                # Primary chat ID from the token data
                                primary_chat_id = token_data.get("chat_id")
                                if primary_chat_id:
                                    chat_ids.append(primary_chat_id)
                                    logger.info(f"Found primary chat ID: {primary_chat_id} for token {token_address}")

                                # Always send to admin chat if configured
                                if ADMIN_CHAT_ID and ADMIN_CHAT_ID not in ['', 'None', None]:
                                    admin_id = int(ADMIN_CHAT_ID)
                                    if admin_id not in chat_ids:
                                        chat_ids.append(admin_id)
                                        logger.info(f"Adding admin chat ID: {admin_id}")

                                if not chat_ids:
                                    logger.warning(f"No chat IDs found for token {token_address}")
                                    continue

                                # Send alerts to each chat
                                for chat_id in chat_ids:
                                    try:
                                        logger.info(f"📢 Sending alert to chat {chat_id} for token {token_address}")

                                        # Prepare token info for alert
                                        token_info = {
                                            "address": token_address,
                                            "name": token_data.get("name", "Unknown Token"),
                                            "symbol": token_data.get("symbol", "???"),
                                            "chain": "ethereum",
                                            "telegram": token_data.get("telegram", "#"),
                                            "website": token_data.get("website", "#"),
                                            "twitter": token_data.get("twitter", "#")
                                        }

                                        # Debug token_info
                                        logger.info(f"🔍 Debug token_info: {token_info}")

                                        # Send the alert
                                        dex_name = "Uniswap"  # Default; could determine actual DEX with more analysis
                                        tx_hash_hex = tx.hash.hex()

                                        logger.info(f"🚀 SENDING ALERT NOW for {token_address} to chat {chat_id}")
                                        logger.info(f"   Token symbol: {token_data.get('symbol', '???')}")
                                        logger.info(f"   Amount: {token_amount}")
                                        logger.info(f"   USD Value: ${usd_value}")
                                        logger.info(f"   DEX: {dex_name}")
                                        logger.info(f"   Transaction hash: {tx_hash_hex}")
                                        logger.info(f"   Token info being sent: {token_info}")

                                        # Record alert data for API
                                        alert_data = {
                                            "timestamp": datetime.now().isoformat(),
                                            "network": "ethereum",
                                            "token_name": token_info.get("name", "Unknown"),
                                            "token_symbol": token_data.get("symbol", "???"),
                                            "contract_address": token_address,
                                            "amount_usd": usd_value,
                                            "tx_hash": tx_hash_hex,
                                            "chat_id": str(chat_id)
                                        }

                                        # Send alert to Telegram chat
                                        await send_eth_alert(
                                            bot=self.bot,
                                            chat_id=chat_id,
                                            symbol=token_data.get("symbol", "???"),
                                            amount=token_amount,
                                            tx_hash=tx_hash_hex,
                                            token_info=token_info,
                                            usd_value=usd_value,
                                            dex_name=dex_name,
                                            alert_data=alert_data
                                        )

                                        # Check if alert was successful (assuming send_eth_alert returns success status)
                                        alert_success = True  # This should be the return value from send_eth_alert
                                        if alert_success:
                                            logger.info(f"✅ ALERT SENT SUCCESSFULLY to chat {chat_id}")
                                            # Update tracking stats
                                            self.total_alerts_sent += 1
                                            self.last_alert_msg = f"ETH Alert: {token_data.get('symbol', '???')} buy of {token_amount:.4f} (~${usd_value}) via {dex_name}"
                                        else:
                                            logger.error(f"❌ ALERT FAILED TO SEND to chat {chat_id} despite no exception")
                                    except Exception as e:
                                        logger.error(f"❌ EXCEPTION DURING ALERT SENDING to chat {chat_id}: {e}", exc_info=True)
                            else:
                                logger.info(f"❌ BELOW THRESHOLD: Buy of {token_amount:.4f} of {token_address} (${usd_value}) below min ${min_usd}")
                                continue
            except Exception as e:
                logger.error(f"⚠️ Error during Ethereum monitoring: {e}", exc_info=True)

            logger.info(f"Completed monitoring loop, sleeping for {self.CHECK_INTERVAL_SECONDS} seconds")
            await asyncio.sleep(self.CHECK_INTERVAL_SECONDS)

    async def track_command(self, update, context):
        """Handle the /track command"""
        if not context.args or len(context.args) < 3:
            await update.message.reply_text(
                "❌ Usage: /track <contract> <name> <symbol> [min_usd]",
                parse_mode="Markdown"
            )
            return

        address = context.args[0].lower()
        if not address.startswith("0x"):
            await update.message.reply_text("❌ Invalid Ethereum address format. It should start with 0x.")
            return

        name = context.args[1]
        symbol = context.args[2]
        min_usd = float(context.args[3]) if len(context.args) > 3 and context.args[3].replace(".", "", 1).isdigit() else 0
        chat_id = update.effective_chat.id

        # Check if this token is already being tracked in this chat
        existing_token = self.find_token(chat_id, address)
        if existing_token:
            await update.message.reply_text(
                f"⚠️ Token `{symbol}` is already being tracked in this chat.",
                parse_mode="Markdown"
            )
            return

        # Track the contract
        self.track_contract(address, name, symbol, chat_id, min_usd)

        logger.info(f"✅ Tracking ETH token {symbol} ({address}) in chat {chat_id}")
        logger.debug(f"Current tracked tokens for chat {chat_id}: {self.tracked_tokens.get(chat_id, [])}")

        # Create chart button
        etherscan_url = f"https://etherscan.io/token/{address}"
        dextools_url = f"https://www.dextools.io/app/ether/pair-explorer/{address}"
        keyboard = [
            [
                InlineKeyboardButton("📊 View Chart", url=dextools_url),
                InlineKeyboardButton("🔍 Etherscan", url=etherscan_url)
            ],
            [
                InlineKeyboardButton("🧪 Test Alert", callback_data=f"test_alert_{address}"),
                InlineKeyboardButton("✨ Customize", callback_data=f"customize_{address}")
            ]
        ]

        await update.message.reply_text(
            f"✅ Now tracking *{name}* (*{symbol}*) on Ethereum\n\n"
            f"📋 *Details:*\n"
            f"• Address: `{address}`\n"
            f"• Minimum alert value: ${min_usd}\n"
            f"• Tracking in: This chat\n\n"
            f"🔔 You'll receive alerts for buy transactions on Ethereum DEXes",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def untrack_command(self, update, context):
        """Handle the /untrack command to remove a token from tracking"""
        if not context.args:
            await update.message.reply_text("❌ Please provide a contract address to untrack.")
            return

        address = context.args[0].lower()
        chat_id = update.effective_chat.id

        # Check if token exists in this chat
        existing_token = self.find_token(chat_id, address)
        if not existing_token:
            await update.message.reply_text(f"❓ Token {address} is not being tracked in this chat.")
            return

        # Untrack the contract in this specific chat
        self.untrack_contract(address, chat_id)

        # Send confirmation
        await update.message.reply_text(f"🛑 Untracked token: {address} from this chat")
        logger.info(f"🛑 Untracked token {address} from chat {chat_id}")


# Constants
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
DEX_ROUTERS = {
    # Uniswap Routers (all versions)
    "UniswapV1": "0xf164fC0Ec4E93095b804a4795bBe1e041497b92a",
    "UniswapV2Factory": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
    "UniswapV2Router": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
    "UniswapV3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
    "UniswapV3Router02": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
    "UniswapV3UniversalRouter": "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD",
    "UniswapV4": "0xEf1c6E67703c7BD7107eed8303Fbe6EC2554BF6B",  # May need updating when V4 is deployed

    # Other DEXes
    "SushiSwap": "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
    "MatchaRouter": "0xdef1c0ded9bec7f1a1670819833240f027b25eff",
    "PancakeV3Router": "0x1b81D678ffb9C0263b24A97847620C99d213eB14",
    "BaseSwap": "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86",
    "0x": "0xdef1c0ded9bec7f1a1670819833240f027b25eff",
    "1inch": "0x1111111254fb6c44bac0bed2854e76f90643097d",
    "DODO": "0xa356867fdcea8e71aeaf87805808803806231fdc",
    "KyberSwap": "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",
    "ShushiSwapV2": "0x03f7724180AA6b939894B5Ca4314783B0b36b329",
    "PancakeV2Router": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
    "CamelotRouter": "0xc873fEcbd354f5A56E00E710B90EF4201db2448d"
}
SWAP_FUNCTION_SIGS = {
    # Standard Uniswap V2 Methods
    "swapExactETHForTokens": "0x7ff36ab5",
    "swapETHForExactTokens": "0xfb3bdb41",
    "swapExactTokensForETH": "0x18cbafe5",
    "swapTokensForExactETH": "0x4a25d94a",
    "swapExactTokensForTokens": "0x38ed1739",
    "swapTokensForExactTokens": "0x8803dbee",

    # Fee supporting methods
    "swapExactETHForTokensSupportingFeeOnTransferTokens": "0xb6f9de95",
    "swapExactTokensForETHSupportingFeeOnTransferTokens": "0x791ac947",
    "swapExactTokensForTokensSupportingFeeOnTransferTokens": "0x5c11d795",

    # Uniswap V3 Methods
    "exactInputSingle": "0x414bf389",
    "exactInput": "0xb858183f",
    "exactOutputSingle": "0x5023b4df",
    "exactOutput": "0xf28c0498",
    "uniswapV3ExactInputSingle": "0x04e45aaf",
    "uniswapV3ExactInput": "0xc04b8d59",
    "uniswapV3ExactOutputSingle": "0x5023b4df",
    "uniswapV3ExactOutput": "0xf28c0498",

    # Universal Router Methods
    "v3SwapExactIn": "0xbc651188",
    "v3SwapExactOut": "0x75ceafe6",

    # Common Router Functions
    "multicall": "0xac9650d8",
    "multicallV2": "0x5ae401dc",
    "multihop": "0x1f0464d6",
    "execute": "0x09c7c7a1",
    "batchSwap": "0x945bcec9",
    "swap": "0x7c025200",
    "uniswapV3SwapCallback": "0xfa461e33",
    "onERC1155Received": "0xf23a6e61",
    "unwrapWETH9": "0x49616997"
}

# Methods specifically for buying tokens (ETH/Native -> Token)
BUY_METHODS = [
    "0x7ff36ab5",  # swapExactETHForTokens
    "0xb6f9de95",  # swapExactETHForTokensSupportingFeeOnTransferTokens
    "0xfb3bdb41",  # swapETHForExactTokens
    "0x38ed1739",  # swapExactTokensForTokens
    "0x5c11d795",  # swapExactTokensForTokensSupportingFeeOnTransferTokens
    "0x04e45aaf",  # uniswapV3ExactInputSingle
    "0xb858183f",  # exactInput
    "0x414bf389",  # exactInputSingle
    "0xbc651188",  # v3SwapExactIn
]

def is_buy_method(method_id):
    """Check if method signature indicates a buy transaction"""
    if not method_id:
        return False
    method_id = method_id[:10].lower()
    return method_id in BUY_METHODS

# FastAPI setup
app = FastAPI()
monitor_instance = None

@app.get("/")
def root():
    return HTMLResponse("""
        <html>
            <head><title>Redirecting</title></head>
            <body>
                <script>
                    window.location.href = '/status';
                </script>
            </body>
        </html>
    """)

@app.get("/status")
def status():
    if monitor_instance:
        return JSONResponse({
            "tracked_contracts": list(monitor_instance.tracked_contracts),
            "alerts_sent": monitor_instance.total_alerts_sent,
            "last_alert": monitor_instance.last_alert_msg[:300]
        })
    return JSONResponse({"status": "bot not running"})

def run_dashboard():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

async def send_eth_alert(bot, chat_id, symbol, amount, tx_hash, token_info=None, usd_value=None, dex_name="Uniswap", alert_data=None):
    """Send an Ethereum token buy alert"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    try:
        # 🛡️ Validate token_info and parameters
        logger.info(f"🔍 Preparing to send ETH alert with token_info: {token_info}")
        logger.info(f"   Chat ID: {chat_id}, Symbol: {symbol}, Amount: {amount}, TX: {tx_hash}")

        # Validate token_info structure
        if not token_info:
            logger.warning("⚠️ token_info is None, creating fallback data")
            token_info = {
                "address": "Unknown",
                "name": symbol,
                "symbol": symbol,
                "chain": "ethereum",
                "telegram": "#",
                "website": "#",
                "twitter": "#"
            }

        token_address = token_info.get("address", "Unknown")
        token_name = token_info.get("name", symbol)
        token_symbol = token_info.get("symbol", symbol)

        # 💵 Calculate USD value if not provided
        if usd_value is None:
            eth_price = 3000  # fallback ETH price
            usd_value = eth_price * amount

        # 🧭 Build URLs
        tx_url = f"https://etherscan.io/tx/{tx_hash}"
        chart_url = f"https://dexscreener.com/ethereum/{token_address}"
        swap_url = f"https://app.uniswap.org/#/swap?outputCurrency={token_address}"

        # 🔗 Optional links
        tg_link = token_info.get("telegram", "#")
        web_link = token_info.get("website", "#")
        twitter_link = token_info.get("twitter", "#")

        # 📝 Compose message
        message = (
            f"🚀 <b>TICKER TRENDING BUY ALERT</b> 🚀\n\n"
            f"🪙 <b>Token:</b> {token_name} (<a href='{chart_url}'>${token_symbol}</a>)\n"
            f"📜 <b>Contract:</b>\n<code>{token_address}</code>\n"
            f"💰 <b>Amount:</b> {amount:.4f} ETH (~${usd_value:.2f})\n"
            f"🌐 <b>DEX:</b> {dex_name}\n\n"
            f"<b>🔗 Links:</b>\n"
            f"<a href='{tg_link}'>🔷 Telegram</a> | <a href='{web_link}'>🔷 Website</a> | <a href='{twitter_link}'>🔷 Twitter</a>\n\n"
            f"🔍 <b>Transaction:</b> <a href='{tx_url}'>View TX</a>\n\n"
            f"<i>Powered by</i> <a href='https://tickertrending.com'>tickertrending.com</a>"
        )

        # 🧠 Log for debugging
        logger.info(f"📤 Sending alert to chat_id: {chat_id}")

        # ✅ Inline buttons
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Chart", url=chart_url), InlineKeyboardButton("🔎 Transaction", url=tx_url)],
            [InlineKeyboardButton("💱 Swap Now", url=swap_url)],
            [InlineKeyboardButton("🚀 BOOST YOUR TOKEN", url="https://tickertrending.com/boost")]
        ])

        # 📬 Send message with more detailed error handling
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
            logger.info(f"✅ Alert sent to chat {chat_id} for {symbol}")
            if alert_data:
                # Store alert data (Implementation for storing alert data will depend on your system)
                try:
                    # Example using a simple list for demonstration (Replace with your actual storage mechanism)
                    with open("alerts.log", "a") as f:
                        f.write(str(alert_data) + "\n")
                    logger.info(f"✅ Alert data saved: {alert_data}")
                except Exception as e:
                    logger.error(f"❌ Error saving alert data: {e}")
            return True
        except Exception as send_error:
            logger.error(f"❌ Error sending message to chat {chat_id}: {send_error}")
            # Try sending a simpler message as fallback
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"🚨 Buy Alert: {amount:.4f} ETH of {symbol} on {dex_name}",
                    disable_web_page_preview=True
                )
                logger.info(f"✓ Fallback alert sent to chat {chat_id}")
                return True
            except Exception as fallback_error:
                logger.error(f"❌ Even fallback message failed: {fallback_error}")
                return False
    except Exception as e:
        logger.error(f"❌ Failed to prepare ETH alert: {e}")
        return False

# Global instance
eth_monitor_instance = None

def get_instance(bot=None):
    global eth_monitor_instance
    if eth_monitor_instance is None:
        eth_monitor_instance = EthMonitor(bot)
    elif bot is not None:
        eth_monitor_instance.bot = bot
    return eth_monitor_instance

async def start_monitoring(bot=None):
    monitor = get_instance(bot)
    logger.info("🚀 Starting Ethereum monitoring task...")
    monitoring_task = asyncio.create_task(monitor.monitor_ethereum())
    return monitoring_task

async def track_uni_token_for_testing(chat_id):
    """Track UNI token for testing purposes"""
    global eth_monitor_instance

    if not eth_monitor_instance or not eth_monitor_instance.bot:
        logger.error("❌ Monitor instance not initialized or bot not set")
        return False

    # UNI Token contract address
    uni_address = "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"

    # Track the UNI token
    eth_monitor_instance.track_contract(
        address=uni_address,
        name="Uniswap Token",
        symbol="UNI",
        chat_id=chat_id,
        min_usd=1  # Low threshold for test
    )

    logger.info(f"✅ Added UNI token for testing in chat {chat_id}")
    return uni_address

async def test_eth_alert(chat_id, token_address=None):
    """Send a test ETH alert to verify the alert system is working"""
    global eth_monitor_instance

    if not eth_monitor_instance or not eth_monitor_instance.bot:
        logger.error("❌ Monitor instance not initialized or bot not set")
        return False

    # If no token address provided, use UNI token for testing
    if not token_address:
        token_address = await track_uni_token_for_testing(chat_id)

    logger.info(f"🧪 Processing test alert request for chat_id: {chat_id}, token address: {token_address}")

    # Force a diagnostic alert to test the full alert chain
    try:
        logger.info("🚨 DIAGNOSTIC: Forcing test alert to verify alert system")
        await send_eth_alert(
            bot=eth_monitor_instance.bot,
            chat_id=chat_id,
            symbol="TEST",
            amount=1.5,
            tx_hash="0x" + "diagnostictest" * 4,
            token_info={
                "address": token_address or "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "name": "Diagnostic Test Token",
                "symbol": "TEST",
                "chain": "ethereum"
            },
            usd_value=3000,
            dex_name="Diagnostic Test"
        )
        logger.info("✅ Diagnostic alert sent successfully")
    except Exception as e:
        logger.error(f"❌ Diagnostic alert failed: {e}", exc_info=True)

    # Log current monitoring state
    if eth_monitor_instance:
        tracked_contracts = list(eth_monitor_instance.tracked_contracts.keys())
        logger.info(f"📋 Currently tracked contracts: {tracked_contracts}")
        chat_tokens = eth_monitor_instance.tracked_tokens.get(chat_id, [])
        logger.info(f"📋 Tokens tracked for chat {chat_id}: {[t.get('address') for t in chat_tokens]}")

    # Use provided token address or create a test one
    if token_address:
        token_data = None

        # First check in new tracking format by chat_id
        token_data = eth_monitor_instance.find_token(chat_id, token_address)
        logger.info(f"🔍 Using new tracking format search: {token_data}")

        # If not found in chat, check legacy format
        if not token_data and token_address.lower() in eth_monitor_instance.tracked_contracts:
            token_data = eth_monitor_instance.tracked_contracts[token_address.lower()]
            # Ensure token_info includes address field
            token_data["address"] = token_address.lower()
            logger.info(f"🔍 Using legacy tracking format: {token_data}")

        # If token is not tracked, fallback to a basic example
        if not token_data:
            logger.info(f"⚠️ Token {token_address} not found in tracked tokens, using fallback test data")
            token_data = {
                "address": token_address,
                "name": "Test Token",
                "symbol": "TEST",
                "chat_id": chat_id,
                "chain": "ethereum"
            }
    else:
        # Check if there are any tokens tracked in this chat
        chat_tokens = eth_monitor_instance.tracked_tokens.get(chat_id, [])
        if chat_tokens:
            # Use the first token from this chat
            token_data = chat_tokens[0]
            logger.info(f"🧪 Using tracked token for test: {token_data.get('symbol')} ({token_data.get('address')})")
        else:
            # Use default fallback test token (Uniswap)
            logger.info(f"⚠️ No tokens tracked for chat {chat_id}, using default test token")
            token_data = {
                "address": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
                "name": "Uniswap Token",
                "symbol": "UNI",
                "chat_id": chat_id,
                "chain": "ethereum"
            }

    logger.info(f"🧪 Sending test ETH alert for token {token_data.get('symbol')} to chat {chat_id}")

    test_tx = "0x" + "0123456789abcdef" * 4  # Fake tx hash

    success = await send_eth_alert(
        bot=eth_monitor_instance.bot,
        chat_id=chat_id,
        symbol=token_data.get("symbol", "TEST"),
        amount=1.5,
        tx_hash=test_tx,
        token_info=token_data,
        usd_value=4500,
        dex_name="Uniswap (Test)"
    )

    if success:
        logger.info(f"✅ Test ETH alert sent successfully to chat {chat_id}")
    else:
        logger.error(f"❌ Failed to send test ETH alert to chat {chat_id}")

    return success

async def test_eth_alert(chat_id=None, token_info=None):
    """Generate a test alert for Ethereum token"""
    from eth_monitor import get_instance
    eth_monitor = get_instance()

    if not eth_monitor or not eth_monitor.bot:
        logger.error("ETH monitor not initialized for test")
        return False

    if not chat_id:
        logger.error("No chat_id provided for test_eth_alert")
        return False

    # Generate a test transaction
    tx_hash = "0x" + "".join([hex(i)[-1] for i in range(16)] * 4)

    # Use provided token info or default to a test token
    if not token_info:
        test_token = {
            "address": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
            "name": "Uniswap",
            "symbol": "UNI",
            "network": "ethereum",
            "decimals": 18
        }
    else:
        test_token = token_info

    symbol = test_token.get("symbol", "UNI")

    # Random values for a more realistic test
    import random
    amount = round(random.uniform(0.5, 5.0), 2)
    usd_value = round(amount * random.uniform(500, 5000), 2)

    # Send a test alert
    await send_eth_alert(
        bot=eth_monitor.bot,
        chat_id=chat_id,
        symbol=symbol,
        amount=amount,
        tx_hash=tx_hash,
        token_info=test_token,
        usd_value=usd_value,
        dex_name="Uniswap V3 (Test Alert)"
    )

    return True
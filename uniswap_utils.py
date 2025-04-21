
import os
import json
import logging
from web3 import Web3
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniswapInteraction:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Connect to Ethereum network
        self.infura_url = os.getenv("INFURA_URL")
        if not self.infura_url:
            logger.error("No INFURA_URL found in .env file")
            raise ValueError("INFURA_URL not set in .env file")
        
        self.w3 = Web3(Web3.HTTPProvider(self.infura_url))
        if not self.w3.is_connected():
            logger.error("Failed to connect to Ethereum network")
            raise ConnectionError("Failed to connect to Ethereum network")
        
        # Load wallet
        self.private_key = os.getenv("PRIVATE_KEY")
        self.wallet_address = os.getenv("WALLET_ADDRESS")
        if not self.private_key or not self.wallet_address:
            logger.warning("Wallet credentials not set in .env file")
        
        # Uniswap V2 Router address
        self.uniswap_router_address = os.getenv("UNISWAP_ROUTER_ADDRESS", "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")
        
        # WETH address on Ethereum mainnet
        self.weth_address = os.getenv("WETH_ADDRESS", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
        
        # Load Uniswap Router ABI
        self.router_abi = self._load_abi("uniswap_router_abi.json")
        
        # Initialize router contract
        self.router = self.w3.eth.contract(address=self.uniswap_router_address, abi=self.router_abi)
    
    def _load_abi(self, filename):
        """Load ABI from file or return a minimal ABI for basic functions."""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"ABI file {filename} not found, using minimal ABI")
            # Minimal ABI for key functions
            return [
                {
                    "inputs": [
                        {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                        {"internalType": "address[]", "name": "path", "type": "address[]"},
                        {"internalType": "address", "name": "to", "type": "address"},
                        {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                    ],
                    "name": "swapExactETHForTokens",
                    "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
                    "stateMutability": "payable",
                    "type": "function"
                },
                {
                    "inputs": [
                        {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                        {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                        {"internalType": "address[]", "name": "path", "type": "address[]"},
                        {"internalType": "address", "name": "to", "type": "address"},
                        {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                    ],
                    "name": "swapExactTokensForETH",
                    "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [
                        {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                        {"internalType": "address[]", "name": "path", "type": "address[]"}
                    ],
                    "name": "getAmountsOut",
                    "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
    
    def get_token_price(self, token_address):
        """Get the price of a token in ETH."""
        try:
            token_contract = self.w3.eth.contract(address=token_address, abi=[{
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            }])

            # Try to get token decimals, fallback to 18 if it fails
            try:
                decimals = token_contract.functions.decimals().call()
                logger.info(f"Token {token_address} has {decimals} decimals")
            except Exception as e:
                logger.warning(f"Could not determine token decimals, defaulting to 18: {e}")
                decimals = 18
                
            amount_in = 10 ** decimals  # 1 full token

            path = [token_address, self.weth_address]
            amounts = self.router.functions.getAmountsOut(amount_in, path).call()
            token_price_in_eth = amounts[1] / 1e18

            return token_price_in_eth
        except Exception as e:
            logger.error(f"Error getting token price: {e}")
            return None
    
    def buy_token(self, token_address, amount_eth):
        """Buy tokens with ETH."""
        if not self.private_key:
            logger.error("Private key not set, cannot execute transaction")
            return False
            
        try:
            # Convert ETH amount to Wei
            amount_wei = self.w3.to_wei(amount_eth, 'ether')
            
            # Set up transaction parameters
            path = [self.weth_address, token_address]
            deadline = int(self.w3.eth.get_block('latest').timestamp) + 300  # 5 minutes from now
            
            # Estimate minimum tokens received (with 1% slippage)
            amounts = self.router.functions.getAmountsOut(amount_wei, path).call()
            min_tokens = int(amounts[1] * 0.99)  # 1% slippage
            
            # Build transaction
            transaction = self.router.functions.swapExactETHForTokens(
                min_tokens,
                path,
                self.wallet_address,
                deadline
            ).build_transaction({
                'from': self.wallet_address,
                'value': amount_wei,
                'gas': 250000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address)
            })
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"Transaction sent: {tx_hash.hex()}")
            
            # Wait for transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            if receipt.status == 1:
                logger.info("Transaction successful!")
                return True
            else:
                logger.error("Transaction failed!")
                return False
                
        except Exception as e:
            logger.error(f"Error buying token: {e}")
            return False

# Example usage
if __name__ == "__main__":
    uniswap = UniswapInteraction()
    # Example token: DAI
    dai_address = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
    price = uniswap.get_token_price(dai_address)
    if price:
        print(f"1 DAI = {price} ETH")


import logging
import time
import os
import requests
from typing import Tuple, Dict, Any, Optional
from web3 import Web3
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class PaymentHandler:
    """Handles payment verification for Ethereum and Solana networks"""
    
    def __init__(self):
        # Connect to Ethereum network
        self.infura_url = os.getenv("INFURA_URL", "https://mainnet.infura.io/v3/your-infura-key")
        self.w3 = None
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.infura_url))
            if self.w3.is_connected():
                logger.info("Connected to Ethereum network")
            else:
                logger.warning("Failed to connect to Ethereum network")
        except Exception as e:
            logger.error(f"Error connecting to Ethereum network: {e}")
        
        # Solana API endpoints
        self.solana_api = "https://api.mainnet-beta.solana.com"
        self.solscan_api = "https://api.solscan.io/transaction"
        
    def verify_eth_transaction(self, tx_hash: str, expected_amount: float, target_address: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Verify an Ethereum transaction
        
        Args:
            tx_hash: Transaction hash
            expected_amount: Expected amount in ETH
            target_address: Target wallet address
            
        Returns:
            Tuple of (success, message, transaction_data)
        """
        if not self.w3 or not self.w3.is_connected():
            return False, "Ethereum connection not available", None
        
        try:
            # Normalize addresses and hash
            if not tx_hash.startswith("0x"):
                tx_hash = "0x" + tx_hash
                
            target_address = target_address.lower()
            
            # Get transaction details
            tx = self.w3.eth.get_transaction(tx_hash)
            if not tx:
                return False, "Transaction not found", None
                
            # Get transaction receipt to check status
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            if not receipt:
                return False, "Transaction receipt not found", None
                
            # Check if transaction was successful
            if receipt.status != 1:
                return False, "Transaction failed", tx
                
            # Check recipient address
            to_address = tx.get('to', '').lower()
            if to_address != target_address:
                return False, f"Transaction was not sent to the expected address: {to_address} != {target_address}", tx
                
            # Check amount
            amount_wei = tx.get('value', 0)
            amount_eth = self.w3.from_wei(amount_wei, 'ether')
            
            # Allow a small deviation for gas fees (0.5%)
            min_expected = expected_amount * 0.995
            
            if amount_eth < min_expected:
                return False, f"Transaction amount too low: {amount_eth} ETH < {expected_amount} ETH", tx
                
            # Check if transaction is confirmed
            current_block = self.w3.eth.block_number
            conf_blocks = current_block - receipt.blockNumber
            
            if conf_blocks < 1:
                return False, "Transaction not confirmed yet, please wait", tx
                
            return True, "Transaction verified successfully", tx
            
        except Exception as e:
            logger.error(f"Error verifying ETH transaction: {e}")
            return False, f"Error verifying transaction: {str(e)}", None
            
    def verify_solana_transaction(self, tx_hash: str, expected_amount: float, target_address: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Verify a Solana transaction
        
        Args:
            tx_hash: Transaction signature
            expected_amount: Expected amount in SOL
            target_address: Target wallet address
            
        Returns:
            Tuple of (success, message, transaction_data)
        """
        try:
            # Try solscan API first (more reliable)
            params = {"tx": tx_hash}
            response = requests.get(self.solscan_api, params=params)
            
            if response.status_code != 200:
                logger.warning(f"Solscan API error: {response.status_code}")
                # Fallback to RPC API
                return self._verify_solana_tx_rpc(tx_hash, expected_amount, target_address)
                
            tx_data = response.json()
            
            # Check if transaction exists
            if not tx_data or "status" in tx_data and tx_data["status"] == "error":
                return False, "Transaction not found", None
                
            # Check if transaction was successful
            if tx_data.get("status") != "Success":
                return False, f"Transaction failed: {tx_data.get('status', 'Unknown')}", tx_data
                
            # Find the transfer instruction
            sol_transfer = None
            for ix in tx_data.get("parsedInstruction", []):
                if ix.get("type") == "sol-transfer":
                    sol_transfer = ix
                    break
                    
            if not sol_transfer:
                return False, "No SOL transfer found in transaction", tx_data
                
            # Check recipient address
            receiver = sol_transfer.get("params", {}).get("receiver")
            if receiver != target_address:
                return False, f"Transaction was not sent to the expected address: {receiver}", tx_data
                
            # Check amount
            amount_lamports = float(sol_transfer.get("params", {}).get("amount", 0))
            amount_sol = amount_lamports / 1_000_000_000  # Convert lamports to SOL
            
            # Allow a small deviation (0.5%)
            min_expected = expected_amount * 0.995
            
            if amount_sol < min_expected:
                return False, f"Transaction amount too low: {amount_sol} SOL < {expected_amount} SOL", tx_data
                
            return True, "Transaction verified successfully", tx_data
            
        except Exception as e:
            logger.error(f"Error verifying Solana transaction: {e}")
            return False, f"Error verifying transaction: {str(e)}", None
            
    def _verify_solana_tx_rpc(self, tx_hash: str, expected_amount: float, target_address: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Fallback method to verify Solana transaction using RPC API"""
        try:
            # Prepare JSON-RPC request
            headers = {'Content-Type': 'application/json'}
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [
                    tx_hash,
                    {"encoding": "json", "maxSupportedTransactionVersion": 0}
                ]
            }
            
            response = requests.post(self.solana_api, headers=headers, json=payload)
            
            if response.status_code != 200:
                return False, f"Solana RPC API error: {response.status_code}", None
                
            result = response.json()
            
            if "result" not in result or not result["result"]:
                return False, "Transaction not found", None
                
            tx_data = result["result"]
            
            # Check if transaction was successful
            if tx_data.get("meta", {}).get("err") is not None:
                return False, "Transaction failed", tx_data
                
            # Extract pre and post balances to verify transfer
            pre_balances = tx_data.get("meta", {}).get("preBalances", [])
            post_balances = tx_data.get("meta", {}).get("postBalances", [])
            
            if not pre_balances or not post_balances:
                return False, "Transaction data incomplete", tx_data
                
            # Find account index for the target address
            account_index = None
            for i, account in enumerate(tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [])):
                if account == target_address:
                    account_index = i
                    break
                    
            if account_index is None:
                return False, f"Target address {target_address} not found in transaction", tx_data
                
            # Check balance change
            pre_bal = pre_balances[account_index]
            post_bal = post_balances[account_index]
            balance_change_lamports = post_bal - pre_bal
            balance_change_sol = balance_change_lamports / 1_000_000_000
            
            # Allow a small deviation (0.5%)
            min_expected = expected_amount * 0.995
            
            if balance_change_sol < min_expected:
                return False, f"Transaction amount too low: {balance_change_sol} SOL < {expected_amount} SOL", tx_data
                
            return True, "Transaction verified successfully", tx_data
            
        except Exception as e:
            logger.error(f"Error verifying Solana transaction using RPC: {e}")
            return False, f"Error verifying transaction: {str(e)}", None

# Singleton instance
_payment_handler = None

def get_payment_handler():
    """Get or create a PaymentHandler instance"""
    global _payment_handler
    if _payment_handler is None:
        _payment_handler = PaymentHandler()
    return _payment_handler

if __name__ == "__main__":
    # Test the payment handler
    handler = get_payment_handler()
    
    # Example ETH transaction verification
    # eth_result, eth_msg, eth_data = handler.verify_eth_transaction(
    #     "0x123...", 0.05, "0x247cd53A34b1746C11944851247D7Dd802C1d703"
    # )
    # print(f"ETH Verification: {eth_result}, {eth_msg}")
    
    # Example SOL transaction verification
    # sol_result, sol_msg, sol_data = handler.verify_solana_transaction(
    #     "abc123...", 0.5, "DbqdUJmaPgLKkCEhebokxGTuXhzoS7D2SuWxhahi8BYn"
    # )
    # print(f"SOL Verification: {sol_result}, {sol_msg}")

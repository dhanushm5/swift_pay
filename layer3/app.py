import os
import json
import subprocess
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware
import uvicorn
import sys

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="SwiftPay API",
    description="API for interacting with SwiftPay blockchain transactions",
    version="1.0.0",
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Default hardhat node URL
HARDHAT_URL = os.getenv("HARDHAT_URL", "http://localhost:8545")

# Connect to Hardhat node
w3 = Web3(Web3.HTTPProvider(HARDHAT_URL))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)  # For compatibility with Hardhat

# Load contract ABI from artifacts
def load_contract_abi():
    try:
        abi_file_path = "./artifacts/contracts/TransactionBlock.sol/TransactionChain.json"
        with open(abi_file_path, "r") as f:
            contract_json = json.load(f)
            return contract_json["abi"]
    except Exception as e:
        print(f"Error loading contract ABI: {e}")
        return None

CONTRACT_ABI = load_contract_abi()
DEFAULT_CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

# Connection status
@app.get("/api/status")
def get_status():
    """Check connection status to the blockchain."""
    try:
        connected = w3.is_connected()
        chain_id = w3.eth.chain_id
        accounts = w3.eth.accounts
        
        return {
            "connected": connected,
            "chainId": chain_id,
            "network": "hardhat" if chain_id == 31337 else "unknown",
            "accounts": accounts[:5] if len(accounts) > 5 else accounts,  # Only show first 5 accounts
            "contractAddress": DEFAULT_CONTRACT_ADDRESS
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to blockchain: {str(e)}")

# Contract instance getter
def get_contract(contract_address: Optional[str] = None):
    """Get contract instance using the specified address or default."""
    address = contract_address or DEFAULT_CONTRACT_ADDRESS
    
    if not address:
        return None  # Return None to indicate no contract available
        
    if not w3.is_connected():
        raise HTTPException(status_code=503, detail="Not connected to blockchain node")
        
    try:
        if not CONTRACT_ABI:
            raise HTTPException(status_code=500, detail="Contract ABI not available")
            
        contract = w3.eth.contract(address=address, abi=CONTRACT_ABI)
        return contract
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting contract: {str(e)}")

# Helper function for sending transactions in development mode
def send_transaction(transaction):
    """Send a transaction using the first account from Hardhat's provided accounts"""
    if not w3.eth.accounts:
        raise HTTPException(status_code=500, detail="No accounts available")
    
    # In development mode with Hardhat, we can send directly from the unlocked account
    tx_hash = w3.eth.send_transaction(transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt.status == 0:  # Transaction failed
        raise HTTPException(status_code=400, detail="Transaction failed")
        
    return tx_hash, receipt

# Deploy new contract
@app.post("/api/contract/deploy")
async def deploy_contract():
    """Deploy a new TransactionChain contract."""
    try:
        if not w3.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to blockchain node")
            
        result = subprocess.run(
            "npx hardhat run scripts/deploy.ts --network localhost",
            shell=True,
            capture_output=True,
            text=True,
            cwd="./"
        )
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Deployment failed: {result.stderr}")
            
        # Extract contract address from the output
        output = result.stdout
        import re
        match = re.search(r"TransactionChain deployed to: (0x[a-fA-F0-9]{40})", output)
        
        if not match:
            raise HTTPException(status_code=500, detail="Could not extract contract address from deployment output")
            
        contract_address = match.group(1)
        
        # Save to .env file
        with open(".env", "w") as f:
            f.write(f"CONTRACT_ADDRESS={contract_address}\n")
            f.write(f"HARDHAT_URL={HARDHAT_URL}\n")
            
        # Update global variable
        global DEFAULT_CONTRACT_ADDRESS
        DEFAULT_CONTRACT_ADDRESS = contract_address
        
        return {"success": True, "contractAddress": contract_address, "output": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deploying contract: {str(e)}")

# Pydantic models for request validation
class UserCreate(BaseModel):
    username: str = Field(..., description="Username for the new user")

class UserCheck(BaseModel):
    username: str = Field(..., description="Username to check")

class BalanceAdd(BaseModel):
    username: str = Field(..., description="Username to add balance to")
    amount: int = Field(..., description="Amount to add")

class EthDeposit(BaseModel):
    username: str = Field(..., description="Username to deposit to")
    amount: str = Field(..., description="ETH amount to deposit (as a string, e.g. '0.1')")

class BalanceCheck(BaseModel):
    username: str = Field(..., description="Username to check balance for")

class TransactionCreate(BaseModel):
    sender_username: str = Field(..., description="Sender username")
    receiver_username: str = Field(..., description="Receiver username")
    amount: int = Field(..., description="Amount to transfer")

class TransactionLookup(BaseModel):
    transaction_id: int = Field(..., description="Transaction ID to look up")

class UserTransactionsLookup(BaseModel):
    username: str = Field(..., description="Username to look up transactions for")

# User Management endpoints
@app.post("/api/users/create")
async def create_user(user: UserCreate, contract_address: Optional[str] = None):
    """Create a new user with the given username."""
    contract = get_contract(contract_address)
    if not contract:
        raise HTTPException(status_code=404, detail="No contract available. Deploy a contract first.")
        
    try:
        # Check if user already exists
        try:
            exists = contract.functions.validateUserByName(user.username).call()
            if exists:
                return {"success": False, "error": "Username already exists"}
        except Exception:
            pass  # If error occurs, assume user doesn't exist and continue
            
        # Create user transaction
        tx = {
            'from': w3.eth.accounts[0],
            'to': contract.address,
            'nonce': w3.eth.get_transaction_count(w3.eth.accounts[0]),
            'data': contract.encodeABI(fn_name='createUserWithName', args=[user.username])
        }
        
        # Send transaction using our helper
        tx_hash, receipt = send_transaction(tx)
            
        # Get the assigned UUID to show to the user
        user_id = contract.functions.getUserIdByName(user.username).call()
        
        return {
            "success": True,
            "username": user.username,
            "userId": user_id,
            "txHash": tx_hash.hex()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

@app.post("/api/users/check")
async def check_user(user: UserCheck, contract_address: Optional[str] = None):
    """Check if a user exists by username."""
    contract = get_contract(contract_address)
    if not contract:
        raise HTTPException(status_code=404, detail="No contract available. Deploy a contract first.")
        
    try:
        exists = contract.functions.validateUserByName(user.username).call()
        
        result = {"exists": exists}
        
        if exists:
            user_id = contract.functions.getUserIdByName(user.username).call()
            result["userId"] = user_id
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking user: {str(e)}")

# Balance Management endpoints
@app.post("/api/balance/add")
async def add_balance(balance: BalanceAdd, contract_address: Optional[str] = None):
    """Add balance to a user's account."""
    contract = get_contract(contract_address)
    if not contract:
        raise HTTPException(status_code=404, detail="No contract available. Deploy a contract first.")
        
    try:
        # Get user ID from username
        user_id = contract.functions.getUserIdByName(balance.username).call()
        
        # Add balance transaction
        tx = {
            'from': w3.eth.accounts[0],
            'to': contract.address,
            'nonce': w3.eth.get_transaction_count(w3.eth.accounts[0]),
            'data': contract.encodeABI(fn_name='userAdd', args=[user_id, balance.amount])
        }
        
        # Send transaction using our helper
        tx_hash, receipt = send_transaction(tx)
            
        # Get new balance
        new_balance = contract.functions.balances(user_id).call()
        
        return {
            "success": True,
            "username": balance.username,
            "userId": user_id,
            "addedAmount": balance.amount,
            "newBalance": new_balance,
            "txHash": tx_hash.hex()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding balance: {str(e)}")

@app.post("/api/balance/deposit")
async def deposit_eth(deposit: EthDeposit, contract_address: Optional[str] = None):
    """Deposit ETH to a user's account."""
    contract = get_contract(contract_address)
    if not contract:
        raise HTTPException(status_code=404, detail="No contract available. Deploy a contract first.")
        
    try:
        # Get user ID from username
        user_id = contract.functions.getUserIdByName(deposit.username).call()
        
        # Convert ETH to Wei
        amount_wei = w3.to_wei(float(deposit.amount), 'ether')
        
        # Deposit ETH transaction
        tx = {
            'from': w3.eth.accounts[0],
            'to': contract.address,
            'value': amount_wei,
            'nonce': w3.eth.get_transaction_count(w3.eth.accounts[0]),
            'data': contract.encodeABI(fn_name='deposit', args=[user_id])
        }
        
        # Send transaction using our helper
        tx_hash, receipt = send_transaction(tx)
            
        # Get new balance
        new_balance = contract.functions.balances(user_id).call()
        
        return {
            "success": True,
            "username": deposit.username,
            "userId": user_id,
            "deposited": deposit.amount,
            "depositedWei": str(amount_wei),
            "newBalance": new_balance,
            "txHash": tx_hash.hex()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error depositing ETH: {str(e)}")

@app.post("/api/balance/check")
async def check_balance(balance_check: BalanceCheck, contract_address: Optional[str] = None):
    """Check a user's balance."""
    contract = get_contract(contract_address)
    if not contract:
        raise HTTPException(status_code=404, detail="No contract available. Deploy a contract first.")
        
    try:
        # Get user ID from username
        user_id = contract.functions.getUserIdByName(balance_check.username).call()
        
        # Get balance
        balance = contract.functions.balances(user_id).call()
        
        return {
            "username": balance_check.username,
            "userId": user_id,
            "balance": balance
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking balance: {str(e)}")

# Transaction Management endpoints
@app.post("/api/transactions/create")
async def create_transaction(transaction: TransactionCreate, contract_address: Optional[str] = None):
    """Create a new transaction between users."""
    contract = get_contract(contract_address)
    if not contract:
        raise HTTPException(status_code=404, detail="No contract available. Deploy a contract first.")
        
    try:
        # Get user IDs from usernames
        sender_id = contract.functions.getUserIdByName(transaction.sender_username).call()
        receiver_id = contract.functions.getUserIdByName(transaction.receiver_username).call()
        
        # Create transaction
        tx = {
            'from': w3.eth.accounts[0],
            'to': contract.address,
            'nonce': w3.eth.get_transaction_count(w3.eth.accounts[0]),
            'data': contract.encodeABI(fn_name='createTransactionAuto', args=[sender_id, receiver_id, transaction.amount])
        }
        
        # Send transaction using our helper
        tx_hash, receipt = send_transaction(tx)
        
        # Extract transaction ID from event logs
        tx_id = None
        for log in receipt.logs:
            # Try to decode the log
            try:
                event = contract.events.TransactionCreated().process_log(log)
                if event:
                    # The TransactionCreated event has the transaction ID as the 5th parameter
                    tx_id = event['args']['transactionid']
                    break
            except:
                continue
                
        if tx_id is None:
            # If we can't extract from logs, get the last transaction count
            tx_count = contract.functions.getTransactionCount().call()
            if tx_count > 0:
                tx_id = tx_count  # This assumes the transaction ID is sequential
        
        return {
            "success": True,
            "senderId": sender_id,
            "senderUsername": transaction.sender_username,
            "receiverId": receiver_id,
            "receiverUsername": transaction.receiver_username,
            "amount": transaction.amount,
            "transactionId": tx_id,
            "txHash": tx_hash.hex()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating transaction: {str(e)}")

@app.get("/api/transactions/all")
async def get_all_transactions(contract_address: Optional[str] = None):
    """Get all transactions."""
    contract = get_contract(contract_address)
    if not contract:
        raise HTTPException(status_code=404, detail="No contract available. Deploy a contract first.")
        
    try:
        tx_count = contract.functions.getTransactionCount().call()
        
        if tx_count == 0:
            return {"transactions": [], "count": 0}
            
        transactions = []
        
        for i in range(tx_count):
            # Get detailed transaction information
            tx_result = contract.functions.getTransactionDetailsByIndex(i).call()
            found, sender, receiver, amount, timestamp, tx_id, prev_hash = tx_result
            
            if not found:
                continue
                
            # Try to get usernames
            sender_name = sender
            receiver_name = receiver
            
            try:
                sender_name = contract.functions.getUserNameById(sender).call()
                receiver_name = contract.functions.getUserNameById(receiver).call()
            except:
                pass  # If username lookup fails, we'll use the IDs
                
            transactions.append({
                "index": i,
                "id": tx_id,
                "sender": {
                    "id": sender,
                    "username": sender_name
                },
                "receiver": {
                    "id": receiver,
                    "username": receiver_name
                },
                "amount": amount,
                "timestamp": timestamp,
                "datetime": None if timestamp == 0 else str(timestamp),
                "previousHash": prev_hash.hex()
            })
            
        return {"transactions": transactions, "count": tx_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {str(e)}")

@app.post("/api/transactions/by-id")
async def get_transaction_by_id(lookup: TransactionLookup, contract_address: Optional[str] = None):
    """Get transaction details by ID."""
    contract = get_contract(contract_address)
    if not contract:
        raise HTTPException(status_code=404, detail="No contract available. Deploy a contract first.")
        
    try:
        # Get transaction details
        tx_result = contract.functions.getTransaction(lookup.transaction_id).call()
        found, sender, receiver, amount, timestamp = tx_result
        
        if not found:
            raise HTTPException(status_code=404, detail=f"Transaction ID {lookup.transaction_id} not found")
            
        # Try to get usernames
        sender_name = sender
        receiver_name = receiver
        
        try:
            sender_name = contract.functions.getUserNameById(sender).call()
            receiver_name = contract.functions.getUserNameById(receiver).call()
        except:
            pass  # If username lookup fails, we'll use the IDs
            
        return {
            "id": lookup.transaction_id,
            "sender": {
                "id": sender,
                "username": sender_name
            },
            "receiver": {
                "id": receiver,
                "username": receiver_name
            },
            "amount": amount,
            "timestamp": timestamp,
            "datetime": None if timestamp == 0 else str(timestamp)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transaction: {str(e)}")

@app.post("/api/transactions/by-user")
async def get_transactions_by_user(lookup: UserTransactionsLookup, contract_address: Optional[str] = None):
    """Get all transactions for a user."""
    contract = get_contract(contract_address)
    if not contract:
        raise HTTPException(status_code=404, detail="No contract available. Deploy a contract first.")
        
    try:
        # Get user ID from username
        user_id = contract.functions.getUserIdByName(lookup.username).call()
        
        # Check if user exists
        user_exists = contract.functions.validateUser(user_id).call()
        if not user_exists:
            raise HTTPException(status_code=404, detail=f"User {lookup.username} does not exist")
            
        # Get user transactions
        tx_result = contract.functions.getUserTransactions(user_id).call()
        tx_ids, senders, receivers, amounts = tx_result
        
        transactions = []
        
        for i in range(len(tx_ids)):
            # Try to get usernames
            sender_name = senders[i]
            receiver_name = receivers[i]
            
            try:
                sender_name = contract.functions.getUserNameById(senders[i]).call()
                receiver_name = contract.functions.getUserNameById(receivers[i]).call()
            except:
                pass  # If username lookup fails, we'll use the IDs
                
            transactions.append({
                "id": tx_ids[i],
                "sender": {
                    "id": senders[i],
                    "username": sender_name
                },
                "receiver": {
                    "id": receivers[i],
                    "username": receiver_name
                },
                "amount": amounts[i]
            })
            
        return {
            "username": lookup.username,
            "userId": user_id,
            "transactions": transactions,
            "count": len(transactions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user transactions: {str(e)}")

@app.post("/api/transactions/received")
async def get_received_transactions(lookup: UserTransactionsLookup, contract_address: Optional[str] = None):
    """Get transactions received by a user."""
    contract = get_contract(contract_address)
    if not contract:
        raise HTTPException(status_code=404, detail="No contract available. Deploy a contract first.")
        
    try:
        # Get user ID from username
        user_id = contract.functions.getUserIdByName(lookup.username).call()
        
        # Check if user exists
        user_exists = contract.functions.validateUser(user_id).call()
        if not user_exists:
            raise HTTPException(status_code=404, detail=f"User {lookup.username} does not exist")
            
        # Get received transactions
        tx_result = contract.functions.userReceived(user_id).call()
        tx_ids, senders, amounts = tx_result
        
        transactions = []
        
        for i in range(len(tx_ids)):
            # Try to get sender username
            sender_name = senders[i]
            
            try:
                sender_name = contract.functions.getUserNameById(senders[i]).call()
            except:
                pass  # If username lookup fails, we'll use the ID
                
            transactions.append({
                "id": tx_ids[i],
                "sender": {
                    "id": senders[i],
                    "username": sender_name
                },
                "amount": amounts[i]
            })
            
        return {
            "username": lookup.username,
            "userId": user_id,
            "receivedTransactions": transactions,
            "count": len(transactions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching received transactions: {str(e)}")

@app.post("/api/transactions/sent")
async def get_sent_transactions(lookup: UserTransactionsLookup, contract_address: Optional[str] = None):
    """Get transactions sent by a user."""
    contract = get_contract(contract_address)
    if not contract:
        raise HTTPException(status_code=404, detail="No contract available. Deploy a contract first.")
        
    try:
        # Get user ID from username
        user_id = contract.functions.getUserIdByName(lookup.username).call()
        
        # Check if user exists
        user_exists = contract.functions.validateUser(user_id).call()
        if not user_exists:
            raise HTTPException(status_code=404, detail=f"User {lookup.username} does not exist")
            
        # Get sent transactions
        tx_result = contract.functions.userSent(user_id).call()
        tx_ids, receivers, amounts = tx_result
        
        transactions = []
        
        for i in range(len(tx_ids)):
            # Try to get receiver username
            receiver_name = receivers[i]
            
            try:
                receiver_name = contract.functions.getUserNameById(receivers[i]).call()
            except:
                pass  # If username lookup fails, we'll use the ID
                
            transactions.append({
                "id": tx_ids[i],
                "receiver": {
                    "id": receivers[i],
                    "username": receiver_name
                },
                "amount": amounts[i]
            })
            
        return {
            "username": lookup.username,
            "userId": user_id,
            "sentTransactions": transactions,
            "count": len(transactions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sent transactions: {str(e)}")

if __name__ == "__main__":
    # Check if hardhat is running
    # subprocess.run(["python", "debug_hardhat.py"], check=False)
    
    # Run the server
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
import os
import json
import subprocess
import logging
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware
import uvicorn
import sys
import traceback
from passlib.context import CryptContext # Added for password hashing

# --- Password Hashing Setup ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
CREDENTIALS_FILE = "user_credentials.json"
# --- End Password Hashing Setup ---

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="SwiftPay API",
    description="API for interacting with SwiftPay blockchain transactions and user authentication", # Updated description
    version="1.0.0",
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Default hardhat node URL
HARDHAT_URL = os.getenv("HARDHAT_URL", "http://localhost:8545")

# Global variable for blockchain connection
w3 = None
connected = False

# Initialize Web3 connection
def init_web3():
    global w3, connected
    try:
        w3 = Web3(Web3.HTTPProvider(HARDHAT_URL))
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)  # For compatibility with Hardhat
        connected = w3.is_connected()
        if connected:
            logger.info(f"Connected to blockchain at {HARDHAT_URL}")
            return True
        else:
            logger.warning(f"Failed to connect to blockchain at {HARDHAT_URL}")
            return False
    except Exception as e:
        logger.error(f"Error initializing Web3: {e}")
        connected = False
        return False

# Try to connect on startup
init_web3()

# Load contract ABI from artifacts
def load_contract_abi():
    try:
        abi_file_path = "./artifacts/contracts/TransactionBlock.sol/TransactionChain.json"
        if not os.path.exists(abi_file_path):
            logger.error(f"ABI file not found at {abi_file_path}")
            return None
            
        with open(abi_file_path, "r") as f:
            contract_json = json.load(f)
            logger.info("Contract ABI loaded successfully")
            return contract_json["abi"]
    except Exception as e:
        logger.error(f"Error loading contract ABI: {e}")
        return None

CONTRACT_ABI = load_contract_abi()
DEFAULT_CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

# --- User Credential Store (Off-Chain) ---
def load_user_credentials() -> Dict[str, Dict]:
    """Load user credentials from the JSON file."""
    if not os.path.exists(CREDENTIALS_FILE):
        return {}
    try:
        with open(CREDENTIALS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.error(f"Error decoding {CREDENTIALS_FILE}. Starting with empty credentials.")
        return {}
    except Exception as e:
        logger.error(f"Error loading user credentials: {e}")
        return {}

def save_user_credentials(credentials: Dict[str, Dict]):
    """Save user credentials to the JSON file."""
    try:
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump(credentials, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving user credentials: {e}")

user_credentials_db = load_user_credentials()
# --- End User Credential Store ---

# Middleware to log requests and handle exceptions
@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        logger.info(f"Request path: {request.url.path}")
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(e)}"}
        )

# Connection status
@app.get("/api/status")
def get_status():
    """Check connection status to the blockchain."""
    try:
        # Try to reconnect if not connected
        global connected
        if not connected:
            init_web3()
            
        if not w3 or not connected:
            return {
                "connected": False,
                "message": "Not connected to blockchain. Is Hardhat running?",
                "contractAddress": DEFAULT_CONTRACT_ADDRESS,
                "contractLoaded": CONTRACT_ABI is not None
            }
        
        chain_id = w3.eth.chain_id
        accounts = w3.eth.accounts
        
        return {
            "connected": True,
            "chainId": chain_id,
            "network": "hardhat" if chain_id == 31337 else "unknown",
            "accounts": accounts[:5] if len(accounts) > 5 else accounts,  # Only show first 5 accounts
            "contractAddress": DEFAULT_CONTRACT_ADDRESS,
            "contractLoaded": CONTRACT_ABI is not None
        }
    except Exception as e:
        logger.error(f"Error in get_status: {e}")
        raise HTTPException(status_code=500, detail=f"Error connecting to blockchain: {str(e)}")

# Contract instance getter
def get_contract(contract_address: Optional[str] = None):
    """Get contract instance using the specified address or default."""
    global connected
    
    # If not connected, try to reconnect
    if not connected:
        init_web3()
    
    address = contract_address or DEFAULT_CONTRACT_ADDRESS
    
    if not address:
        logger.warning("No contract address provided or found in environment")
        return None  # Return None to indicate no contract available
        
    if not w3 or not connected:
        logger.error("Cannot get contract: not connected to blockchain")
        raise HTTPException(status_code=503, detail="Not connected to blockchain node. Is Hardhat running?")
        
    try:
        if not CONTRACT_ABI:
            logger.error("Cannot get contract: ABI not available")
            raise HTTPException(status_code=500, detail="Contract ABI not available. Is the contract compiled?")
            
        contract = w3.eth.contract(address=address, abi=CONTRACT_ABI)
        return contract
    except Exception as e:
        logger.error(f"Error getting contract: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting contract: {str(e)}")

# Helper function for sending transactions in development mode
def send_transaction(transaction):
    """Send a transaction using the first account from Hardhat's provided accounts"""
    if not w3 or not w3.eth.accounts:
        raise HTTPException(status_code=500, detail="No accounts available. Is Hardhat running?")
    
    try:
        # In development mode with Hardhat, we can send directly from the unlocked account
        tx_hash = w3.eth.send_transaction(transaction)
        logger.info(f"Transaction sent: {tx_hash.hex()}")
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f"Transaction mined: {tx_hash.hex()}, status: {receipt.status}")
        
        if receipt.status == 0:  # Transaction failed
            raise HTTPException(status_code=400, detail="Transaction failed on blockchain")
            
        return tx_hash, receipt
    except Exception as e:
        logger.error(f"Error sending transaction: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending transaction: {str(e)}")

# Deploy new contract
@app.post("/api/contract/deploy")
async def deploy_contract():
    """Deploy a new TransactionChain contract."""
    try:
        if not w3 or not connected:
            if not init_web3():
                raise HTTPException(status_code=503, detail="Not connected to blockchain node. Is Hardhat running?")
            
        logger.info("Running contract deployment script...")
        result = subprocess.run(
            "npx hardhat run scripts/deploy.ts --network localhost",
            shell=True,
            capture_output=True,
            text=True,
            cwd="./"
        )
        
        if result.returncode != 0:
            logger.error(f"Deployment failed: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Deployment failed: {result.stderr}")
            
        # Extract contract address from the output
        output = result.stdout
        import re
        match = re.search(r"TransactionChain deployed to: (0x[a-fA-F0-9]{40})", output)
        
        if not match:
            logger.error("Could not extract contract address from deployment output")
            raise HTTPException(status_code=500, detail="Could not extract contract address from deployment output")
            
        contract_address = match.group(1)
        logger.info(f"Contract deployed at: {contract_address}")
        
        # Save to .env file
        with open(".env", "w") as f:
            f.write(f"CONTRACT_ADDRESS={contract_address}\n")
            f.write(f"HARDHAT_URL={HARDHAT_URL}\n")
            
        # Update global variable
        global DEFAULT_CONTRACT_ADDRESS
        DEFAULT_CONTRACT_ADDRESS = contract_address
        
        return {"success": True, "contractAddress": contract_address, "output": output}
    except Exception as e:
        logger.error(f"Error deploying contract: {e}")
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

# Add models for new auth endpoints
class UserAuth(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

class UserRegister(UserAuth):
    pass # Inherits username and password

# --- New Authentication Endpoints ---

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegister):
    """Register a new user with username and password."""
    username = user_data.username
    password = user_data.password
    
    logger.info(f"Attempting registration for username: {username}")
    
    # 1. Check if username already exists in off-chain store
    if username in user_credentials_db:
        logger.warning(f"Registration failed: Username '{username}' already exists.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
        
    # 2. Hash the password
    hashed_password = pwd_context.hash(password)
    
    # 3. Create user on the blockchain
    contract = get_contract()
    if not contract:
         logger.error("Registration failed: Blockchain contract not available.")
         raise HTTPException(status_code=503, detail="Blockchain service unavailable.")
         
    try:
        logger.info(f"Calling smart contract to create user '{username}' on blockchain.")
        # Use the contract function that takes username
        tx = {
            'from': w3.eth.accounts[0],
            'to': contract.address,
            'gas': 3000000,
            'nonce': w3.eth.get_transaction_count(w3.eth.accounts[0]),
            'data': contract.encodeABI(fn_name='createUserWithName', args=[username])
        }
        tx_hash, receipt = send_transaction(tx)
        
        # Retrieve the generated UUID from the contract
        blockchain_uuid = contract.functions.getUserIdByName(username).call()
        logger.info(f"User '{username}' created on blockchain with UUID: {blockchain_uuid}")
        
    except Exception as e:
        logger.error(f"Blockchain user creation failed for '{username}': {e}")
        # Check if it failed because the username *already* existed on chain (maybe created outside this flow)
        try:
            exists_on_chain = contract.functions.validateUserByName(username).call()
            if exists_on_chain:
                 logger.warning(f"Username '{username}' already exists on blockchain, but not in local DB. Attempting to link.")
                 blockchain_uuid = contract.functions.getUserIdByName(username).call()
            else:
                 raise HTTPException(status_code=500, detail=f"Failed to create user on blockchain: {str(e)}")
        except Exception as inner_e:
             logger.error(f"Failed to check/link existing blockchain user '{username}': {inner_e}")
             raise HTTPException(status_code=500, detail=f"Failed to create or link user on blockchain: {str(inner_e)}")

    # 4. Store user credentials (username, hashed_password, uuid) off-chain
    user_credentials_db[username] = {
        "hashed_password": hashed_password,
        "blockchain_uuid": blockchain_uuid
    }
    save_user_credentials(user_credentials_db)
    logger.info(f"User '{username}' successfully registered and stored locally.")
    
    return {"success": True, "username": username, "userId": blockchain_uuid}

@app.post("/api/auth/login")
async def login_user(user_data: UserAuth):
    """Authenticate a user with username and password."""
    username = user_data.username
    password = user_data.password
    
    logger.info(f"Login attempt for username: {username}")
    
    # 1. Find user in the off-chain store
    user_info = user_credentials_db.get(username)
    if not user_info:
        logger.warning(f"Login failed: Username '{username}' not found.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 2. Verify the password
    hashed_password = user_info.get("hashed_password")
    if not hashed_password or not pwd_context.verify(password, hashed_password):
        logger.warning(f"Login failed: Invalid password for username '{username}'.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 3. Check if user still exists on blockchain (optional but good practice)
    blockchain_uuid = user_info.get("blockchain_uuid")
    if blockchain_uuid:
        try:
            contract = get_contract()
            if contract and not contract.functions.validateUser(blockchain_uuid).call():
                 logger.warning(f"Login failed: User '{username}' (UUID: {blockchain_uuid}) not found on blockchain anymore.")
                 # Decide how to handle this - maybe re-create? For now, deny login.
                 raise HTTPException(status_code=404, detail="User account not found on blockchain.")
        except Exception as e:
            logger.error(f"Error verifying user '{username}' on blockchain during login: {e}")
            # Decide if login should proceed - maybe allow if blockchain is down? For now, deny.
            raise HTTPException(status_code=503, detail="Could not verify user with blockchain.")
            
    logger.info(f"User '{username}' successfully authenticated.")
    
    # Return user info needed for session (e.g., username and blockchain UUID)
    return {
        "success": True,
        "username": username,
        "userId": blockchain_uuid
    }

# --- End New Authentication Endpoints ---

# --- Deprecated/Modified User Management Endpoints ---
# Consider removing or modifying these old endpoints as they are insecure

# @app.post("/api/users/create") - Now handled by /api/auth/register
# async def create_user(user: UserCreate, contract_address: Optional[str] = None): ...

# @app.post("/api/users/check") - Logic is now part of /api/auth/login & /api/auth/register
# async def check_user(user: UserCheck, contract_address: Optional[str] = None): ...

# --- End Deprecated/Modified User Management Endpoints ---

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
    try:
        logger.info(f"Checking balance for user: {balance_check.username}")
        contract = get_contract(contract_address)
        if not contract:
            logger.error("No contract available for balance check")
            return {"error": "No contract available. Deploy a contract first or check if Hardhat is running."}
            
        # Get user ID from username
        try:
            user_id = contract.functions.getUserIdByName(balance_check.username).call()
            logger.info(f"Found user ID {user_id} for '{balance_check.username}'")
        except Exception as e:
            logger.error(f"Error getting user ID: {e}")
            return {"error": f"User '{balance_check.username}' not found"}
        
        # Get balance
        balance = contract.functions.balances(user_id).call()
        logger.info(f"Balance for '{balance_check.username}' (ID {user_id}): {balance}")
        
        return {
            "username": balance_check.username,
            "userId": user_id,
            "balance": balance
        }
    except Exception as e:
        logger.error(f"Error checking balance: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Error checking balance: {str(e)}"}

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
    try:
        logger.info(f"Getting transactions for user: {lookup.username}")
        contract = get_contract(contract_address)
        if not contract:
            logger.error("No contract available for transaction lookup")
            return {"error": "No contract available. Deploy a contract first or check if Hardhat is running."}
            
        # Get user ID from username
        try:
            user_id = contract.functions.getUserIdByName(lookup.username).call()
            logger.info(f"Found user ID {user_id} for '{lookup.username}'")
        except Exception as e:
            logger.error(f"Error getting user ID: {e}")
            return {"error": f"User '{lookup.username}' not found"}
        
        # Check if user exists
        user_exists = contract.functions.validateUser(user_id).call()
        if not user_exists:
            logger.error(f"User {lookup.username} does not exist")
            return {"error": f"User '{lookup.username}' does not exist"}
            
        # Get user transactions
        tx_result = contract.functions.getUserTransactions(user_id).call()
        tx_ids, senders, receivers, amounts = tx_result
        
        transactions = []
        
        for i in range(len(tx_ids)):
            # Try to get usernames
            sender_name = str(senders[i])
            receiver_name = str(receivers[i])
            
            try:
                if senders[i] > 0:
                    sender_name = contract.functions.getUserNameById(senders[i]).call()
                if receivers[i] > 0:
                    receiver_name = contract.functions.getUserNameById(receivers[i]).call()
            except Exception as e:
                logger.warning(f"Error getting username for transaction {tx_ids[i]}: {e}")
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
            
        logger.info(f"Found {len(transactions)} transactions for user '{lookup.username}'")
        return {
            "username": lookup.username,
            "userId": user_id,
            "transactions": transactions,
            "count": len(transactions)
        }
    except Exception as e:
        logger.error(f"Error fetching user transactions: {e}")
        logger.error(traceback.format_exc())
        return {"error": f"Error fetching user transactions: {str(e)}"}

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

# Add a startup event to check blockchain connection
@app.on_event("startup")
async def startup_event():
    logger.info("Starting SwiftPay API...")
    
    # Check if contract ABI is loaded
    if CONTRACT_ABI:
        logger.info("Contract ABI loaded successfully")
    else:
        logger.warning("Contract ABI not loaded. Contract functionality will be unavailable")
        
    # Check contract address
    if DEFAULT_CONTRACT_ADDRESS:
        logger.info(f"Contract address set to: {DEFAULT_CONTRACT_ADDRESS}")
    else:
        logger.warning("Contract address not set. Deploy a contract first")

    # Check blockchain connection
    if init_web3():
        logger.info(f"Connected to blockchain at {HARDHAT_URL}")
        
        # Check if we can get accounts
        try:
            accounts = w3.eth.accounts
            logger.info(f"Found {len(accounts)} accounts")
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
    else:
        logger.warning(f"Failed to connect to blockchain at {HARDHAT_URL}")
        logger.warning("Is Hardhat running? Run 'npx hardhat node' to start it")

if __name__ == "__main__":
    # Run the server
    logger.info(f"User credentials loaded from: {CREDENTIALS_FILE}")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
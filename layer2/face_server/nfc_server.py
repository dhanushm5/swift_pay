import os
import json
import logging
import time
from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('nfc_server.log')
    ]
)
logger = logging.getLogger(__name__)

# Create app
app = FastAPI(
    title="NFC Card Authentication API",
    description="NFC card registration and verification API",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create storage directory if it doesn't exist
STORAGE_DIR = os.path.abspath("nfc_data")
os.makedirs(STORAGE_DIR, exist_ok=True)
DB_PATH = os.path.join(STORAGE_DIR, "nfc_db.json")

class NFCDatabase:
    def __init__(self):
        self.cards = {}  # username -> card data mapping
        self.load_database()

    def load_database(self):
        """Load existing NFC database"""
        if os.path.exists(DB_PATH):
            try:
                with open(DB_PATH, "r") as f:
                    self.cards = json.load(f)
                logger.info(f"Loaded NFC database with {len(self.cards)} cards")
            except Exception as e:
                logger.error(f"Error loading NFC database: {e}")
        else:
            logger.info("Creating new NFC database")
            self.save_database()

    def save_database(self):
        """Save NFC database to storage"""
        try:
            with open(DB_PATH, "w") as f:
                json.dump(self.cards, f, indent=4)
            logger.info(f"Saved NFC database with {len(self.cards)} cards")
        except Exception as e:
            logger.error(f"Error saving NFC database: {e}")

    def register_card(self, username: str, card_id: str) -> bool:
        """Register an NFC card for a user"""
        try:
            # Store card data with timestamp
            self.cards[username] = {
                "card_id": card_id,
                "registered_at": str(time.time())
            }
            self.save_database()
            logger.info(f"Successfully registered NFC card for user '{username}'")
            return True
        except Exception as e:
            logger.error(f"Error registering card for user '{username}': {e}")
            return False

    def verify_card(self, username: str, card_id: str) -> bool:
        """Verify if a card matches the stored card for a username"""
        try:
            if username not in self.cards:
                logger.warning(f"User '{username}' not found in NFC database")
                return False

            stored_card = self.cards[username]["card_id"]
            result = stored_card == card_id

            logger.info(f"NFC card verification for '{username}': result={result}")
            return result
        except Exception as e:
            logger.error(f"Error verifying card for user '{username}': {e}")
            return False

# Initialize NFC database
nfc_db = NFCDatabase()

class CardData(BaseModel):
    username: str
    card_id: str

@app.post("/register")
async def register_card(data: CardData):
    """Register a new NFC card for a user"""
    try:
        logger.info(f"Registering NFC card for user: {data.username}")
        
        success = nfc_db.register_card(data.username, data.card_id)
        
        if not success:
            return {
                "success": False,
                "message": "Failed to register NFC card"
            }
            
        return {
            "success": True,
            "message": f"NFC card registered successfully for user {data.username}"
        }
        
    except Exception as e:
        logger.error(f"Error registering NFC card: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verify")
async def verify_card(data: CardData):
    """Verify a user's NFC card"""
    try:
        logger.info(f"Verifying NFC card for user: {data.username}")
        
        verified = nfc_db.verify_card(data.username, data.card_id)
        
        return {
            "success": True,
            "verified": verified,
            "message": "NFC card verification successful" if verified else "NFC card verification failed"
        }
        
    except Exception as e:
        logger.error(f"Error verifying NFC card: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/authorize-payment")
async def authorize_payment(data: CardData):
    """Authorize a payment using NFC card"""
    try:
        logger.info(f"Authorizing payment for user: {data.username}")
        
        verified = nfc_db.verify_card(data.username, data.card_id)
        
        return {
            "success": True,
            "authorized": verified,
            "message": "Payment authorized via NFC card" if verified else "NFC card verification failed"
        }
        
    except Exception as e:
        logger.error(f"Error authorizing payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting NFC Card Authentication API...")
    uvicorn.run("nfc_server:app", host="0.0.0.0", port=8002, reload=True)
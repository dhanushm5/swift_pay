import os
import json
import base64
import numpy as np
import cv2
import logging
import time
import pickle  # Added pickle import for face embeddings
from io import BytesIO
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
from typing import Optional, Dict, List, Any
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from face_utils import FaceProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('face_server.log')
    ]
)
logger = logging.getLogger(__name__)

# Create app
app = FastAPI(
    title="Enhanced Face Recognition API",
    description="Advanced facial recognition and liveness detection API",
    version="2.0.0",
)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create storage directory if it doesn't exist
STORAGE_DIR = os.path.abspath("face_data")
os.makedirs(STORAGE_DIR, exist_ok=True)
DB_PATH = os.path.join(STORAGE_DIR, "face_db.json")
EMBEDDINGS_DIR = os.path.join(STORAGE_DIR, "embeddings")
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

# Initialize face processor
face_processor = FaceProcessor()

class FaceDB:
    def __init__(self):
        self.users = {}  # username -> face data mapping
        self.load_database()

    def load_database(self):
        """Load existing face database"""
        if os.path.exists(DB_PATH):
            try:
                with open(DB_PATH, "r") as f:
                    self.users = json.load(f)
                logger.info(f"Loaded face database with {len(self.users)} users")
            except Exception as e:
                logger.error(f"Error loading face database: {e}")
        else:
            logger.info("Creating new face database")
            self.save_database()

    def save_database(self):
        """Save face database to storage"""
        try:
            with open(DB_PATH, "w") as f:
                json.dump(self.users, f, indent=4)
            logger.info(f"Saved face database with {len(self.users)} users")
        except Exception as e:
            logger.error(f"Error saving face database: {e}")

    def add_user(self, username: str, face_image: np.ndarray) -> bool:
        """Add or update a user's face data"""
        try:
            # Process face image
            processed_face, is_live = face_processor.detect_face(face_image)
            
            if processed_face is None or not is_live:
                logger.error(f"Failed to process face for user '{username}'")
                return False
                
            # Generate face embedding
            embedding = face_processor.get_face_embedding(processed_face)
            
            if embedding is None:
                logger.error(f"Failed to generate face embedding for user '{username}'")
                return False
                
            # Save processed face image
            face_path = os.path.join(STORAGE_DIR, f"{username}.jpg")
            cv2.imwrite(face_path, cv2.cvtColor(processed_face, cv2.COLOR_RGB2BGR))
            
            # Save face embedding
            embedding_path = os.path.join(EMBEDDINGS_DIR, f"{username}.pkl")
            with open(embedding_path, 'wb') as f:
                pickle.dump(embedding, f)
            
            # Update database
            self.users[username] = {
                "face_path": face_path,
                "embedding_path": embedding_path,
                "registered_at": str(time.time())
            }
            self.save_database()
            
            logger.info(f"Successfully registered face for user '{username}'")
            return True
            
        except Exception as e:
            logger.error(f"Error adding user '{username}' to face database: {e}")
            return False

    def verify_face(self, face_image: np.ndarray, username: str) -> bool:
        """Verify if a face matches the stored face for a username"""
        try:
            if username not in self.users:
                logger.warning(f"User '{username}' not found in face database")
                return False
                
            # Process the input face
            processed_face, is_live = face_processor.detect_face(face_image)
            
            if processed_face is None or not is_live:
                logger.error(f"Failed to process face for verification")
                return False
                
            # Generate embedding for input face
            input_embedding = face_processor.get_face_embedding(processed_face)
            
            if input_embedding is None:
                logger.error("Failed to generate face embedding for input face")
                return False
                
            # Load stored embedding
            with open(self.users[username]["embedding_path"], 'rb') as f:
                stored_embedding = pickle.load(f)
            
            # Compare embeddings
            similarity = face_processor.compare_faces(input_embedding, stored_embedding)
            
            # Define threshold for face matching
            SIMILARITY_THRESHOLD = 0.85
            result = similarity > SIMILARITY_THRESHOLD
            
            logger.info(f"Face verification for '{username}': similarity={similarity:.4f}, result={result}")
            return result
            
        except Exception as e:
            logger.error(f"Error verifying face for user '{username}': {e}")
            return False

# Initialize face database
face_db = FaceDB()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        logger.info(f"Request: {request.method} {request.url.path}")
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Request error: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.get("/")
@limiter.limit("10/minute")
async def root(request: Request):
    """Health check endpoint"""
    return {
        "status": "Enhanced Face Recognition API is running",
        "version": "2.0.0",
        "storagePath": STORAGE_DIR
    }

@app.post("/register")
@limiter.limit("3/minute")
async def register_face(
    request: Request,
    username: str = Form(...),
    file: UploadFile = File(...)
):
    """Register a new user with their face"""
    try:
        logger.info(f"Registering face for user: {username}")
        
        # Read and validate image
        image_data = await file.read()
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image format")
        
        # Process face without registering to check if it would pass
        processed_face, is_live = face_processor.detect_face(image)
        
        if processed_face is None:
            return {
                "success": False,
                "message": "Could not detect a face in the image. Please ensure your face is clearly visible.",
                "error_code": "NO_FACE_DETECTED"
            }
            
        if not is_live:
            return {
                "success": False,
                "message": "Liveness check failed. Please ensure good lighting, look directly at the camera, and try again.",
                "error_code": "LIVENESS_CHECK_FAILED",
                "advice": "Make sure you have good lighting, are looking directly at the camera, and your whole face is visible."
            }
            
        # If we get here, face detection and liveness check passed, now register
        success = face_db.add_user(username, image)
        
        if not success:
            return {
                "success": False,
                "message": "Face detected but registration failed. Please try again."
            }
            
        return {
            "success": True,
            "message": f"Face registered successfully for user {username}"
        }
        
    except Exception as e:
        logger.error(f"Error registering face: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verify")
@limiter.limit("10/minute")
async def verify_face(
    request: Request,
    username: str = Form(...),
    file: UploadFile = File(...)
):
    """Verify a user's face"""
    try:
        logger.info(f"Verifying face for user: {username}")
        
        # Read and validate image
        image_data = await file.read()
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image format")
            
        # Verify face
        verified = face_db.verify_face(image, username)
        
        return {
            "success": True,
            "verified": verified,
            "message": "Face verification successful" if verified else "Face verification failed"
        }
        
    except Exception as e:
        logger.error(f"Error verifying face: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/authorize-payment")
@limiter.limit("5/minute")
async def authorize_payment(
    request: Request,
    username: str = Form(...),
    file: UploadFile = File(...)
):
    """Authorize a payment using facial recognition"""
    try:
        logger.info(f"Authorizing payment for user: {username}")
        
        # Read and validate image
        image_data = await file.read()
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image format")
            
        # Verify face with stricter checks for payment
        verified = face_db.verify_face(image, username)
        
        return {
            "success": True,
            "authorized": verified,
            "message": "Payment authorized via facial recognition" if verified else "Face verification failed"
        }
        
    except Exception as e:
        logger.error(f"Error authorizing payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import time
    
    logger.info("Starting Enhanced Face Recognition API...")
    logger.info(f"Storage directory: {STORAGE_DIR}")
    logger.info(f"Database path: {DB_PATH}")
    logger.info(f"Embeddings directory: {EMBEDDINGS_DIR}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
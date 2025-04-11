import os
import json
import base64
import numpy as np
import cv2
import logging
from io import BytesIO
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
from typing import Optional, Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create app
app = FastAPI(
    title="Face Recognition API",
    description="Simple API for facial recognition and payment authorization",
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
STORAGE_DIR = os.path.abspath("face_data")
os.makedirs(STORAGE_DIR, exist_ok=True)
DB_PATH = os.path.join(STORAGE_DIR, "face_db.json")

# Load OpenCV face detector
try:
    cascPath = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    if not os.path.exists(cascPath):
        logger.error(f"Cascade file not found at {cascPath}")
        # Try to find it in a different location
        alt_path = os.path.join(os.path.dirname(cv2.__file__), 'data', 'haarcascade_frontalface_default.xml')
        if os.path.exists(alt_path):
            cascPath = alt_path
            logger.info(f"Found cascade file at alternative path: {alt_path}")
        else:
            logger.error("Could not find haarcascade_frontalface_default.xml file")
    
    face_cascade = cv2.CascadeClassifier(cascPath)
    logger.info(f"Loaded face cascade classifier from {cascPath}")
    
    if face_cascade.empty():
        logger.error("Failed to load face cascade classifier - the classifier is empty")
except Exception as e:
    logger.error(f"Error loading face cascade: {e}")
    face_cascade = None

# Check which OpenCV version is installed
logger.info(f"OpenCV version: {cv2.__version__}")

class FaceDB:
    def __init__(self):
        self.users = {}  # username -> face image filename mapping
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
            logger.info(f"No face database found at {DB_PATH}, creating new database")
            # Create empty file
            self.save_database()

    def save_database(self):
        """Save face database to storage"""
        try:
            with open(DB_PATH, "w") as f:
                json.dump(self.users, f)
            logger.info(f"Saved face database with {len(self.users)} users to {DB_PATH}")
        except Exception as e:
            logger.error(f"Error saving face database: {e}")

    def add_user(self, username: str, face_image: np.ndarray):
        """Add or update a user's face image"""
        try:
            # Save the face image to disk
            user_face_path = os.path.join(STORAGE_DIR, f"{username}.jpg")
            logger.info(f"Saving face image for user '{username}' to {user_face_path}")
            
            if face_image is None or face_image.size == 0:
                logger.error(f"Invalid face image for user '{username}': Image is empty")
                raise ValueError("Invalid face image: Image is empty")
                
            # Ensure the image is in RGB format
            if len(face_image.shape) < 3:
                logger.warning(f"Converting grayscale face image to RGB for user '{username}'")
                face_image = cv2.cvtColor(face_image, cv2.COLOR_GRAY2BGR)
                
            success = cv2.imwrite(user_face_path, face_image)
            
            if not success:
                logger.error(f"Failed to save face image for user '{username}'")
                raise IOError(f"Failed to save face image to {user_face_path}")
                
            # Verify the file was created
            if not os.path.exists(user_face_path):
                logger.error(f"Face image file for user '{username}' not found after saving")
                raise IOError(f"Face image file not found after saving: {user_face_path}")
                
            logger.info(f"Successfully saved face image for user '{username}'")
            
            # Store the path in the database
            self.users[username] = user_face_path
            self.save_database()
            return user_face_path
        except Exception as e:
            logger.error(f"Error adding user '{username}' to face database: {e}")
            raise

    def verify_face(self, face_image: np.ndarray, username: str) -> bool:
        """Verify if a face matches the stored face for a username"""
        try:
            if username not in self.users:
                logger.warning(f"User '{username}' not found in face database")
                return False
            
            # Load the stored face image
            stored_image_path = self.users[username]
            if not os.path.exists(stored_image_path):
                logger.error(f"Stored face image for user '{username}' not found at {stored_image_path}")
                return False
            
            logger.info(f"Loading stored face image for user '{username}' from {stored_image_path}")
            stored_face = cv2.imread(stored_image_path)
            
            if stored_face is None:
                logger.error(f"Failed to load stored face image for user '{username}'")
                return False
                
            # Convert to grayscale for better comparison
            stored_face_gray = cv2.cvtColor(stored_face, cv2.COLOR_BGR2GRAY)
            
            # Convert input face to grayscale for comparison
            if len(face_image.shape) > 2:
                face_image_gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
            else:
                face_image_gray = face_image
                
            # Resize for comparison (both images must be the same size)
            face_image_gray = cv2.resize(face_image_gray, (stored_face_gray.shape[1], stored_face_gray.shape[0]))
            
            # Use template matching for basic comparison
            # (You might want to use a more sophisticated method in a production environment)
            score = cv2.matchTemplate(face_image_gray, stored_face_gray, cv2.TM_CCOEFF_NORMED)[0][0]
            logger.info(f"Face match score for '{username}': {score:.4f}")
            
            # Lower threshold to increase match probability
            threshold = 0.75 # Adjust based on testing
            result = score > threshold
            logger.info(f"Face verification result for '{username}': {result} (threshold: {threshold})")
            
            # Convert numpy.bool_ to Python bool to avoid serialization issues
            return bool(result)
        except Exception as e:
            logger.error(f"Error verifying face for user '{username}': {e}")
            return False

# Initialize face database
face_db = FaceDB()

def detect_face(image_data: bytes) -> np.ndarray:
    """Detect a face in an image and return the face region"""
    try:
        if face_cascade is None or face_cascade.empty():
            logger.error("Face cascade classifier not properly loaded")
            raise HTTPException(status_code=500, detail="Face detection system not properly initialized")
        
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            logger.error("Failed to decode image")
            raise HTTPException(status_code=400, detail="Invalid image format")
            
        logger.info(f"Processing image with shape: {img.shape}")
        
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Use multiple scale factors for better detection
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        if len(faces) == 0:
            # Try again with more lenient parameters
            logger.warning("No faces detected with default parameters, trying with more lenient parameters")
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=3,
                minSize=(20, 20),
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
        if len(faces) == 0:
            logger.error("No face detected in the image")
            # Return the whole image as a fallback
            logger.warning("Using the whole image as fallback")
            face_img = img
            return face_img
            # Uncomment below if you want to enforce face detection
            # raise HTTPException(status_code=400, detail="No face detected in the image")
        
        # Get the largest face in the image
        largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
        x, y, w, h = largest_face
        
        logger.info(f"Detected face at: x={x}, y={y}, width={w}, height={h}")
        
        # Add a bit of margin
        margin = int(0.2 * w)  # 20% margin
        x = max(0, x - margin)
        y = max(0, y - margin)
        w = min(img.shape[1] - x, w + 2 * margin)
        h = min(img.shape[0] - y, h + 2 * margin)
        
        # Extract face region
        face_img = img[y:y+h, x:x+w]
        logger.info(f"Extracted face with shape: {face_img.shape}")
        
        return face_img
    except Exception as e:
        logger.error(f"Error detecting face: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

# Middleware for request logging
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
async def root():
    """Health check endpoint"""
    return {"status": "Face recognition API is running", "storagePath": STORAGE_DIR}

@app.post("/register")
async def register_face(username: str = Form(...), file: UploadFile = File(...)):
    """Register a new user with their face"""
    try:
        logger.info(f"Registering face for user: {username}")
        logger.info(f"Received file: {file.filename}, content_type: {file.content_type}")
        
        image_data = await file.read()
        logger.info(f"Read {len(image_data)} bytes from uploaded file")
        
        face_img = detect_face(image_data)
        
        if face_img is None:
            logger.error(f"Failed to detect face for user '{username}'")
            return {"success": False, "message": "Failed to detect face in image"}
        
        # Add to database
        image_path = face_db.add_user(username, face_img)
        
        return {
            "success": True, 
            "message": f"Face registered for user {username}",
            "imagePath": image_path
        }
    except Exception as e:
        logger.error(f"Error registering face for user '{username}': {e}")
        return {"success": False, "message": str(e)}

@app.post("/verify")
async def verify_face(username: str = Form(...), file: UploadFile = File(...)):
    """Verify a user's face matches their stored face"""
    try:
        logger.info(f"Verifying face for user: {username}")
        logger.info(f"Received file: {file.filename}, content_type: {file.content_type}")
        
        image_data = await file.read()
        logger.info(f"Read {len(image_data)} bytes from uploaded file")
        
        face_img = detect_face(image_data)
        
        if face_img is None:
            logger.error(f"Failed to detect face for user '{username}'")
            return {"success": False, "verified": False, "message": "Failed to detect face in image"}
        
        # Verify against stored face
        verified = face_db.verify_face(face_img, username)
        
        return {
            "success": True,
            "verified": verified,
            "message": "Face verification successful" if verified else "Face verification failed"
        }
    except Exception as e:
        logger.error(f"Error verifying face for user '{username}': {e}")
        return {"success": False, "verified": False, "message": str(e)}

@app.post("/authorize-payment")
async def authorize_payment(username: str = Form(...), file: UploadFile = File(...)):
    """Authorize a payment using facial recognition"""
    try:
        logger.info(f"Authorizing payment for user: {username}")
        logger.info(f"Received file: {file.filename}, content_type: {file.content_type}")
        
        image_data = await file.read()
        logger.info(f"Read {len(image_data)} bytes from uploaded file")
        
        face_img = detect_face(image_data)
        
        if face_img is None:
            logger.error(f"Failed to detect face for payment authorization for user '{username}'")
            return {
                "success": False, 
                "authorized": False,
                "message": "Failed to detect face in image"
            }
        
        # Verify against stored face
        authorized = face_db.verify_face(face_img, username)
        
        return {
            "success": True,
            "authorized": authorized,
            "message": "Payment authorized via facial recognition" if authorized else "Face verification failed"
        }
    except Exception as e:
        logger.error(f"Error authorizing payment via face recognition for user '{username}': {e}")
        return {"success": False, "authorized": False, "message": str(e)}

@app.get("/users")
async def list_users():
    """List all users in the face database"""
    try:
        return {"users": list(face_db.users.keys()), "count": len(face_db.users)}
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return {"success": False, "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Face Recognition API on port 8001...")
    logger.info(f"Face database path: {DB_PATH}")
    logger.info(f"Storage directory: {STORAGE_DIR}")
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
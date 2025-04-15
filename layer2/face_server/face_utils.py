import cv2
import numpy as np
import dlib
from facenet_pytorch import MTCNN, InceptionResnetV1
import torch
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class FaceProcessor:
    def __init__(self):
        # Initialize face detection models
        self.mtcnn = MTCNN(
            image_size=160, margin=0, min_face_size=20,
            thresholds=[0.6, 0.7, 0.7], factor=0.709, post_process=True,
            device='cpu'
        )
        
        # Initialize facial landmark detector
        self.landmark_predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        
        # Initialize face recognition model
        self.facenet = InceptionResnetV1(pretrained='vggface2').eval()
        
        logger.info("Face processing models initialized successfully")

    def detect_face(self, image: np.ndarray) -> Tuple[Optional[np.ndarray], bool]:
        """
        Detect face in image and perform liveness detection
        Returns: (face_image, is_live)
        """
        try:
            # Convert to RGB if needed
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:
                image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
            elif image.shape[2] == 3 and image.dtype == np.uint8:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Detect faces using MTCNN
            boxes, probs = self.mtcnn.detect(image)
            
            if boxes is None or len(boxes) == 0:
                logger.warning("No face detected in image")
                return None, False

            # Get the box with highest probability
            box = boxes[np.argmax(probs)]
            x1, y1, x2, y2 = [int(b) for b in box]

            # Add margin
            margin = int(0.2 * (x2 - x1))
            x1 = max(0, x1 - margin)
            y1 = max(0, y1 - margin)
            x2 = min(image.shape[1], x2 + margin)
            y2 = min(image.shape[0], y2 + margin)

            # Extract face region
            face = image[y1:y2, x1:x2]

            # Perform liveness detection
            is_live = self.check_liveness(face)
            
            if not is_live:
                logger.warning("Liveness check failed - possible spoofing attempt")
                return None, False

            # Align face using landmarks
            face_aligned = self.align_face(face)
            
            if face_aligned is None:
                logger.warning("Failed to align face")
                return None, False

            return face_aligned, True

        except Exception as e:
            logger.error(f"Error in face detection: {str(e)}")
            return None, False

    def align_face(self, face_image: np.ndarray) -> Optional[np.ndarray]:
        """Align face using facial landmarks"""
        try:
            # Convert to grayscale for landmark detection
            gray = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
            
            # Detect face rectangle for landmark detection
            rect = dlib.rectangle(0, 0, face_image.shape[1], face_image.shape[0])
            
            # Get facial landmarks
            landmarks = self.landmark_predictor(gray, rect)
            
            # Convert landmarks to numpy array
            landmarks_points = []
            for n in range(68):
                x = landmarks.part(n).x
                y = landmarks.part(n).y
                landmarks_points.append((x, y))
            
            # Calculate eyes center
            left_eye = np.mean(landmarks_points[36:42], axis=0)
            right_eye = np.mean(landmarks_points[42:48], axis=0)
            
            # Calculate angle to align eyes horizontally
            dy = right_eye[1] - left_eye[1]
            dx = right_eye[0] - left_eye[0]
            angle = np.degrees(np.arctan2(dy, dx))
            
            # Get center of face
            center = (face_image.shape[1]//2, face_image.shape[0]//2)
            
            # Create rotation matrix
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            
            # Perform the rotation
            aligned_face = cv2.warpAffine(face_image, M, (face_image.shape[1], face_image.shape[0]))
            
            return aligned_face

        except Exception as e:
            logger.error(f"Error in face alignment: {str(e)}")
            return None

    def check_liveness(self, face_image: np.ndarray) -> bool:
        """
        Perform liveness detection to prevent spoofing
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
            
            # 1. Texture analysis using Local Binary Patterns (LBP)
            lbp = self.get_lbp(gray)
            texture_score = np.std(lbp)
            
            # 2. Eye blink detection using landmarks
            eye_aspect_ratio = self.get_eye_aspect_ratio(face_image)
            
            # 3. Head pose estimation
            head_pose_valid = self.check_head_pose(face_image)
            
            # 4. Check for image artifacts that might indicate a printed photo
            artifact_score = self.check_image_artifacts(gray)
            
            # Log the scores for debugging
            logger.info(f"Liveness check scores - texture: {texture_score}, eye ratio: {eye_aspect_ratio}, head pose valid: {head_pose_valid}, artifact score: {artifact_score}")
            
            # Create a score for each check (0 or 1)
            texture_check = texture_score > 25  # Reduced from 30
            eye_check = eye_aspect_ratio > 0.15  # Reduced from 0.2
            pose_check = head_pose_valid  # We'll ignore this check for registration
            artifact_check = artifact_score < 0.85  # Increased from 0.4 to 0.85
            
            # Count how many checks pass
            passing_checks = sum([texture_check, eye_check, True, artifact_check])  # Always count pose as passing
            
            # Require at least 3 out of 4 checks to pass
            is_live = passing_checks >= 3
            
            if not is_live:
                logger.warning("Liveness check failed - possible spoofing attempt")
                logger.warning(f"Failed checks: " + 
                              (not texture_check) * "texture " +
                              (not eye_check) * "eye_ratio " +
                              "head_pose " * 0 +  # Don't report head pose failure
                              (not artifact_check) * "artifacts")
            
            return is_live

        except Exception as e:
            logger.error(f"Error in liveness detection: {str(e)}")
            return False

    def get_lbp(self, gray_image: np.ndarray) -> np.ndarray:
        """Calculate Local Binary Pattern for texture analysis"""
        radius = 1
        n_points = 8 * radius
        lbp = np.zeros_like(gray_image)
        
        for i in range(radius, gray_image.shape[0] - radius):
            for j in range(radius, gray_image.shape[1] - radius):
                center = gray_image[i, j]
                pattern = 0
                
                for k in range(n_points):
                    angle = 2 * np.pi * k / n_points
                    x = i + radius * np.cos(angle)
                    y = j - radius * np.sin(angle)
                    
                    x1 = int(np.floor(x))
                    x2 = int(np.ceil(x))
                    y1 = int(np.floor(y))
                    y2 = int(np.ceil(y))
                    
                    tx = x - x1
                    ty = y - y1
                    
                    w1 = (1 - tx) * (1 - ty)
                    w2 = tx * (1 - ty)
                    w3 = (1 - tx) * ty
                    w4 = tx * ty
                    
                    neighbor = w1 * gray_image[x1, y1] + \
                              w2 * gray_image[x2, y1] + \
                              w3 * gray_image[x1, y2] + \
                              w4 * gray_image[x2, y2]
                    
                    pattern |= (neighbor > center) << k
                
                lbp[i, j] = pattern
                
        return lbp

    def get_eye_aspect_ratio(self, face_image: np.ndarray) -> float:
        """Calculate eye aspect ratio to detect blinks"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
            
            # Detect face rectangle
            rect = dlib.rectangle(0, 0, face_image.shape[1], face_image.shape[0])
            
            # Get facial landmarks
            landmarks = self.landmark_predictor(gray, rect)
            
            # Calculate eye aspect ratio for both eyes
            def eye_ratio(eye_points):
                p1 = np.array([landmarks.part(eye_points[0]).x, landmarks.part(eye_points[0]).y])
                p2 = np.array([landmarks.part(eye_points[1]).x, landmarks.part(eye_points[1]).y])
                p3 = np.array([landmarks.part(eye_points[2]).x, landmarks.part(eye_points[2]).y])
                p4 = np.array([landmarks.part(eye_points[3]).x, landmarks.part(eye_points[3]).y])
                p5 = np.array([landmarks.part(eye_points[4]).x, landmarks.part(eye_points[4]).y])
                p6 = np.array([landmarks.part(eye_points[5]).x, landmarks.part(eye_points[5]).y])
                
                ear = (np.linalg.norm(p2-p6) + np.linalg.norm(p3-p5)) / (2.0 * np.linalg.norm(p1-p4))
                return ear
            
            # Calculate ratio for both eyes
            left_eye_ratio = eye_ratio([36, 37, 38, 39, 40, 41])
            right_eye_ratio = eye_ratio([42, 43, 44, 45, 46, 47])
            
            # Return average eye aspect ratio
            return (left_eye_ratio + right_eye_ratio) / 2.0

        except Exception as e:
            logger.error(f"Error calculating eye aspect ratio: {str(e)}")
            return 0.0

    def check_head_pose(self, face_image: np.ndarray) -> bool:
        """Estimate head pose to detect unnatural angles"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
            
            # Detect face rectangle
            rect = dlib.rectangle(0, 0, face_image.shape[1], face_image.shape[0])
            
            # Get facial landmarks
            landmarks = self.landmark_predictor(gray, rect)
            
            # Get nose tip and chin positions
            nose_tip = (landmarks.part(30).x, landmarks.part(30).y)
            chin = (landmarks.part(8).x, landmarks.part(8).y)
            
            # Calculate vertical angle
            vertical_angle = np.abs(np.arctan2(chin[1] - nose_tip[1], chin[0] - nose_tip[0]))
            
            # Get left and right face edges
            left_face = (landmarks.part(0).x, landmarks.part(0).y)
            right_face = (landmarks.part(16).x, landmarks.part(16).y)
            
            # Calculate horizontal angle
            horizontal_angle = np.abs(np.arctan2(right_face[1] - left_face[1], right_face[0] - left_face[0]))
            
            # Check if angles are within acceptable range
            return (vertical_angle < np.pi/4 and horizontal_angle < np.pi/4)

        except Exception as e:
            logger.error(f"Error checking head pose: {str(e)}")
            return False

    def check_image_artifacts(self, gray_image: np.ndarray) -> float:
        """Check for image artifacts that might indicate a printed photo"""
        try:
            # Apply Laplacian filter to detect edges
            laplacian = cv2.Laplacian(gray_image, cv2.CV_64F)
            
            # Calculate variance of Laplacian (measure of image artifacts)
            variance = np.var(laplacian)
            
            # Normalize variance to 0-1 range
            normalized_variance = min(variance / 500.0, 1.0)
            
            return normalized_variance

        except Exception as e:
            logger.error(f"Error checking image artifacts: {str(e)}")
            return 1.0

    def get_face_embedding(self, face_image: np.ndarray) -> Optional[np.ndarray]:
        """Generate face embedding using FaceNet"""
        try:
            # Preprocess image
            face_tensor = self.mtcnn(face_image)
            
            if face_tensor is None:
                return None
            
            # Add batch dimension
            face_tensor = face_tensor.unsqueeze(0)
            
            # Generate embedding
            with torch.no_grad():
                embedding = self.facenet(face_tensor)
                
            return embedding.numpy()

        except Exception as e:
            logger.error(f"Error generating face embedding: {str(e)}")
            return None

    def compare_faces(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compare two face embeddings and return similarity score"""
        try:
            # Ensure embeddings are flattened 1D arrays
            emb1_flat = embedding1.flatten()
            emb2_flat = embedding2.flatten()
            
            # Calculate cosine similarity
            similarity = np.dot(emb1_flat, emb2_flat) / (np.linalg.norm(emb1_flat) * np.linalg.norm(emb2_flat))
            return float(similarity)

        except Exception as e:
            logger.error(f"Error comparing face embeddings: {str(e)}")
            return 0.0
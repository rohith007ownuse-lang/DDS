"""
face_detection.py
Face detection and landmarking using MediaPipe FaceLandmarker.
Downloads model automatically if needed.
"""

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from src.utils import COL_CYAN
import os
import urllib.request

# Model path - relative to project root
MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MODEL_PATH = os.path.join(MODEL_DIR, 'face_landmarker.task')
MODEL_URL = 'https://storage.googleapis.com/mediapipe-models/face_landmarker/float16/1/face_landmarker.task'

# Flag to track if we've already attempted download
_MODEL_DOWNLOAD_ATTEMPTED = False

def _ensure_model_exists():
    """Download the model file if it doesn't exist."""
    global _MODEL_DOWNLOAD_ATTEMPTED
    
    # Avoid repeated download attempts
    if _MODEL_DOWNLOAD_ATTEMPTED:
        return
        
    if not os.path.exists(MODEL_PATH):
        print(f'[face_detection] Downloading face landmarker model to {MODEL_PATH}...')
        try:
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            print('[face_detection] Download completed.')
        except Exception as e:
            print(f'[face_detection] Failed to download model: {e}')
            raise
    _MODEL_DOWNLOAD_ATTEMPTED = True

# Ensure model exists before initializing
_ensure_model_exists()

# Initialize FaceLandmarker
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=False,
    output_facial_transformation_matrixes=False,
    num_faces=1
)

try:
    detector = vision.FaceLandmarker.create_from_options(options)
except Exception as e:
    print(f'[face_detection] Failed to initialize FaceLandmarker: {e}')
    raise

# Drawing utilities: we'll implement our own draw_landmarks using connections.
from mediapipe.tasks.python.vision import FaceLandmarksConnections
import cv2
import numpy as np


def _draw_face_landmarks(image, face_landmarks, connections=None,
                         landmark_drawing_spec=None,
                         connection_drawing_spec=None):
    """Draws the face landmarks and connections on the image.
    Args:
        image: A numpy array representing the image (BGR).
        face_landmarks: A list of detected landmarks (NormalizedLandmark).
        connections: A list of landmark index tuples that specifies how landmarks
            are connected in the drawing.
        landmark_drawing_spec: Either a DrawingSpec object or a list of
            DrawingSpec objects specifying the landmark drawing parameters.
        connection_drawing_spec: Either a DrawingSpec object or a list of
            DrawingSpec objects specifying the connection drawing parameters.
    """
    if not face_landmarks:
        return
    image_rows, image_cols, _ = image.shape
    idx_to_coordinates = {}
    for idx, landmark in enumerate(face_landmarks):
        visibility = getattr(landmark, 'visibility', 1.0)
        if visibility is None:
            visibility = 1.0
        presence = getattr(landmark, 'presence', 1.0)
        if presence is None:
            presence = 1.0
        if visibility < 0.5 or presence < 0.5:
            continue
        landmark_px = _normalized_to_pixel_coordinates(
            landmark.x, landmark.y, image_cols, image_rows)
        if landmark_px:
            idx_to_coordinates[idx] = landmark_px

    if connections:
        if isinstance(connections, (list, tuple)):
            # Draw the connections.
            for connection in connections:
                # Handle both tuple/list and Connection objects
                if hasattr(connection, 'start') and hasattr(connection, 'end'):
                    start_idx = connection.start
                    end_idx = connection.end
                else:
                    # Assume it's a subscriptable sequence like tuple/list
                    start_idx = connection[0]
                    end_idx = connection[1]
                if start_idx in idx_to_coordinates and end_idx in idx_to_coordinates:
                    cv2.line(image, idx_to_coordinates[start_idx],
                             idx_to_coordinates[end_idx],
                             (0, 255, 0), 1)  # green color, thickness 1

    # Draw landmarks after connections for better visual appearance.
    for idx, landmark_px in idx_to_coordinates.items():
        cv2.circle(image, landmark_px, 1, (0, 255, 0), -1)  # small green dot


def _normalized_to_pixel_coordinates(normalized_x, normalized_y, image_width, image_height):
    """Converts normalized value pair to pixel coordinates."""
    # Checks if the float value is between 0 and 1.
    def _is_valid_normalized_value(value):
        return (value >= 0.0 and value <= 1.0)

    if not (_is_valid_normalized_value(normalized_x) and
            _is_valid_normalized_value(normalized_y)):
        return None
    x_px = min(int(normalized_x * image_width), image_width - 1)
    y_px = min(int(normalized_y * image_height), image_height - 1)
    return x_px, y_px


class FaceLandmarkerResult:
    """Adapter to mimic the old MediaPipe results structure."""
    def __init__(self, mp_result):
        # mp_result.face_landmarks is a list of list of NormalizedLandmark
        # We'll convert to a list of list of objects with x, y, z attributes.
        # For simplicity, we keep the NormalizedLandmark objects as they have x, y, z.
        self.multi_face_landmarks = mp_result.face_landmarks if mp_result.face_landmarks else []


class FaceMesh:
    """Mimics the old MediaPipe solution face_mesh object."""
    def process(self, rgb_frame):
        """Processes an RGB frame and returns the face landmarker result."""
        # Convert numpy image to mediapipe Image.
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        # Detect face landmarks.
        result = detector.detect(mp_image)
        # Adapt to the expected structure.
        return FaceLandmarkerResult(result)


# Create an instance that mimics the old face_mesh
face_mesh = FaceMesh()

# For backward compatibility with existing code expecting detect_face function
detect_face = face_mesh.process


def draw_face_mesh(frame, face_landmarks):
    """Draws face mesh connections on the given BGR frame.
    Args:
        frame: BGR image numpy array.
        face_landmarks: list of NormalizedLandmark for one face.
    """
    if not face_landmarks:
        return frame
    # Draw the face mesh contours.
    _draw_face_landmarks(
        frame,
        face_landmarks,
        connections=FaceLandmarksConnections.FACE_LANDMARKS_CONTOURS,
        landmark_drawing_spec=None,
        connection_drawing_spec=None)
    return frame

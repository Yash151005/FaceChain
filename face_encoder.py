"""
face_encoder.py — Face Detection & SHA-256 Fingerprinting

Detects faces in an image using the `face_recognition` library (dlib-backed),
extracts a 128-dimension embedding vector for the primary face, and produces
a deterministic SHA-256 hash that serves as a unique biometric fingerprint.
"""

import hashlib
import json
from pathlib import Path

import face_recognition
import numpy as np


class NoFaceDetectedError(Exception):
    """Raised when no face can be found in the supplied image."""
    pass


def detect_and_encode(image_path: str) -> dict:
    """
    Detect the primary face in *image_path* and return its encoding + SHA-256 hash.

    Parameters
    ----------
    image_path : str
        Absolute or relative path to a JPEG/PNG image file.

    Returns
    -------
    dict
        {
            "face_hash":     str,          # SHA-256 hex digest
            "encoding":      list[float],  # 128-dim face vector
            "face_count":    int,          # total faces detected
            "face_location": tuple,        # (top, right, bottom, left) of primary face
        }

    Raises
    ------
    FileNotFoundError
        If *image_path* does not exist.
    NoFaceDetectedError
        If no faces are detected in the image.
    """
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Load image into a numpy array (RGB)
    image = face_recognition.load_image_file(str(path))

    # Detect face bounding boxes  (model="hog" is fast; use "cnn" for GPU)
    face_locations = face_recognition.face_locations(image, model="hog")

    if not face_locations:
        raise NoFaceDetectedError(
            "No face detected in the image. Please use a clear, front-facing photo."
        )

    # Compute 128-dim encodings for every detected face
    encodings = face_recognition.face_encodings(image, known_face_locations=face_locations)

    # Select the largest face (by bounding-box area) as the primary face
    def _box_area(loc):
        top, right, bottom, left = loc
        return (bottom - top) * (right - left)

    primary_idx = max(range(len(face_locations)), key=lambda i: _box_area(face_locations[i]))
    primary_encoding = encodings[primary_idx]
    primary_location = face_locations[primary_idx]

    # Deterministic SHA-256 hash of the encoding vector
    # Round to 8 decimal places for consistency across platforms
    rounded = [round(float(v), 8) for v in primary_encoding]
    encoding_json = json.dumps(rounded, separators=(",", ":"))
    face_hash = hashlib.sha256(encoding_json.encode("utf-8")).hexdigest()

    return {
        "face_hash": face_hash,
        "encoding": rounded,
        "face_count": len(face_locations),
        "face_location": primary_location,
    }

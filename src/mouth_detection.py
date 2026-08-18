"""
mouth_detection.py
Everything about measuring mouth openness.
"""

from src.utils import distance

UPPER_LIP = 13
LOWER_LIP = 14
LEFT_MOUTH = 61
RIGHT_MOUTH = 291


def calculate_mar(landmarks):
    upper = landmarks[UPPER_LIP]
    lower = landmarks[LOWER_LIP]
    left = landmarks[LEFT_MOUTH]
    right = landmarks[RIGHT_MOUTH]

    vertical = distance(upper, lower)
    horizontal = distance(left, right)

    return vertical / horizontal

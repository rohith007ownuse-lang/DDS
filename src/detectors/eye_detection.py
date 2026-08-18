"""
eye_detection.py
Everything about measuring eye openness.
"""

from src.utils import distance

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]


def calculate_ear(landmarks, eye):
    p1 = landmarks[eye[0]]
    p2 = landmarks[eye[1]]
    p3 = landmarks[eye[2]]
    p4 = landmarks[eye[3]]
    p5 = landmarks[eye[4]]
    p6 = landmarks[eye[5]]

    vertical1 = distance(p2, p6)
    vertical2 = distance(p3, p5)
    horizontal = distance(p1, p4)

    return (vertical1 + vertical2) / (2 * horizontal)


def calculate_avg_ear(landmarks):
    left = calculate_ear(landmarks, LEFT_EYE)
    right = calculate_ear(landmarks, RIGHT_EYE)
    return (left + right) / 2

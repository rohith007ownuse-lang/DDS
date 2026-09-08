"""
head_pose.py
Head pose estimation (solvePnP) and a configurable-direction pose tracker.
"""

import time
import cv2
import numpy as np

NOSE_TIP = 1
CHIN = 152
LEFT_EYE_CORNER = 33
RIGHT_EYE_CORNER = 263
LEFT_MOUTH_CORNER = 61
RIGHT_MOUTH_CORNER = 291

MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),
    (0.0, -330.0, -65.0),
    (-225.0, 170.0, -135.0),
    (225.0, 170.0, -135.0),
    (-150.0, -150.0, -125.0),
    (150.0, -150.0, -125.0),
], dtype="double")


def get_head_pose(landmarks, frame_w, frame_h):
    image_points = np.array([
        (landmarks[NOSE_TIP].x * frame_w, landmarks[NOSE_TIP].y * frame_h),
        (landmarks[CHIN].x * frame_w, landmarks[CHIN].y * frame_h),
        (landmarks[LEFT_EYE_CORNER].x * frame_w, landmarks[LEFT_EYE_CORNER].y * frame_h),
        (landmarks[RIGHT_EYE_CORNER].x * frame_w, landmarks[RIGHT_EYE_CORNER].y * frame_h),
        (landmarks[LEFT_MOUTH_CORNER].x * frame_w, landmarks[LEFT_MOUTH_CORNER].y * frame_h),
        (landmarks[RIGHT_MOUTH_CORNER].x * frame_w, landmarks[RIGHT_MOUTH_CORNER].y * frame_h),
    ], dtype="double")

    focal_length = frame_w
    center = (frame_w / 2, frame_h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype="double")
    dist_coeffs = np.zeros((4, 1))

    success, rotation_vector, translation_vector = cv2.solvePnP(
        MODEL_POINTS, image_points, camera_matrix, dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE
    )
    if not success:
        return None

    rmat, _ = cv2.Rodrigues(rotation_vector)
    pose_mat = cv2.hconcat((rmat, translation_vector))
    _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(pose_mat)
    pitch, yaw, roll = euler_angles.flatten()

    if pitch > 90:
        pitch -= 180
    elif pitch < -90:
        pitch += 180

    return pitch, yaw, roll


class HeadPoseTracker:
    DOWN_SIGN = -1  # flip to +1 if testing shows the opposite on your camera

    def __init__(self, baseline_pitch=0.0, deviation_threshold=12.0, duration_threshold=1.0,
                 direction="both"):
        self.baseline_pitch = baseline_pitch
        self.deviation_threshold = deviation_threshold
        self.duration_threshold = duration_threshold
        self.direction = direction
        self._start = None

    def update(self, pitch):
        raw_delta = pitch - self.baseline_pitch

        if self.direction == "both":
            deviation = abs(raw_delta)
        elif self.direction == "down":
            deviation = max(0.0, raw_delta * self.DOWN_SIGN)
        elif self.direction == "up":
            deviation = max(0.0, -raw_delta * self.DOWN_SIGN)
        else:
            raise ValueError(f"Unknown direction '{self.direction}'")

        if deviation > self.deviation_threshold:
            if self._start is None:
                self._start = time.time()
            duration = time.time() - self._start
            return duration, duration >= self.duration_threshold, deviation

        self._start = None
        return 0.0, False, deviation

    def reset(self):
       self._start = None

HeadNodTracker = HeadPoseTracker

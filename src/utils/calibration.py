"""
calibration.py
Runs the 5s baseline calibration in a plain cv2 window (before the
Tkinter dashboard starts) - reused as-is since it already works well
and re-implementing it in Tkinter isn't worth the effort for a one-time
5-second startup step.
"""

import time
import cv2
import numpy as np

from src.utils import (
    CANVAS_W, CANVAS_H, COL_BG, COL_PANEL, COL_PANEL_EDGE,
    COL_TEXT, COL_SUBTEXT, COL_CYAN, COL_GREEN, COL_AMBER,
    rounded_rect, put_text, draw_corner_brackets
)
from src.eye_detection import LEFT_EYE, RIGHT_EYE, calculate_avg_ear
from src.mouth_detection import calculate_mar
from src.head_pose import get_head_pose

CALIBRATION_DURATION = 5.0
MIN_CALIBRATION_SAMPLES = 15
EAR_CALIB_FACTOR = 0.75
MAR_CALIB_MARGIN = 0.20
EAR_THRESHOLD_MIN, EAR_THRESHOLD_MAX = 0.15, 0.30
MAR_THRESHOLD_MIN, MAR_THRESHOLD_MAX = 0.40, 0.90


def build_calibration_screen(cam_frame, remaining, duration, samples_collected, face_found):
    canvas = np.full((CANVAS_H, CANVAS_W, 3), COL_BG, dtype=np.uint8)
    cv2.rectangle(canvas, (0, 0), (CANVAS_W, 50), (18, 14, 10), -1)
    cv2.line(canvas, (0, 50), (CANVAS_W, 50), COL_PANEL_EDGE, 1)
    put_text(canvas, "CALIBRATING PERSONAL BASELINE", (30, 33), 0.75, COL_CYAN, 2)

    cam_x, cam_y = 30, 80
    cam_w, cam_h = 780, 640
    disp = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
    disp = cv2.resize(disp, (cam_w, cam_h))
    canvas[cam_y:cam_y + cam_h, cam_x:cam_x + cam_w] = disp
    border_color = COL_GREEN if face_found else COL_AMBER
    draw_corner_brackets(canvas, (cam_x, cam_y), (cam_x + cam_w, cam_y + cam_h), border_color, length=34, thickness=3)

    side_x = cam_x + cam_w + 30
    side_w = CANVAS_W - side_x - 30
    y = 80

    card_h = 170
    rounded_rect(canvas, (side_x, y), (side_x + side_w, y + card_h), COL_PANEL, radius=14)
    put_text(canvas, "TIME REMAINING", (side_x + 25, y + 32), 0.5, COL_SUBTEXT, 1)
    put_text(canvas, f"{max(0.0, remaining):.1f}s", (side_x + 25, y + 110), 1.6, COL_CYAN, 3)
    y += card_h + 20

    prog_h = 100
    rounded_rect(canvas, (side_x, y), (side_x + side_w, y + prog_h), COL_PANEL, radius=14)
    put_text(canvas, "PROGRESS", (side_x + 25, y + 30), 0.45, COL_SUBTEXT, 1)
    bar_x, bar_y = side_x + 25, y + 48
    bar_w, bar_h = side_w - 50, 20
    rounded_rect(canvas, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (35, 30, 22), radius=8)
    progress = max(0.0, min(1.0, 1.0 - (remaining / duration)))
    fill_w = int(bar_w * progress)
    if fill_w > 4:
        rounded_rect(canvas, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), COL_CYAN, radius=8)
    y += prog_h + 20

    instr_h = 180
    rounded_rect(canvas, (side_x, y), (side_x + side_w, y + instr_h), COL_PANEL, radius=14)
    put_text(canvas, "INSTRUCTIONS", (side_x + 25, y + 30), 0.5, COL_SUBTEXT, 1)
    put_text(canvas, "Sit naturally, look at the camera", (side_x + 25, y + 65), 0.48, COL_TEXT, 1)
    put_text(canvas, "Keep eyes open normally", (side_x + 25, y + 95), 0.48, COL_TEXT, 1)
    put_text(canvas, "Relax your mouth", (side_x + 25, y + 125), 0.48, COL_TEXT, 1)
    face_msg = "Face detected" if face_found else "No face - move into frame"
    face_color = COL_GREEN if face_found else COL_AMBER
    put_text(canvas, face_msg, (side_x + 25, y + 158), 0.48, face_color, 1)

    put_text(canvas, f"Samples: {samples_collected}", (side_x, CANVAS_H - 20), 0.45, COL_SUBTEXT, 1)
    return canvas


def run_calibration(cap, face_mesh, window_name="Calibration", duration=CALIBRATION_DURATION):
    ear_samples, mar_samples, pitch_samples = [], [], []
    start = time.time()

    while True:
        remaining = duration - (time.time() - start)
        if remaining <= 0:
            break
        success, frame = cap.read()
        if not success:
            continue

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        face_found = False

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0]  # Already a list of landmarks
            h, w, _ = frame.shape
            for idx in LEFT_EYE + RIGHT_EYE:
                point = landmarks[idx]
                x, y_px = int(point.x * w), int(point.y * h)
                cv2.circle(frame, (x, y_px), 2, (0, 255, 0), -1)

            ear = calculate_avg_ear(landmarks)
            mar = calculate_mar(landmarks)
            ear_samples.append(ear)
            mar_samples.append(mar)

            pose = get_head_pose(landmarks, w, h)
            if pose is not None:
                pitch_samples.append(pose[0])
            face_found = True

        screen = build_calibration_screen(frame, remaining, duration, len(ear_samples), face_found)
        cv2.imshow(window_name, screen)
        key = cv2.waitKey(1)
        if key == ord("q"):
            return None, None, None

    if len(ear_samples) < MIN_CALIBRATION_SAMPLES:
        return None, None, None

    baseline_ear = float(np.median(ear_samples))
    baseline_mar = float(np.median(mar_samples))
    baseline_pitch = float(np.median(pitch_samples)) if pitch_samples else 0.0

    ear_threshold = max(EAR_THRESHOLD_MIN, min(baseline_ear * EAR_CALIB_FACTOR, EAR_THRESHOLD_MAX))
    mar_threshold = max(MAR_THRESHOLD_MIN, min(baseline_mar + MAR_CALIB_MARGIN, MAR_THRESHOLD_MAX))

    return ear_threshold, mar_threshold, baseline_pitch
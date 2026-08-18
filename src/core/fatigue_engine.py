"""
fatigue_engine.py
The only module that reads eye + mouth + head-pose signals together
and decides an overall drowsiness status.
"""

import time
from collections import deque

from src.eye_detection import calculate_avg_ear
from src.mouth_detection import calculate_mar
from src.head_pose import get_head_pose, HeadPoseTracker
from src.severity import severity_for


class FatigueEngine:
    def __init__(self, ear_threshold, mar_threshold, baseline_pitch,
                 eye_closed_duration=1.3, yawn_duration=1.5,
                 head_pitch_drop=12.0, head_nod_duration=1.0,
                 head_pose_alert_deviation=15.0, head_pose_alert_duration=2.5,
                 perclos_window=60.0, perclos_threshold=0.15, perclos_min_samples=30):

        self.EAR_THRESHOLD = ear_threshold
        self.MAR_THRESHOLD = mar_threshold
        self.eye_closed_duration = eye_closed_duration
        self.yawn_duration = yawn_duration

        self.nod_tracker = HeadPoseTracker(
            baseline_pitch=baseline_pitch,
            deviation_threshold=head_pitch_drop,
            duration_threshold=head_nod_duration,
            direction="down"
        )
        self.pose_alert_tracker = HeadPoseTracker(
            baseline_pitch=baseline_pitch,
            deviation_threshold=head_pose_alert_deviation,
            duration_threshold=head_pose_alert_duration,
            direction="both"
        )

        self.eye_closed_start = None
        self.last_eye_closed_duration = 0.0
        self.mouth_open_start = None
        self.yawn_detected = False
        self.yawn_counter = 0

        self.perclos_window = perclos_window
        self.perclos_threshold = perclos_threshold
        self.perclos_min_samples = perclos_min_samples
        self.perclos_history = deque()

        self.drowsy_active = False
        self.drowsy_episode_start = None
        self.total_drowsy_episodes = 0
        self.total_drowsy_time = 0.0
        self.max_closed_time = 0.0
        self.ear_sum = 0.0
        self.ear_count = 0

        self.last_ear = 0.0
        self.last_mar = 0.0
        self.last_pitch = baseline_pitch
        self.last_perclos = 0.0

    def process_frame(self, landmarks, frame_w, frame_h):
        now = time.time()

        ear = calculate_avg_ear(landmarks)
        mar = calculate_mar(landmarks)

        self.ear_sum += ear
        self.ear_count += 1

        pose = get_head_pose(landmarks, frame_w, frame_h)
        pitch = pose[0] if pose is not None else self.nod_tracker.baseline_pitch
        nod_duration, head_nod_detected, nod_deviation = self.nod_tracker.update(pitch)
        pose_alert_duration, head_pose_alert, pose_deviation = self.pose_alert_tracker.update(pitch)

        yawn_event = False
        if mar > self.MAR_THRESHOLD:
            if self.mouth_open_start is None:
                self.mouth_open_start = now
            mouth_duration = now - self.mouth_open_start
            if mouth_duration >= self.yawn_duration and not self.yawn_detected:
                self.yawn_counter += 1
                self.yawn_detected = True
                yawn_event = True
        else:
            self.mouth_open_start = None
            self.yawn_detected = False

        is_closed = ear < self.EAR_THRESHOLD
        eye_closed_event = False
        eye_reopened_event = False

        if is_closed:
            if self.eye_closed_start is None:
                self.eye_closed_start = now
                eye_closed_event = True
            closed_time = now - self.eye_closed_start
            self.last_eye_closed_duration = closed_time
            self.max_closed_time = max(self.max_closed_time, closed_time)
        else:
            if self.eye_closed_start is not None:
                eye_reopened_event = True
            self.eye_closed_start = None
            closed_time = 0.0

        self.perclos_history.append((now, is_closed))
        while self.perclos_history and now - self.perclos_history[0][0] > self.perclos_window:
            self.perclos_history.popleft()

        if len(self.perclos_history) >= self.perclos_min_samples:
            closed_count = sum(1 for _, c in self.perclos_history if c)
            perclos = closed_count / len(self.perclos_history)
        else:
            perclos = 0.0

        self.last_ear = ear
        self.last_mar = mar
        self.last_pitch = pitch
        self.last_perclos = perclos

        drowsy_start_event = False
        drowsy_end_event = False
        DROWSY_STATUSES = ("DROWSINESS DETECTED", "DROWSINESS DETECTED (PERCLOS)")

        if closed_time >= self.eye_closed_duration:
            status = "DROWSINESS DETECTED"
            if not self.drowsy_active:
                self.drowsy_active = True
                self.drowsy_episode_start = now
                self.total_drowsy_episodes += 1
                drowsy_start_event = True
        elif perclos >= self.perclos_threshold:
            status = "DROWSINESS DETECTED (PERCLOS)"
            if not self.drowsy_active:
                self.drowsy_active = True
                self.drowsy_episode_start = now
                self.total_drowsy_episodes += 1
                drowsy_start_event = True
        elif head_pose_alert:
            status = "HEAD POSE ALERT"
        elif head_nod_detected:
            status = "HEAD NOD DETECTED"
        elif is_closed:
            status = "EYES CLOSED"
        else:
            status = "NORMAL"

        if status not in DROWSY_STATUSES and self.drowsy_active:
            drowsy_duration = now - self.drowsy_episode_start
            self.total_drowsy_time += drowsy_duration
            self.drowsy_active = False
            drowsy_end_event = True

        closed_ratio = min(1.0, closed_time / self.eye_closed_duration) if self.eye_closed_duration else 0.0
        perclos_ratio = min(1.0, perclos / self.perclos_threshold) if self.perclos_threshold else 0.0
        drowsy_percent = round(100 * max(closed_ratio, perclos_ratio))

        return {
            "ear": ear, "mar": mar, "pitch": pitch,
            "closed_time": closed_time, "perclos": perclos,
            "nod_duration": nod_duration, "nod_deviation": nod_deviation,
            "pose_alert_duration": pose_alert_duration, "pose_deviation": pose_deviation,
            "status": status, "severity": severity_for(status),
            "drowsy_percent": drowsy_percent,
            "yawn_counter": self.yawn_counter, "yawn_event": yawn_event,
            "eye_closed_event": eye_closed_event, "eye_reopened_event": eye_reopened_event,
            "eye_reopened_duration": self.last_eye_closed_duration,
            "drowsy_start_event": drowsy_start_event, "drowsy_end_event": drowsy_end_event,
        }

    def handle_face_lost(self):
        drowsy_end_event = False
        eye_reopened_event = self.eye_closed_start is not None

        if self.drowsy_active:
            drowsy_duration = time.time() - self.drowsy_episode_start
            self.total_drowsy_time += drowsy_duration
            self.drowsy_active = False
            drowsy_end_event = True

        self.eye_closed_start = None
        self.mouth_open_start = None

        return {
            "ear": self.last_ear, "mar": self.last_mar, "pitch": self.last_pitch,
            "closed_time": 0.0, "perclos": self.last_perclos,
            "nod_duration": 0.0, "nod_deviation": 0.0,
            "pose_alert_duration": 0.0, "pose_deviation": 0.0,
            "status": "NO FACE", "severity": severity_for("NO FACE"),
            "drowsy_percent": 0,
            "yawn_counter": self.yawn_counter, "yawn_event": False,
            "eye_closed_event": False, "eye_reopened_event": eye_reopened_event,
            "eye_reopened_duration": self.last_eye_closed_duration,
            "drowsy_start_event": False, "drowsy_end_event": drowsy_end_event,
        }

    def summary(self, session_duration):
        avg_ear = (self.ear_sum / self.ear_count) if self.ear_count > 0 else 0.0
        return {
            "duration_seconds": session_duration,
            "yawns": self.yawn_counter,
            "drowsy_episodes": self.total_drowsy_episodes,
            "drowsy_time_seconds": self.total_drowsy_time,
            "max_closed_time": self.max_closed_time,
            "avg_ear": avg_ear,
        }

"""
fatigue_engine.py
The only module that reads eye + mouth + head-pose signals together
and decides an overall drowsiness status.

Also owns the HARDWARE control layer (as a thin communication/control
layer around the existing detection logic). TWO independent safety
triggers exist, and both lead to PROGRESSIVE (gradual) braking via the
Arduino's L298N PWM control rather than an instant motor cut:

  - NORMAL            : face present + eyes open -> vehicle operates normally
  - DROWSINESS_WARNING: eyes continuously closed, timer running, below stop
                        threshold (default 8s). Short blinks reset the timer.
  - EYE-CLOSURE STOP  : eyes continuously closed >= emergency_stop_threshold
                        -> sends "G" (gradual brake) and LATCHES the stop.
  - FACE-LOSS STOP    : face missing for >= face_loss_stop_threshold (default
                        2s) -> sends "G" (gradual brake) and LATCHES the stop.
                        Brief <2s detection glitches do NOT trigger braking.

Once either trigger latches, the vehicle stays stopped even if the driver
reopens their eyes or the face returns. Only clear_emergency_stop() (manual
RESET "R") releases the stop so the vehicle can operate again.

Architecture:
  Camera -> Python/OpenCV/MediaPipe -> Decision -> Serial/Bluetooth
           -> Arduino UNO -> L298N PWM -> 4 DC motors
"""

import time
from collections import deque

from src.detectors.eye_detection import calculate_avg_ear
from src.detectors.mouth_detection import calculate_mar
from src.detectors.head_pose import get_head_pose, HeadPoseTracker
from src.core.severity import severity_for
from src.utils.config_manager import get_config
from src.hardware.serial_communicator import get_serial_communicator


class FatigueEngine:
    def __init__(self, ear_threshold, mar_threshold, baseline_pitch,
                 eye_closed_duration=None, yawn_duration=None,
                 head_pitch_drop=None, head_nod_duration=None,
                 head_pose_alert_deviation=None, head_pose_alert_duration=None,
                 perclos_window=None, perclos_threshold=None, perclos_min_samples=None,
                 emergency_stop_threshold=None, face_loss_stop_threshold=None):

        # Load facial/detection settings from config (editable in
        # config/system_config.json under "detection"). Constructor args
        # (e.g. calibrated EAR/MAR from main.py) override the config.
        self.config = get_config()

        if ear_threshold is None:
            ear_threshold = self.config.get('detection.ear_threshold', 0.23)
        if mar_threshold is None:
            mar_threshold = self.config.get('detection.mar_threshold', 0.40)
        if eye_closed_duration is None:
            eye_closed_duration = self.config.get('detection.eye_closed_duration', 1.3)
        if yawn_duration is None:
            yawn_duration = self.config.get('detection.yawn_duration', 1.0)
        if head_pitch_drop is None:
            head_pitch_drop = self.config.get('detection.head_pitch_threshold', 15.0)
        if head_nod_duration is None:
            head_nod_duration = self.config.get('detection.head_pose_duration', 1.3)
        if head_pose_alert_deviation is None:
            head_pose_alert_deviation = self.config.get('detection.head_pose_alert_deviation', 15.0)
        if head_pose_alert_duration is None:
            head_pose_alert_duration = self.config.get('detection.head_pose_alert_duration', 2.5)
        if perclos_window is None:
            perclos_window = self.config.get('detection.perclos_window', 60.0)
        if perclos_threshold is None:
            perclos_threshold = self.config.get('detection.perclos_threshold', 0.15)
        if perclos_min_samples is None:
            perclos_min_samples = self.config.get('detection.perclos_min_samples', 30)

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

        # ---- Hardware control layer (thin layer around detection) ----
        self.hardware_enabled = self.config.get('hardware.enabled', False)

        # Emergency stop threshold: continuous eye closure required for STOP.
        # Default 8.0s; overridable via config or constructor arg.
        if emergency_stop_threshold is None:
            emergency_stop_threshold = self.config.get(
                'hardware.emergency_stop_threshold', 8.0)
        self.emergency_stop_threshold = float(emergency_stop_threshold)

        # Face-loss safety threshold: continuous time the face may be missing
        # before the safety brake sequence starts (default 2.0s).
        if face_loss_stop_threshold is None:
            face_loss_stop_threshold = self.config.get(
                'hardware.face_loss_stop_threshold', 2.0)
        self.face_loss_stop_threshold = float(face_loss_stop_threshold)

        # Latched emergency stop: set True once a trigger fires, cleared only
        # by an explicit manual reset. This enforces the "no auto-resume" rule.
        self.emergency_stop_latched = False
        self.emergency_stop_active = False
        self.emergency_stop_time = 0.0
        self.total_emergency_stops = 0

        # Which trigger caused the current (latched) stop:
        # "eye_closure" or "face_loss". None while normal.
        self.stop_reason = None

        # True after a gradual-brake command ("G") has been sent and until reset.
        self.braking_active = False

        # Face-loss timing (continuous, resets when face is detected again).
        self.face_lost_start = None
        self.face_lost_time = 0.0
        self.total_face_loss_stops = 0

        self.serial_comm = get_serial_communicator() if self.hardware_enabled else None
        self.last_command_sent = None
        self.command_cooldown = 0.1
        self.last_command_time = 0

        if self.serial_comm:
            self.serial_comm.set_callbacks(
                on_connect=self._on_hardware_connected,
                on_command_sent=self._on_command_sent
            )
            self.serial_comm.start()

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

        # ---- Status determination (unchanged detection logic) ----
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

        # ---- Hardware safety state machine ----
        # Face is present in this frame, so the face-loss timer resets.
        self.face_lost_start = None
        self.face_lost_time = 0.0

        # Progressive-braking safety trigger 1: EYE-CLOSURE.
        # Eyes continuously closed >= emergency_stop_threshold ->
        # send "G" (gradual brake). The Arduino ramps ENA/ENB PWM down.
        hw_state = "NORMAL"
        stop_triggered_event = False
        stop_released_event = False

        if not self.emergency_stop_latched:
            # Not yet latched - evaluate whether eyes have been closed long enough.
            if closed_time >= self.emergency_stop_threshold:
                # LATCH the stop state and begin GRADUAL braking on hardware.
                self.emergency_stop_latched = True
                self.emergency_stop_active = True
                self.emergency_stop_time = now
                self.total_emergency_stops += 1
                self.stop_reason = "eye_closure"
                self.braking_active = True
                stop_triggered_event = True
                self._send_hardware_command("G")  # G = GRADUAL BRAKE
                hw_state = "EMERGENCY_STOP"
            elif is_closed and closed_time > 0:
                # Eyes closed, timer running but not at the threshold yet.
                hw_state = "DROWSINESS_WARNING"
            else:
                hw_state = "NORMAL"
        else:
            # Latched: vehicle stays stopped until manual reset (no auto-resume).
            if self.emergency_stop_active:
                # Remain in the stopped/latched state (do not auto-resume).
                self.emergency_stop_active = False  # latch held, not per-frame active
            hw_state = "EMERGENCY_STOP"

        # ---- Compute drowsiness percent for the dashboard (unchanged) ----
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
            # Hardware control state
            "hardware_state": hw_state,
            "emergency_stop_latched": self.emergency_stop_latched,
            "stop_reason": self.stop_reason,
            "braking_active": self.braking_active,
            "face_lost_time": self.face_lost_time,
            "face_loss_stop_latched": self.emergency_stop_latched and self.stop_reason == "face_loss",
            "stop_triggered_event": stop_triggered_event,
            "stop_released_event": stop_released_event,
            "total_emergency_stops": self.total_emergency_stops,
            "total_face_loss_stops": self.total_face_loss_stops,
        }

    def handle_face_lost(self):
        drowsy_end_event = False
        eye_reopened_event = self.eye_closed_start is not None
        now = time.time()

        if self.drowsy_active:
            drowsy_duration = now - self.drowsy_episode_start
            self.total_drowsy_time += drowsy_duration
            self.drowsy_active = False
            drowsy_end_event = True

        self.eye_closed_start = None
        self.mouth_open_start = None

        # ---- Face-loss safety timing ----
        # Continuous time the face has been missing. A brief <2s glitch
        # does not stop the vehicle; the timer simply continues and only
        # triggers the safety brake once it crosses the threshold.
        if self.face_lost_start is None:
            self.face_lost_start = now
        self.face_lost_time = now - self.face_lost_start

        # ---- Progressive-braking safety trigger 2: FACE-LOSS ----
        # Face missing for >= face_loss_stop_threshold -> send "G" (gradual
        # brake) and LATCH the stop. Face returning does NOT auto-resume.
        stop_triggered_event = False
        hw_state = "EMERGENCY_STOP" if self.emergency_stop_latched else "NORMAL"

        if not self.emergency_stop_latched and \
                self.face_lost_time >= self.face_loss_stop_threshold:
            self.emergency_stop_latched = True
            self.emergency_stop_active = True
            self.emergency_stop_time = now
            self.total_emergency_stops += 1
            self.total_face_loss_stops += 1
            self.stop_reason = "face_loss"
            self.braking_active = True
            stop_triggered_event = True
            self._send_hardware_command("G")  # G = GRADUAL BRAKE
            hw_state = "EMERGENCY_STOP"

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
            "hardware_state": hw_state,
            "emergency_stop_latched": self.emergency_stop_latched,
            "stop_reason": self.stop_reason,
            "braking_active": self.braking_active,
            "face_lost_time": self.face_lost_time,
            "face_loss_stop_latched": self.emergency_stop_latched and self.stop_reason == "face_loss",
            "stop_triggered_event": stop_triggered_event,
            "stop_released_event": False,
            "total_emergency_stops": self.total_emergency_stops,
            "total_face_loss_stops": self.total_face_loss_stops,
        }

    def clear_emergency_stop(self):
        """
        Manually clear the latched emergency stop state and send RESET ("R")
        to the Arduino so the vehicle can operate again.

        "R" is always sent when hardware is enabled (not only when this engine
        thinks it is latched) because the Arduino may have latched via a manual
        STOP or an earlier brake even if this engine's latch flag was cleared.
        Sending a redundant "R" is harmless on the Arduino side.
        """
        was_latched = self.emergency_stop_latched
        self.emergency_stop_latched = False
        self.emergency_stop_active = False
        self.braking_active = False
        self.stop_reason = None
        if self.hardware_enabled:
            self._send_hardware_command("R")  # R = RESET (unlatch on Arduino side)
        return was_latched

    def reset(self):
        self.eye_closed_start = None
        self.last_eye_closed_duration = 0.0
        self.mouth_open_start = None
        self.face_lost_start = None
        self.face_lost_time = 0.0
        self.yawn_detected = False
        self.yawn_counter = 0
        self.perclos_history.clear()
        self.drowsy_active = False
        self.drowsy_episode_start = None
        self.total_drowsy_episodes = 0
        self.total_drowsy_time = 0.0
        self.max_closed_time = 0.0
        self.ear_sum = 0.0
        self.ear_count = 0
        self.last_ear = 0.0
        self.last_mar = 0.0
        self.last_perclos = 0.0
        self.nod_tracker.reset()
        self.pose_alert_tracker.reset()
        self.clear_emergency_stop()

    def summary(self, session_duration):
        avg_ear = (self.ear_sum / self.ear_count) if self.ear_count > 0 else 0.0
        return {
            "duration_seconds": session_duration,
            "yawns": self.yawn_counter,
            "drowsy_episodes": self.total_drowsy_episodes,
            "drowsy_time_seconds": self.total_drowsy_time,
            "max_closed_time": self.max_closed_time,
            "emergency_stops": self.total_emergency_stops,
            "face_loss_stops": self.total_face_loss_stops,
            "avg_ear": avg_ear,
        }

    def _on_hardware_connected(self, connected: bool):
        status = "CONNECTED" if connected else "DISCONNECTED"
        print(f"[FatigueEngine] Hardware {status}")

    def _on_command_sent(self, command: str):
        print(f"[FatigueEngine] Command sent to hardware: {command}")

    def _send_hardware_command(self, command: str):
        if not self.hardware_enabled or not self.serial_comm:
            return
        now = time.time()
        if now - self.last_command_time < self.command_cooldown:
            return
        if command == self.last_command_sent:
            return
        if self.serial_comm.send_command_immediate(command):
            self.last_command_sent = command
            self.last_command_time = now

"""
session_logger.py
CSV event logging + plain-text session summary.
"""

import os
import time
import csv


class SessionLogger:
    def __init__(self, log_dir=None):
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
        log_dir = os.path.abspath(log_dir)
        os.makedirs(log_dir, exist_ok=True)

        self.session_id = time.strftime("%Y%m%d_%H%M%S")
        self.event_log_path = os.path.join(log_dir, f"events_{self.session_id}.csv")
        self.summary_path = os.path.join(log_dir, f"summary_{self.session_id}.txt")
        self.session_start = time.time()

        self._file = open(self.event_log_path, "w", newline="")
        self._writer = csv.writer(self._file)
        self._writer.writerow(["timestamp", "elapsed_seconds", "event", "details"])
        self._file.flush()

        self.phone_events = 0
        self.drink_events = 0
        self._phone_was_active = False
        self._drink_was_active = False

    def log(self, event, details=""):
        elapsed = time.time() - self.session_start
        self._writer.writerow([
            time.strftime("%Y-%m-%d %H:%M:%S"), f"{elapsed:.2f}", event, details
        ])
        self._file.flush()

    def track_status(self, status):
        if status == "PHONE USE DETECTED" and not self._phone_was_active:
            self.phone_events += 1
            self.log("PHONE_USE_START")
        self._phone_was_active = (status == "PHONE USE DETECTED")

        if status == "DRINKING DETECTED" and not self._drink_was_active:
            self.drink_events += 1
            self.log("DRINKING_START")
        self._drink_was_active = (status == "DRINKING DETECTED")

    def write_summary_file(self, engine_summary, ear_threshold, mar_threshold):
        mm, ss = divmod(int(engine_summary["duration_seconds"]), 60)
        dmm, dss = divmod(int(engine_summary["drowsy_time_seconds"]), 60)
        with open(self.summary_path, "w") as f:
            f.write("DRIVER MONITORING SESSION SUMMARY\n" + "=" * 40 + "\n")
            f.write(f"Session ID: {self.session_id}\n")
            f.write(f"Duration: {mm:02d}:{ss:02d}\n\n")
            f.write(f"Yawns: {engine_summary['yawns']}\n")
            f.write(f"Drowsy episodes: {engine_summary['drowsy_episodes']}\n")
            f.write(f"Total time drowsy: {dmm:02d}:{dss:02d}\n")
            f.write(f"Longest eyes-closed streak: {engine_summary['max_closed_time']:.2f}s\n")
            f.write(f"Average EAR: {engine_summary['avg_ear']:.3f}\n\n")
            f.write(f"Phone-use events: {self.phone_events}\n")
            f.write(f"Drinking events: {self.drink_events}\n\n")
            f.write(f"EAR threshold used: {ear_threshold:.3f}\n")
            f.write(f"MAR threshold used: {mar_threshold:.3f}\n")

    def close(self):
        self._file.close()

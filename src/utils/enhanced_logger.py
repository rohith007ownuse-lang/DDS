"""
enhanced_logger.py
Enhanced logging with real-time analytics and detailed session summaries.
Provides sliding window analytics and comprehensive session reporting.
"""

import os
import time
import json
import csv
import threading
from collections import deque, defaultdict
from datetime import datetime, timedelta
# Import colors from utils (they're defined in src/utils/utils.py)
try:
    from src.utils.utils import COL_RED as _RED, COL_AMBER as _AMBER, COL_GREEN as _GREEN, COL_CYAN as _CYAN
    from src.utils.config_manager import get_config
except ImportError:
    # Fallback colors if import fails
    _RED = (50, 50, 255)
    _AMBER = (0, 170, 255)
    _GREEN = (110, 220, 90)
    _CYAN = (255, 230, 40)

    # Fallback get_config function
    def get_config():
        return {}


class EnhancedSessionLogger:
    """
    Enhanced logger that provides:
    1. Real-time sliding window analytics (5/10/15 minute summaries)
    2. Detailed session summary on exit
    3. Configurable logging levels and formats
    4. Thread-safe operation
    """

    def __init__(self, log_dir=None, config_manager=None):
        self.config = config_manager or get_config()

        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
        self.log_dir = os.path.abspath(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)

        self.session_id = time.strftime("%Y%m%d_%H%M%S")
        self.session_start = time.time()

        # Event logging (CSV format for compatibility)
        self.event_log_path = os.path.join(self.log_dir, f"events_{self.session_id}.csv")
        self.summary_path = os.path.join(self.log_dir, f"summary_{self.session_id}.txt")

        # Real-time analytics storage
        self.analytics_window = self.config.get('logging.realtime_analytics_window', 600)  # 10 minutes default
        self._event_deque = deque(maxlen=10000)  # Rolling window of events
        self._lock = threading.Lock()

        # Sliding window analytics counters
        self._window_counters = {
            '5min': defaultdict(int),
            '10min': defaultdict(int),
            '15min': defaultdict(int)
        }
        self._window_timestamps = {
            '5min': time.time(),
            '10min': time.time(),
            '15min': time.time()
        }

        # Initialize event log file
        self._init_event_log()

        # Start analytics update thread if enabled
        if self.config.get('logging.enable_detailed_logging', True):
            self._analytics_thread = threading.Thread(target=self._analytics_worker, daemon=True)
            self._analytics_thread.start()

        self.phone_events = 0
        self.drink_events = 0
        self._phone_was_active = False
        self._drink_was_active = False

    def _init_event_log(self):
        """Initialize the event log file with headers."""
        try:
            with open(self.event_log_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "elapsed_seconds", "event", "details", "session_id"])
        except Exception as e:
            print(f"[EnhancedLogger] Error initializing event log: {e}")

    def log(self, event, details=""):
        """Log an event with timestamp and details."""
        elapsed = time.time() - self.session_start
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        event_data = {
            'timestamp': timestamp,
            'elapsed': elapsed,
            'event': event,
            'details': details,
            'session_id': self.session_id
        }

        with self._lock:
            self._event_deque.append(event_data)

            # Write to CSV file
            try:
                with open(self.event_log_path, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([timestamp, f"{elapsed:.2f}", event, details, self.session_id])
            except Exception as e:
                print(f"[EnhancedLogger] Error writing to event log: {e}")

            # Update sliding window counters
            self._update_window_counters(event, elapsed)

    def _update_window_counters(self, event, elapsed):
        """Update sliding window counters for analytics."""
        now = time.time()

        # Check and update each window
        for window_name, window_seconds in [('5min', 300), ('10min', 600), ('15min', 900)]:
            window_start = now - window_seconds

            # Reset counter if window has expired
            if now - self._window_timestamps[window_name] > window_seconds:
                self._window_counters[window_name].clear()
                self._window_timestamps[window_name] = now

            # Increment counter for this event
            self._window_counters[window_name][event] += 1

    def track_status(self, status):
        """Track status changes for phone/drink detection."""
        if status == "PHONE USE DETECTED" and not self._phone_was_active:
            self.phone_events += 1
            self.log("PHONE_USE_START")
        self._phone_was_active = (status == "PHONE USE DETECTED")

        if status == "DRINKING DETECTED" and not self._drink_was_active:
            self.drink_events += 1
            self.log("DRINKING_START")
        self._drink_was_active = (status == "DRINKING DETECTED")

    def get_realtime_analytics(self, window_minutes=10):
        """
        Get analytics for the specified time window.
        Returns dict with event counts and rates.
        """
        window_key = f'{window_minutes}min'
        with self._lock:
            counts = dict(self._window_counters[window_key])

        window_seconds = window_minutes * 60
        total_events = sum(counts.values())
        rate_per_minute = (total_events / window_seconds) * 60 if window_seconds > 0 else 0

        return {
            'window_minutes': window_minutes,
            'total_events': total_events,
            'event_counts': counts,
            'rate_per_minute': round(rate_per_minute, 2),
            'most_common_event': max(counts.items(), key=lambda x: x[1])[0] if counts else None
        }

    def get_comprehensive_summary(self, engine_summary, ear_threshold, mar_threshold):
        """Generate a detailed session summary."""
        session_duration = time.time() - self.session_start

        # Get analytics for different windows
        analytics_5min = self.get_realtime_analytics(5)
        analytics_10min = self.get_realtime_analytics(10)
        analytics_15min = self.get_realtime_analytics(15)

        # Format timestamps
        start_time = datetime.fromtimestamp(self.session_start)
        end_time = datetime.fromtimestamp(time.time())

        summary = f"""DRIVER MONITORING SESSION SUMMARY
{'=' * 50}

Session Information:
  Session ID: {self.session_id}
  Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
  End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
  Duration: {int(session_duration//3600):02d}:{int((session_duration%3600)//60):02d}:{int(session_duration%60):02d}

Detection Performance:
  Yawns Detected: {engine_summary.get('yawns', 0)}
  Drowsy Episodes: {engine_summary.get('drowsy_episodes', 0)}
  Total Drowsy Time: {int(engine_summary.get('drowsy_time_seconds', 0)//60):02d}:{int(engine_summary.get('drowsy_time_seconds', 0)%60):02d}
  Longest Eyes-Closed Streak: {engine_summary.get('max_closed_time', 0):.2f}s
  Average EAR: {engine_summary.get('avg_ear', 0):.3f}
  EAR Threshold Used: {ear_threshold:.3f}
  MAR Threshold Used: {mar_threshold:.3f}

Distraction Events:
  Phone Use Events: {self.phone_events}
  Drinking Events: {self.drink_events}

Real-Time Analytics (Sliding Windows):
  5-Minute Window:
    Total Events: {analytics_5min['total_events']}
    Rate: {analytics_5min['rate_per_minute']} events/min
    Most Common: {analytics_5min['most_common_event'] or 'None'}

  10-Minute Window:
    Total Events: {analytics_10min['total_events']}
    Rate: {analytics_10min['rate_per_minute']} events/min
    Most Common: {analytics_10min['most_common_event'] or 'None'}

  15-Minute Window:
    Total Events: {analytics_15min['total_events']}
    Rate: {analytics_15min['rate_per_minute']} events/min
    Most Common: {analytics_15min['most_common_event'] or 'None'}

Recent Event History (Last 10 Events):
"""

        # Add last 10 events
        with self._lock:
            recent_events = list(self._event_deque)[-10:] if len(self._event_deque) >= 10 else list(self._event_deque)

        for event in reversed(recent_events):  # Most recent first
            summary += f"  [{event['timestamp']}] {event['event']}: {event['details']}\n"

        summary += f"""
Configuration Used:
  Detection Settings:
    EAR Threshold: {ear_threshold}
    MAR Threshold: {mar_threshold}
    Eye Closed Duration: {self.config.get('detection.eye_closed_duration', 1.3)}s
    Yawn Duration: {self.config.get('detection.yawn_duration', 1.0)}s
    Head Pose Duration: {self.config.get('detection.head_pose_duration', 1.3)}s
    PERCLOS Window: {self.config.get('detection.perclos_window', 60.0)}s
    PERCLOS Threshold: {self.config.get('detection.perclos_threshold', 0.15)}

System Notes:
  - All processing performed locally on device
  - No personal data transmitted or stored externally
  - Session logs stored in: {self.log_dir}
  - Enhanced logging enabled: {self.config.get('logging.enable_detailed_logging', True)}

End of Summary
{'=' * 50}
"""
        return summary

    def write_summary_file(self, engine_summary, ear_threshold, mar_threshold):
        """Write the comprehensive summary to file."""
        try:
            summary = self.get_comprehensive_summary(engine_summary, ear_threshold, mar_threshold)
            with open(self.summary_path, "w") as f:
                f.write(summary)
            print(f"[EnhancedLogger] Session summary written to: {self.summary_path}")
        except Exception as e:
            print(f"[EnhancedLogger] Error writing summary file: {e}")

    def close(self):
        """Clean up resources."""
        # The analytics thread is daemon, so it will exit when main thread exits
        pass

    def _analytics_worker(self):
        """Background worker for periodic analytics updates."""
        while True:
            time.sleep(30)  # Update every 30 seconds
            # Could add periodic logging or other analytics tasks here
            pass


# Global enhanced logger instance
_enhanced_logger = None


def get_enhanced_logger() -> EnhancedSessionLogger:
    """Get or create the global enhanced logger instance."""
    global _enhanced_logger
    if _enhanced_logger is None:
        _enhanced_logger = EnhancedSessionLogger()
    return _enhanced_logger


def init_enhanced_logger(log_dir=None, config_manager=None):
    """Initialize the enhanced logger with optional parameters."""
    global _enhanced_logger
    _enhanced_logger = EnhancedSessionLogger(log_dir, config_manager)
    return _enhanced_logger
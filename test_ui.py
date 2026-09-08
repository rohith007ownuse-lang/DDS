#!/usr/bin/env python3
"""
Test script to verify the UI dashboard can be instantiated without error.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Mock the dependencies
class MockCap:
    def isOpened(self):
        return True
    def read(self):
        return (True, None)
    def release(self):
        pass

class MockFaceMeshModule:
    def detect_face(self, rgb):
        # Return a mock result with empty multi_face_landmarks
        class MockResults:
            multi_face_landmarks = []
        return MockResults()
    def draw_face_mesh(self, frame, landmarks):
        pass

class MockEngine:
    def process_frame(self, landmarks, frame_w, frame_h):
        return {
            "drowsy_percent": 0,
            "perclos": 0,
            "closed_time": 0.0,
            "yawn_counter": 0,
            "pose_alert_duration": 0.0,
            "drowsy_start_event": False,
            "drowsy_end_event": False,
            "yawn_event": False,
            "status": "NORMAL",
            "severity": None
        }
    def handle_face_lost(self):
        return {
            "drowsy_percent": 0,
            "perclos": 0,
            "closed_time": 0.0,
            "yawn_counter": 0,
            "pose_alert_duration": 0.0,
            "drowsy_start_event": False,
            "drowsy_end_event": False,
            "yawn_event": False,
            "status": "NORMAL",
            "severity": None
        }
    def reset(self):
        pass
    def summary(self, duration):
        return {"duration_seconds": duration}
    EAR_THRESHOLD = 0.2
    MAR_THRESHOLD = 0.5

class MockObjectDetector:
    def process_frame(self, frame):
        return {
            "status": "NORMAL",
            "severity": None,
            "distraction_percent": 0,
            "detections": []
        }

class MockAlertManager:
    def update(self, overall_severity):
        pass
    def stop(self):
        pass

class MockLogger:
    def __init__(self):
        self.session_start = 0
    def get_realtime_analytics(self, window_minutes):
        return {
            "event_counts": {
                "YAWN": 0,
                "DROWSINESS_START": 0
            },
            "total_events": 0,
            "rate_per_minute": 0
        }
    def track_status(self, status):
        pass
    def log(self, event, data=None):
        pass
    def write_summary_file(self, summary, ear_thresh, mar_thresh):
        pass
    def close(self):
        pass

def test_ui():
    """Test that the UI can be created without error."""
    cap = MockCap()
    face_mesh_module = MockFaceMeshModule()
    engine = MockEngine()
    object_detector = MockObjectDetector()
    alert_manager = MockAlertManager()
    logger = MockLogger()

    # Import the app class
    from src.ui.tk_dashboard import DrowsiGuardApp

    # Create the app instance
    app = DrowsiGuardApp(
        cap=cap,
        face_mesh_module=face_mesh_module,
        engine=engine,
        object_detector=object_detector,
        alert_manager=alert_manager,
        logger=logger,
        test_mode=True  # We assume test_mode skips the video update loop
    )

    # Destroy the app immediately to avoid entering the mainloop
    app.destroy()
    print("UI test passed: DrowsiGuardApp instantiated and destroyed without error.")

if __name__ == "__main__":
    test_ui()
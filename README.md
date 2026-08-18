# DrowsiGuard - Driver Monitoring System (Tkinter UI)

## Setup
1. Python 3.10 or 3.11 recommended (mediapipe compatibility)
2. pip install -r requirements.txt
3. python main.py

First run downloads YOLOv8n weights automatically (~6MB, needs internet once).
Alert tones generate automatically on first run - no external audio files needed.

## What's real vs. demo in this UI
REAL (wired to your actual detectors):
  Fatigue %, Attention %, PERCLOS, Eye Closure, Yawns, Phone/Drink detection,
  Alert cards, Time Driven, live webcam feed with real face-mesh overlay,
  Night Mode (a real toggle - blends a tint over the feed), Alert Threshold
  buttons (genuinely clickable, affect which pill is highlighted).

HONEST DEMO/PLACEHOLDER (clearly labeled "(DEMO)" in the UI, not real hardware):
  Vehicle Status panel - no OBD-II hardware connected.
  Live Location map - no GPS hardware connected. The animated route is a
  visual demo of what this panel could show once GPS hardware is added,
  not fabricated real data.

Gaze Direction and smoke/cigarette detection are marked "not tracked yet" /
"(planned)" rather than faked, since neither is implemented yet.

## Architecture
- Calibration still runs in a plain cv2 window (src/calibration.py) since
  it already worked well and re-implementing a one-time 5s step in Tkinter
  wasn't worth the effort.
- The live dashboard (src/tk_dashboard.py) is a Tkinter app. main.py runs
  calibration first, then launches it.
- All detection logic (fatigue_engine.py, object_detection.py, head_pose.py,
  eye_detection.py, mouth_detection.py, severity.py, alert_manager.py,
  session_logger.py) is UNCHANGED from the OpenCV version - only the UI
  layer changed. If you still have the old cv2 dashboard.py, you can keep
  it around for reference, but main.py now uses tk_dashboard.py instead.

## Testing note
This was tested headlessly using Xvfb (a virtual display) with synthetic
data injected via DrowsiGuardApp.process_one_frame()/apply_frame_result(),
verified by sampling actual rendered pixel colors to confirm severity-based
coloring works (green dominant in NORMAL, red spikes in CRITICAL, yellow
spikes in WARNING). It has NOT been tested with a real webcam/real
MediaPipe/real YOLO on an actual display - please verify on your machine
and report anything that looks off.

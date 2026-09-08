# Graph Report - DriverDrowsinessDetectionSystem  (2026-09-08)

## Corpus Check
- 43 files · ~57,026 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 364 nodes · 549 edges · 18 communities (11 shown, 2 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 5 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `581052f7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- DrowsiGuardApp
- get_config
- SerialCommunicator
- fatigue_engine.py
- test_ui.py
- MapCanvas
- Hardware Integration Plan for Driver Drowsiness Detection System
- EnhancedSessionLogger
- ObjectDetector
- face_detection.py
- AlertManager
- VehicleControlPanel
- SessionLogger

## God Nodes (most connected - your core abstractions)
1. `DrowsiGuardApp` - 27 edges
2. `get_config()` - 22 edges
3. `SerialCommunicator` - 21 edges
4. `VehicleControlPanel` - 18 edges
5. `MapCanvas` - 17 edges
6. `ConfigManager` - 17 edges
7. `Hardware Integration Plan for Driver Drowsiness Detection System` - 14 edges
8. `EnhancedSessionLogger` - 14 edges
9. `FatigueEngine` - 13 edges
10. `main()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `FatigueEngine`  [EXTRACTED]
  main.py → src/core/fatigue_engine.py
- `main()` --calls--> `ObjectDetector`  [EXTRACTED]
  main.py → src/detectors/object_detection.py
- `main()` --calls--> `DrowsiGuardApp`  [EXTRACTED]
  main.py → src/ui/tk_dashboard.py
- `main()` --calls--> `AlertManager`  [EXTRACTED]
  main.py → src/utils/alert_manager.py
- `main()` --calls--> `run_calibration()`  [EXTRACTED]
  main.py → src/utils/calibration.py

## Import Cycles
- None detected.

## Communities (18 total, 2 thin omitted)

### Community 0 - "DrowsiGuardApp"
Cohesion: 0.08
Nodes (16): DrowsiGuardApp, MetricCard, pct_color(), pct_word(), tk_dashboard.py Tkinter-based live dashboard. Built on the visual…, Enhanced vehicle status with more realistic variations, Reconfigure this card's widgets in place - no recreation, no flicker., Update the guided navigation from Campari house to Parliament House (+8 more)

### Community 1 - "get_config"
Cohesion: 0.06
Nodes (44): Any, check_dependencies(), main(), main.py Runs the 5s calibration in a plain cv2 window (reused as-is since it…, Check for essential system dependencies and warn if missing., serial_communicator.py Handles serial communication with Arduino hardware for…, vehicle_control_panel.py Separate window for manual vehicle control. Provides…, ConfigManager (+36 more)

### Community 2 - "SerialCommunicator"
Cohesion: 0.07
Nodes (20): init_serial_communicator(), Main worker loop handling connection, commands, and heartbeats., Attempt to establish serial connection., Manages serial communication with Arduino hardware. Features: - Automatic…, Disconnect from serial port., Process commands from the queue., Send a command to the Arduino. Uses state-change optimization to avoid sending…, Public method to queue a command for sending. (+12 more)

### Community 3 - "fatigue_engine.py"
Cohesion: 0.08
Nodes (23): FatigueEngine, fatigue_engine.py The only module that reads eye + mouth + head-pose signals…, Manually clear the latched emergency stop state and send RESET ("R") to the…, calculate_avg_ear(), calculate_ear(), eye_detection.py Everything about measuring eye openness., get_head_pose(), HeadPoseTracker (+15 more)

### Community 4 - "test_ui.py"
Cohesion: 0.09
Nodes (9): MockAlertManager, MockCap, MockEngine, MockFaceMeshModule, MockLogger, MockObjectDetector, Test script to verify the UI dashboard can be instantiated without error., Test that the UI can be created without error. (+1 more)

### Community 5 - "MapCanvas"
Cohesion: 0.11
Nodes (11): MapCanvas, Load and prepare a map image for display, Create a default path from bottom-left to top-right if none provided, Create a bus-like vehicle icon, Update with custom path points, Update with real GPS data points, Map a value from one range to another, Move vehicle smoothly along the predefined path (+3 more)

### Community 6 - "Hardware Integration Plan for Driver Drowsiness Detection System"
Cohesion: 0.06
Nodes (32): Communication Protocol, Communication Reliability:, Configuration Parameters, Current System Status, Data Flow, Dependencies, Estimated Effort, Fail-Safe Design: (+24 more)

### Community 7 - "EnhancedSessionLogger"
Cohesion: 0.12
Nodes (11): EnhancedSessionLogger, get_config(), Update sliding window counters for analytics., Track status changes for phone/drink detection., Get analytics for the specified time window. Returns dict with event counts and…, Generate a detailed session summary., Write the comprehensive summary to file., Background worker for periodic analytics updates. (+3 more)

### Community 8 - "ObjectDetector"
Cohesion: 0.22
Nodes (5): combine(), severity.py Single source of truth mapping every possible detector status to a…, severity_for(), ObjectDetector, object_detection.py Phone/drink detection using stock pretrained YOLOv8n.…

### Community 9 - "face_detection.py"
Cohesion: 0.14
Nodes (14): _draw_face_landmarks(), draw_face_mesh(), _ensure_model_exists(), FaceLandmarkerResult, FaceMesh, _normalized_to_pixel_coordinates(), face_detection.py Face detection and landmarking using MediaPipe…, Converts normalized value pair to pixel coordinates. (+6 more)

### Community 10 - "AlertManager"
Cohesion: 0.15
Nodes (8): AlertManager, alert_manager.py Owns all sound. Non-dismissible - no snooze/dismiss method…, Play the given wav file in a loop until stopped., Detect available audio player based on OS., Check if a command exists in PATH., Build command to play wav file in a loop based on OS., generate_tone_wav(), audio_synth.py Generates alert tone .wav files procedurally - pure Python…

## Knowledge Gaps
- **24 isolated node(s):** `Overview`, `Current System Status`, `Communication Protocol`, `Data Flow`, `Phase 1: Serial Communication Layer` (+19 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 171 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DrowsiGuardApp` connect `DrowsiGuardApp` to `get_config`, `VehicleControlPanel`, `test_ui.py`?**
  _High betweenness centrality (0.240) - this node is a cross-community bridge._
- **Why does `get_config()` connect `get_config` to `DrowsiGuardApp`, `VehicleControlPanel`, `SerialCommunicator`, `fatigue_engine.py`?**
  _High betweenness centrality (0.151) - this node is a cross-community bridge._
- **Why does `SerialCommunicator` connect `SerialCommunicator` to `get_config`, `fatigue_engine.py`?**
  _High betweenness centrality (0.149) - this node is a cross-community bridge._
- **What connects `Overview`, `Current System Status`, `Communication Protocol` to the rest of the system?**
  _24 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `DrowsiGuardApp` be split into smaller, more focused modules?**
  _Cohesion score 0.07665505226480836 - nodes in this community are weakly interconnected._
- **Should `get_config` be split into smaller, more focused modules?**
  _Cohesion score 0.055191256830601096 - nodes in this community are weakly interconnected._
- **Should `SerialCommunicator` be split into smaller, more focused modules?**
  _Cohesion score 0.07357357357357357 - nodes in this community are weakly interconnected._
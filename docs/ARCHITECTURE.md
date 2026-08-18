# System Architecture

## Overview

The Driver Drowsiness Detection System is built on a modular architecture with clear separation of concerns:

```
Input (Webcam)
    ↓
Face Detection → Head Pose → Eye Detection → Mouth Detection → Object Detection
    ↓                                              ↓
Facial Landmarks ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ↓
    ↓
Fatigue Engine (Score Calculation)
    ↓
Severity Classification (NORMAL/WARNING/CRITICAL)
    ↓
Alert Manager + Dashboard
    ↓
Output (Alerts, UI, Logs)
```

## Module Breakdown

### Detectors (`src/detectors/`)

#### FaceDetection (`face_detection.py`)
- Uses MediaPipe Face Mesh for landmark detection
- Detects 468 facial landmarks
- Provides face rectangle coordinates
- Input: Frame
- Output: Face landmarks, face region

#### EyeDetection (`eye_detection.py`)
- Analyzes eye landmarks from face mesh
- Calculates EAR (Eye Aspect Ratio)
- Detects eye closure and blinks
- Input: Eye landmarks, face landmarks
- Output: Eye state, blink count, closure duration

#### MouthDetection (`mouth_detection.py`)
- Analyzes mouth landmarks
- Detects yawning based on mouth opening
- Input: Mouth landmarks
- Output: Mouth opening ratio, yawn count

#### HeadPose (`head_pose.py`)
- Estimates head rotation angles (yaw, pitch, roll)
- Detects head nodding
- Input: Face landmarks
- Output: Head angles, pose classification

#### ObjectDetection (`object_detection.py`)
- YOLOv8 nano model for person/face detection
- Detects phones, cups (proxy for alertness)
- Input: Frame
- Output: Detected objects, bounding boxes

### Core (`src/core/`)

#### FatigueEngine (`fatigue_engine.py`)
- Aggregates signals from all detectors
- Calculates drowsiness score (0-100)
- Tracks metrics:
  - PERCLOS (Percentage of Eye Closure)
  - Blink rate
  - Yawn frequency
  - Head movements
  - Attention score

Algorithm:
```
drowsiness_score = 
  (PERCLOS_weight × PERCLOS) +
  (blink_weight × blink_abnormality) +
  (yawn_weight × yawn_frequency) +
  (head_weight × head_nodding_rate)
```

#### Severity (`severity.py`)
- Classifies drowsiness level into 3 categories:
  - **NORMAL** (score < 40): Alert driver, continue monitoring
  - **WARNING** (40 ≤ score < 70): Visual warning, louder alerts
  - **CRITICAL** (score ≥ 70): Trigger alarm, suggest pulling over

### UI (`src/ui/`)

#### TkDashboard (`tk_dashboard.py`)
- Tkinter-based real-time dashboard
- Components:
  - Live video feed with overlay
  - Drowsiness meter
  - Alert history
  - Session statistics
  - Calibration controls
  - Settings panel

### Utilities (`src/utils/`)

#### AlertManager (`alert_manager.py`)
- Manages alert triggering logic
- Cooldown periods between alerts
- Alert escalation strategy

#### AudioSynth (`audio_synth.py`)
- Generates alert tones using pyttsx3
- Text-to-speech announcements
- Different alert levels produce different sounds

#### Calibration (`calibration.py`)
- Initial 5-second calibration routine
- Establishes baseline face detection
- Tests all sensors
- Sets default thresholds

#### SessionLogger (`session_logger.py`)
- Logs all detection events to CSV
- Generates session summaries
- Event format: timestamp, metrics, classification

#### Utils (`utils.py`)
- Helper functions
- Coordinate transformations
- Image processing utilities

## Data Flow

### Per-Frame Processing (~33ms at 30 FPS)

```python
frame = camera.read()
                ↓
face_landmarks = face_detector.detect(frame)
                ↓
eye_state = eye_detector.analyze(face_landmarks)
mouth_state = mouth_detector.analyze(face_landmarks)
head_pose = head_pose_detector.estimate(face_landmarks)
objects = yolo_detector.detect(frame)
                ↓
drowsiness_score = fatigue_engine.calculate(
    eye_state, mouth_state, head_pose, objects
)
                ↓
severity = severity_classifier.classify(drowsiness_score)
                ↓
if severity requires alert:
    alert_manager.trigger_alert(severity)
                ↓
session_logger.log_event(timestamp, metrics, severity)
                ↓
dashboard.update_display(frame, drowsiness_score, severity)
```

## Model Dependencies

### MediaPipe Face Mesh
- **Model**: face_landmarker.task
- **Input**: 192×192 RGB images
- **Output**: 468 3D facial landmarks
- **Latency**: ~10ms on GPU, ~50ms on CPU

### YOLOv8 Nano
- **Model**: yolov8n.pt
- **Input**: 640×640 RGB images
- **Output**: Object detections with confidence
- **Latency**: ~20ms on GPU, ~100ms on CPU

## Key Design Decisions

1. **Modular Architecture**: Each detector is independent, allowing easy testing and swapping
2. **Real-time Processing**: Optimized for 30 FPS operation
3. **Graceful Degradation**: System works even if some detectors fail
4. **Threshold-based Classification**: Clear boundaries for alerting
5. **Event Logging**: Complete audit trail of system decisions
6. **User Calibration**: Initial setup ensures personal baseline

## Performance Optimization

### GPU Acceleration
- MediaPipe can use GPU for face detection
- YOLOv8 supports CUDA/TensorRT

### Frame Skipping
- Optional frame skipping for CPU-constrained systems
- Processes every frame, analyzes every other

### Memory Management
- Frame buffering for temporal analysis
- Ring buffer for metrics history

## Error Handling

- **Graceful degradation**: If face not detected, use last known position
- **Timeout handling**: If detector hangs, skip frame
- **Invalid data filtering**: Outlier rejection for metrics
- **Logging**: All errors logged with context

## Future Enhancements

1. **Gaze Direction**: Eye gaze tracking for attention zones
2. **Facial Expression**: Emotion detection
3. **Voice Analysis**: Drowsiness detection from speech patterns
4. **Vehicle Integration**: OBD-II data integration
5. **Multi-camera**: Support for cabin monitoring
6. **Deep Learning**: Replace threshold-based severity with neural network

## Testing Strategy

- **Unit tests**: Individual detector validation
- **Integration tests**: Full pipeline end-to-end
- **Performance tests**: Latency and accuracy benchmarks
- **Edge cases**: Poor lighting, occlusions, multiple faces

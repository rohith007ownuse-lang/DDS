# Setup Guide

## System Requirements

### Minimum
- Python 3.8
- Webcam (built-in or USB)
- 2GB RAM
- Intel i5 or equivalent

### Recommended
- Python 3.10+
- USB 3.0 webcam
- 4GB+ RAM
- Intel i7 / Apple Silicon / AMD Ryzen 5+
- GPU (NVIDIA CUDA or Apple Metal)

### Supported Platforms
- Linux (Ubuntu 20.04+, Debian 11+)
- Windows 10/11
- macOS 11+

## Step-by-Step Installation

### 1. Prerequisites

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv

# Arch
sudo pacman -S python python-pip

# Fedora
sudo dnf install python3 python3-pip
```

#### Windows
- Download Python 3.10+ from python.org
- Add Python to PATH during installation

#### macOS
```bash
# Using Homebrew
brew install python3
```

### 2. Clone Repository

```bash
git clone https://github.com/yourusername/DriverDrowsinessDetectionSystem.git
cd DriverDrowsinessDetectionSystem
```

### 3. Create Virtual Environment

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 5. Download Models (if needed)

Models download automatically on first run. Manual download:

```bash
# YOLOv8 nano (6MB)
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# MediaPipe Face Landmarker
# Download from: https://developers.google.com/mediapipe/solutions/vision/face_landmarker/
# Place in models/
```

### 6. Test Installation

```bash
# Test imports
python -c "import cv2, mediapipe, torch; print('✓ All libraries loaded')"

# Test webcam
python -c "import cv2; cap = cv2.VideoCapture(0); print('✓ Webcam OK' if cap.isOpened() else '✗ Webcam failed'); cap.release()"
```

## Running the Application

### First Run

```bash
python main.py
```

On first run:
1. System performs 5-second calibration
2. Face detection baseline is established
3. Models are downloaded/initialized
4. Dashboard launches

### Dashboard Controls

#### Calibration
- **Calibrate**: Re-run calibration for better accuracy
- **Save Settings**: Save current thresholds

#### Monitoring
- **Start**: Begin monitoring
- **Pause**: Pause detection (keeps recording)
- **Stop**: Stop and save session

#### Settings
- **Sensitivity**: Adjust detection sensitivity (Low/Medium/High)
- **Alert Volume**: Set alert sound volume
- **Night Mode**: Enable for low-light driving

#### Data
- **View Logs**: Open session logs
- **Export Session**: Save current session data
- **Clear History**: Reset event log

## Configuration

### Main Configuration File

Edit `config/config.yaml`:

```yaml
# Detection Settings
detection:
  confidence_threshold: 0.7
  face_min_detection_confidence: 0.5
  
# Alert Thresholds
thresholds:
  normal_max: 40
  warning_max: 70
  critical_min: 70
  
# Audio
audio:
  enabled: true
  volume: 0.8
  alert_sound_type: "bell"
  
# UI
ui:
  refresh_rate: 30  # FPS
  show_landmarks: true
  night_mode: false
  
# Logging
logging:
  enabled: true
  log_directory: "data/logs"
  event_frequency: 1  # log every N frames
```

### Calibration Settings

Adjust in calibration phase:
- **Face detection confidence**: How certain before detecting a face
- **Lighting compensation**: Adjustments for light conditions
- **Personal thresholds**: Based on individual baseline

## Troubleshooting

### Webcam Issues

```bash
# Check available cameras
python -c "import cv2; print([i for i in range(5) if cv2.VideoCapture(i).isOpened()])"

# Test specific camera
python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera 0 OK' if cap.isOpened() else 'Failed')"
```

**Solution**: Check permissions, try different USB ports, restart computer

### Low Detection Accuracy

1. Re-run calibration: Click "Calibrate" in dashboard
2. Improve lighting: Ensure face is well-lit
3. Adjust sensitivity: Try "High" sensitivity setting
4. Check webcam: Ensure lens is clean

### Slow Performance

1. Disable night mode
2. Set sensitivity to "Low" (skips some frames)
3. Close other applications
4. Try CPU-optimized mode:
   ```bash
   export DISABLE_CUDA=1
   python main.py
   ```

### Models Not Found

```bash
# Re-download models
python -c "
from ultralytics import YOLO
YOLO('yolov8n.pt')
print('✓ YOLOv8n ready')
"
```

### Permission Denied

```bash
# Linux: Fix webcam permissions
sudo usermod -a -G video $USER
# Log out and back in
```

## Development Setup

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

Includes: pytest, black, flake8, mypy

### Run Tests

```bash
pytest tests/
pytest tests/test_detectors.py -v
```

### Code Formatting

```bash
black src/
flake8 src/ --max-line-length=100
```

### Type Checking

```bash
mypy src/ --ignore-missing-imports
```

## Docker Setup (Optional)

### Build Image

```bash
docker build -t ddds:latest .
```

### Run Container

```bash
docker run --gpus all \
  -v /dev/video0:/dev/video0 \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ddds:latest
```

## GPU Acceleration (Optional)

### NVIDIA CUDA

```bash
# Install CUDA toolkit
# https://developer.nvidia.com/cuda-downloads

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Apple Silicon (Metal)

```bash
pip install torch torchvision torchaudio
# Metal acceleration automatic
```

## Performance Tuning

### For Slow Systems

```yaml
detection:
  frame_skip: 2  # Process every 2nd frame
  resolution: 480p  # Reduce camera resolution
  
thresholds:
  # Increase to reduce false alarms
  normal_max: 50
  warning_max: 75
```

### For High-End Systems

```yaml
detection:
  frame_skip: 0  # Process every frame
  resolution: 1080p
  
ui:
  refresh_rate: 60  # Higher FPS
  show_landmarks: true
```

## Next Steps

1. Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
2. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
3. Explore examples in `examples/` directory
4. Read module docstrings: `pydoc src.detectors`

## Support

- **Issues**: GitHub Issues
- **Docs**: See `/docs` folder
- **Examples**: Check `/examples` folder

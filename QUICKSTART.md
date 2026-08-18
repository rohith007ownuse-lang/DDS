# Quick Start Guide

Get your drowsiness detection system running in 5 minutes!

## ⚡ TL;DR

```bash
# 1. Clone
git clone https://github.com/rohith007ownuse-lang/DDS.git
cd DDS

# 2. Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Run
python main.py
```

That's it! Your webcam will calibrate (5 seconds) then the dashboard opens.

---

## 📋 Requirements

### System Requirements
- **Python**: 3.8+ (3.10+ recommended for MediaPipe compatibility)
- **Webcam**: Built-in or USB
- **RAM**: 2GB minimum
- **OS**: Linux, macOS, or Windows

### Python Dependencies
Automatically installed via `pip install -r requirements.txt`:
- OpenCV (computer vision)
- MediaPipe (face detection)
- YOLOv8 (object detection)
- NumPy (numerical computing)
- Pillow (image processing)
- pyttsx3 (audio alerts)

---

## 🚀 Installation Steps

### Step 1: Clone the Repository

```bash
git clone https://github.com/rohith007ownuse-lang/DDS.git
cd DDS
```

### Step 2: Create Virtual Environment

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

The first run will automatically download ML models (~50MB total):
- YOLOv8n model
- MediaPipe Face Landmarker

### Step 4: Run the Application

```bash
python main.py
```

### Step 5: Follow On-Screen Instructions

1. **Calibration** (5 seconds)
   - Sit facing the webcam
   - Let the system detect your face
   - You'll see a plain OpenCV window

2. **Dashboard Launches** 
   - Tkinter GUI appears
   - Live video feed shows
   - Monitoring begins automatically

---

## 🎯 What You'll See

### Dashboard Features

- **Live Feed**: Your webcam with face landmarks
- **Drowsiness Meter**: Real-time scoring (0-100)
- **Alert Status**: Visual indicators
- **Session Stats**: Time driven, events detected
- **Controls**: Calibrate, settings, export data

### Color Indicators

- 🟢 **Green (Normal)**: Alert < 40, you're good
- 🟡 **Yellow (Warning)**: Alert 40-70, getting tired
- 🔴 **Red (Critical)**: Alert > 70, pull over!

---

## ⚙️ Configuration (Optional)

Edit `config/config.yaml` to customize:

```yaml
# Alert sensitivity
thresholds:
  normal_max: 40      # Below this = no alert
  warning_max: 70     # Above this = critical alert

# Detection settings
detection:
  confidence_threshold: 0.7
  
# Audio
audio:
  enabled: true
  volume: 0.8
```

---

## 🧪 Testing Installation

### Verify Everything Works

```bash
# Test imports
python -c "import cv2, mediapipe, torch; print('✓ All libraries OK')"

# Test webcam
python -c "import cv2; cap = cv2.VideoCapture(0); print('✓ Webcam OK' if cap.isOpened() else '✗ No webcam')"

# Full system test
python main.py
```

---

## ⚠️ Troubleshooting

### Webcam Not Found
```bash
# Linux: Check permissions
sudo usermod -a -G video $USER
# Log out and back in

# All OS: Try listing cameras
python -c "import cv2; [print(f'Camera {i} OK') for i in range(5) if cv2.VideoCapture(i).isOpened()]"
```

### Models Download Fails
```bash
# Manually download
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### Low Detection Accuracy
- Ensure good lighting
- Clean webcam lens
- Click "Calibrate" in dashboard
- Try "High" sensitivity in settings

### Tkinter Not Found (Linux)
```bash
# Ubuntu/Debian
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

### Audio Not Playing
- Audio system may not be available in headless environments
- Disable in settings or check system audio

---

## 📁 Project Structure

```
DDS/
├── main.py              ← Run this!
├── requirements.txt     ← Dependencies
├── README.md            ← Full documentation
├── QUICKSTART.md        ← This file
├── src/
│   ├── detectors/       ← Detection modules
│   ├── core/            ← Processing logic
│   ├── ui/              ← Dashboard UI
│   └── utils/           ← Helpers
├── config/config.yaml   ← Settings
├── data/logs/           ← Event logs (auto-created)
└── docs/                ← Architecture & guides
```

---

## 🎮 Using the Dashboard

### Controls

| Action | How |
|--------|-----|
| **Start/Stop** | Click "Start" button |
| **Calibrate** | Click "Calibrate" for better accuracy |
| **Settings** | Adjust sensitivity and alerts |
| **View Logs** | Click "View Logs" to see session data |
| **Night Mode** | Toggle for low-light driving |
| **Export** | Save session to CSV |

### Keyboard Shortcuts (if implemented)

- `Esc` - Exit
- `S` - Start/Stop
- `C` - Calibrate

---

## 📊 Understanding Your Data

Events logged to `data/logs/`:
- `events_YYYYMMDD_HHMMSS.csv` - Raw detection data
- `summary_YYYYMMDD_HHMMSS.txt` - Session summary

Metrics tracked:
- **PERCLOS**: Eye closure percentage
- **Blink Rate**: Blinks per minute
- **Yawn Count**: Number of yawns detected
- **Head Pose**: Head movement angles
- **Drowsiness Score**: 0-100 composite score

---

## 🔧 Next Steps

1. **Read Full Documentation**
   - `README.md` - Features and overview
   - `docs/SETUP.md` - Detailed setup guide
   - `docs/ARCHITECTURE.md` - How it works
   - `CONTRIBUTING.md` - How to contribute

2. **Customize**
   - Edit `config/config.yaml` for your preferences
   - Run calibration periodically

3. **Monitor**
   - Check `data/logs/` for event history
   - Review session summaries

4. **Troubleshoot**
   - See `docs/TROUBLESHOOTING.md` for common issues
   - Check logs for error messages

---

## 🆘 Need Help?

- **Documentation**: Check `/docs` folder
- **Issues**: Open GitHub issue with:
  - OS and Python version
  - Error message
  - Steps to reproduce
- **Logs**: Share relevant logs from `data/logs/`

---

## 🎉 Enjoy!

Your drowsiness detection system is ready. Stay safe while driving! 🚗✅

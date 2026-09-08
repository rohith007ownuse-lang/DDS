"""
main.py
Runs the 5s calibration in a plain cv2 window (reused as-is since it
already works), then launches the Tkinter DrowsiGuard dashboard for
live monitoring.
"""

print("About to start main")
import cv2
import argparse
import sys
import shutil
import platform
import time

from src.detectors.face_detection import face_mesh
import src.detectors.face_detection as face_detection_module
from src.core.fatigue_engine import FatigueEngine
from src.utils.calibration import run_calibration
from src.utils.alert_manager import AlertManager
from src.detectors.object_detection import ObjectDetector
from src.utils.enhanced_logger import init_enhanced_logger, get_enhanced_logger
from src.utils.config_manager import get_config
from src.ui.tk_dashboard import DrowsiGuardApp

CALIB_WINDOW = "Calibration"


def check_dependencies():
    """Check for essential system dependencies and warn if missing."""
    # Check for tkinter
    try:
        import tkinter
    except ImportError:
        print("ERROR: tkinter is not installed. Please install python3-tk (or equivalent) for your system.")
        print("On Ubuntu/Debian: sudo apt install python3-tk")
        sys.exit(1)

    # Check for audio players (for alert tones)
    system = platform.system()
    audio_players = []
    if system == "Linux":
        audio_players = ['aplay', 'paplay', 'ffplay']
    elif system == "Darwin":  # macOS
        audio_players = ['afplay']
    elif system == "Windows":
        audio_players = ['powershell']  # PowerShell is used to play sounds

    found = False
    for player in audio_players:
        if shutil.which(player) is not None:
            found = True
            break
    if not found and system != "Windows":  # Windows always has PowerShell? but we check anyway
        print("WARNING: No suitable audio player found for alert tones.")
        if system == "Linux":
            print("Install one of: aplay (alsa-utils), paplay (pulseaudio), or ffplay (ffmpeg).")
        elif system == "Darwin":
            print("afplay should be available on macOS; if missing, check your installation.")
        # For Windows, we assume PowerShell is present.
    # Note: We don't exit on missing audio player; the app will run but alerts may be silent.
    print("Dependency check passed.")


def main():
    parser = argparse.ArgumentParser(description="Run DrowsiGuard driver monitoring system.")
    parser.add_argument(
        "--camera-index",
        type=int,
        default=0,
        help="Index of the webcam to use (default: 0). Use \"ls /dev/video*\" to list available devices on Linux."
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to custom configuration file"
    )
    args = parser.parse_args()
    print("Arguments parsed. About to check dependencies.")

    # Load custom config if provided
    if args.config:
        from src.utils.config_manager import ConfigManager
        global config_manager
        config_manager = ConfigManager(args.config)
        print(f"Loaded custom configuration from: {args.config}")

    # Check dependencies before initializing GUI
    check_dependencies()

    # Initialize webcam
    cap = cv2.VideoCapture(args.camera_index)
    if not cap.isOpened():
        print(f"WARNING: Cannot open webcam at index {args.camera_index}.")
        print("Camera disabled - running in simulation mode.")
        print("Please check that a webcam is connected and the index is correct,")
        print("or run with --camera-index to specify the correct device.")
        cap = None  # Set to None to continue without camera
    else:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if cap is not None:
        print("Starting calibration...")
        calib_ear, calib_mar, calib_pitch = run_calibration(cap, face_mesh, CALIB_WINDOW)
        cv2.destroyWindow(CALIB_WINDOW)

        if calib_ear is None:
            calib_ear, calib_mar, calib_pitch = 0.25, 0.45, 0.0
            print("Calibration skipped/failed -> using defaults.")
        else:
            print(f"Calibration complete -> EAR={calib_ear:.3f}, MAR={calib_mar:.3f}, pitch={calib_pitch:.1f}")
    else:
        print("Calibration skipped - no camera available.")
        calib_ear, calib_mar, calib_pitch = 0.25, 0.45, 0.0
        print(f"Calibration complete -> EAR={calib_ear:.3f}, MAR={calib_mar:.3f}, pitch={calib_pitch:.1f}")

    # Initialize configuration
    config = get_config()

    # Enable hardware if configured
    hardware_enabled = config.get('hardware.enabled', False)
    if hardware_enabled:
        print("Hardware integration enabled - initializing serial communication...")
        # Hardware will be initialized in FatigueEngine

    engine = FatigueEngine(calib_ear, calib_mar, calib_pitch)

    # Initialize enhanced logger
    logger = init_enhanced_logger()
    logger.log("CALIBRATION", f"EAR={calib_ear:.3f}, MAR={calib_mar:.3f}, pitch={calib_pitch:.1f}")

    alert_manager = AlertManager()
    print("Alert tones ready.")

    try:
        object_detector = ObjectDetector()
        print("Object detection (phone/drink) loaded OK.")
    except Exception as e:
        print(f"WARNING: object detector unavailable ({e}). Phone/drink detection disabled.")
        object_detector = None

    app = DrowsiGuardApp(
        cap=cap,
        face_mesh_module=face_detection_module,
        engine=engine,
        object_detector=object_detector,
        alert_manager=alert_manager,
        logger=logger,
    )
    app.mainloop()


if __name__ == "__main__":
    main()

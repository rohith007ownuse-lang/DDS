"""
config_manager.py
Centralized configuration management for DrowsiGuard system.
Handles loading, saving, and accessing all system parameters.
"""

import json
import os
from typing import Dict, Any, Optional
# Import colors from utils (they're defined in src/utils/utils.py)
try:
    from src.utils.utils import COL_RED as _RED, COL_AMBER as _AMBER, COL_GREEN as _GREEN, COL_CYAN as _CYAN
except ImportError:
    # Fallback colors if import fails
    _RED = (50, 50, 255)
    _AMBER = (0, 170, 255)
    _GREEN = (110, 220, 90)
    _CYAN = (255, 230, 40)


class ConfigManager:
    """Manages application configuration with persistence and validation."""

    def __init__(self, config_file: str = "config/system_config.json"):
        self.config_file = config_file
        self.config_dir = os.path.dirname(config_file)
        self._config: Dict[str, Any] = {}
        self._defaults = self._get_default_config()

        # Ensure config directory exists
        os.makedirs(self.config_dir, exist_ok=True)

        # Load existing config or create default
        self.load()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration values."""
        return {
            # Detection thresholds
            "detection": {
                "ear_threshold": 0.23,
                "mar_threshold": 0.40,
                "eye_closed_duration": 1.3,
                "yawn_duration": 1.0,
                "head_pose_duration": 1.3,
                "head_pitch_threshold": 15.0,
                "head_pose_alert_deviation": 15.0,
                "head_pose_alert_duration": 2.5,
                "perclos_window": 60.0,
                "perclos_threshold": 0.15,
                "perclos_min_samples": 30
            },

            # Hardware settings
            "hardware": {
                "enabled": False,
                "serial_port": "/dev/ttyACM0",
                "baud_rate": 9600,
                "timeout": 1.0,
                "heartbeat_interval": 0.5,
                "max_reconnect_attempts": 5,
                "reconnect_delay": 2.0,
                "command_delay": 0.05,
                "min_safe_distance": 25,
                "motor_speed": 170,
                "emergency_stop_threshold": 8.0,
                "face_loss_stop_threshold": 2.0,
                "brake_duration": 1.5
            },

            # Alert settings
            "alerts": {
                "enable_audio": True,
                "alert_volume": 0.8,
                "pre_alert_threshold": 0.8,  # Trigger pre-alert at 80% of main threshold
                "adaptive_alerting": True,
                "voice_alerts_enabled": False,
                "emergency_call_enabled": False
            },

            # Dashboard/UI settings
            "ui": {
                "theme": "dark",
                "show_fps": True,
                "show_landmarks": True,
                "night_mode_auto": True,
                "update_interval_ms": 33,
                "video_width": 640,
                "video_height": 360,
                "alert_panel_width": 200,
                "summary_panel_height": 80,
                "one_touch_action_size": 60
            },

            # Resource optimization
            "performance": {
                "adaptive_resolution": True,
                "min_resolution_width": 320,
                "min_resolution_height": 240,
                "max_fps": 30,
                "frame_skip_threshold": 0.8,  # Skip frame if processing > 80% of frame time
                "use_umat": True,
                "detect_every_n_frames": 1
            },

            # Logging & analytics
            "logging": {
                "enable_detailed_logging": True,
                "log_level": "INFO",
                "max_log_file_size_mb": 10,
                "keep_log_files": 5,
                "session_summary_on_exit": True,
                "realtime_analytics_window": 600  # 10 minutes in seconds
            },

            # Driver profiling
            "driver_profile": {
                "auto_calibrate_on_start": True,
                "calibration_duration": 10.0,
                "save_driver_profiles": True,
                "profile_storage_dir": "data/driver_profiles",
                "adaptive_thresholds": False
            },

            # Extended detection features
            "extended_detection": {
                "blink_rate_analysis": True,
                "micro_sleep_detection": True,
                "heart_rate_estimation": False,
                "gaze_tracking": True,
                "eye_openness_asymmetry": True,
                "blink_rate_threshold": 25,  # blinks per minute
                "micro_sleep_threshold": 0.5,  # seconds
                "gaze_deviation_threshold": 20  # degrees from center
            },

            # Monitoring/telemetry
            "monitoring": {
                "enable_telemetry": False,
                "telemetry_interval": 300,  # 5 minutes
                "alert_forwarding": True,
                "emergency_services_number": "911",
                "monitoring_station_id": "DRIVER_MONITOR_001"
            },

            # System info
            "system": {
                "version": "1.0.0",
                "last_updated": "2026-08-19",
                "debug_mode": False
            }
        }

    def load(self) -> bool:
        """Load configuration from file. Returns True if successful."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                # Merge with defaults to ensure all keys exist
                self._config = self._deep_merge(self._defaults, loaded_config)
                return True
            else:
                # No config file, use defaults
                self._config = self._defaults.copy()
                self.save()  # Create default config file
                return True
        except Exception as e:
            print(f"[ConfigManager] Error loading config: {e}")
            self._config = self._defaults.copy()
            return False

    def save(self) -> bool:
        """Save current configuration to file. Returns True if successful."""
        try:
            # Ensure directory exists
            os.makedirs(self.config_dir, exist_ok=True)

            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=4, sort_keys=True)
            return True
        except Exception as e:
            print(f"[ConfigManager] Error saving config: {e}")
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        Example: get('detection.ear_threshold') or get('hardware.enabled')
        """
        keys = key_path.split('.')
        value = self._config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any) -> bool:
        """
        Set configuration value using dot notation.
        Example: set('detection.ear_threshold', 0.25)
        """
        keys = key_path.split('.')
        config = self._config

        try:
            # Navigate to parent of target key
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]

            # Set the value
            config[keys[-1]] = value
            return True
        except Exception as e:
            print(f"[ConfigManager] Error setting config {key_path}: {e}")
            return False

    def update(self, updates: Dict[str, Any]) -> bool:
        """
        Update multiple configuration values at once.
        """
        try:
            self._deep_update(self._config, updates)
            return True
        except Exception as e:
            print(f"[ConfigManager] Error updating config: {e}")
            return False

    def reset_to_defaults(self) -> bool:
        """Reset configuration to default values."""
        self._config = self._defaults.copy()
        return self.save()

    def _deep_merge(self, dict1: Dict, dict2: Dict) -> Dict:
        """Recursively merge two dictionaries, with dict2 taking precedence."""
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _deep_update(self, target: Dict, updates: Dict) -> None:
        """Recursively update target dictionary with updates."""
        for key, value in updates.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value

    def get_all(self) -> Dict[str, Any]:
        """Get a copy of the entire configuration."""
        return self._config.copy()

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate configuration values.
        Returns (is_valid, list_of_errors)
        """
        errors = []

        # Validate detection thresholds
        ear = self.get('detection.ear_threshold')
        if not 0.1 <= ear <= 0.5:
            errors.append(f"EAR threshold must be between 0.1 and 0.5, got {ear}")

        mar = self.get('detection.mar_threshold')
        if not 0.1 <= mar <= 0.8:
            errors.append(f"MAR threshold must be between 0.1 and 0.8, got {mar}")

        # Validate durations
        if self.get('detection.eye_closed_duration') <= 0:
            errors.append("Eye closed duration must be positive")

        if self.get('detection.yawn_duration') <= 0:
            errors.append("Yawn duration must be positive")

        # Validate hardware settings
        if self.get('hardware.enabled'):
            port = self.get('hardware.serial_port')
            if not port:
                errors.append("Serial port must be specified when hardware is enabled")

            baud = self.get('hardware.baud_rate')
            if baud not in [300, 600, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]:
                errors.append(f"Baud rate {baud} is not standard")

        # Validate UI settings
        width = self.get('ui.video_width')
        height = self.get('ui.video_height')
        if width < 100 or height < 100:
            errors.append(f"Video dimensions too small: {width}x{height}")

        # Validate performance settings
        fps = self.get('performance.max_fps')
        if not 1 <= fps <= 60:
            errors.append(f"Max FPS must be between 1 and 60, got {fps}")

        return len(errors) == 0, errors


# Global configuration instance
config_manager = ConfigManager()


def get_config() -> ConfigManager:
    """Get the global configuration manager instance."""
    return config_manager


# Convenience functions for common config access
def get_detection_config() -> Dict[str, Any]:
    """Get detection-related configuration."""
    return get_config().get('detection', {})


def get_hardware_config() -> Dict[str, Any]:
    """Get hardware-related configuration."""
    return get_config().get('hardware', {})


def get_ui_config() -> Dict[str, Any]:
    """Get UI-related configuration."""
    return get_config().get('ui', {})


def get_performance_config() -> Dict[str, Any]:
    """Get performance-related configuration."""
    return get_config().get('performance', {})


def get_logging_config() -> Dict[str, Any]:
    """Get logging-related configuration."""
    return get_config().get('logging', {})


def get_driver_profile_config() -> Dict[str, Any]:
    """Get driver profile configuration."""
    return get_config().get('driver_profile', {})


def get_extended_detection_config() -> Dict[str, Any]:
    """Get extended detection configuration."""
    return get_config().get('extended_detection', {})


def get_monitoring_config() -> Dict[str, Any]:
    """Get monitoring/telemetry configuration."""
    return get_config().get('monitoring', {})
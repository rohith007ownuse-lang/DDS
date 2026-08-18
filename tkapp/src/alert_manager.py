"""
alert_manager.py
Owns all sound. Non-dismissible - no snooze/dismiss method exists.
"""

import os
import winsound

from src.audio_synth import generate_tone_wav

SEVERITY_CONFIG = {
    "WARNING": {"pattern": [(700, 180), (0, 600)], "volume": 0.45},
    "CRITICAL": {"pattern": [(1100, 300), (0, 120), (1100, 300), (0, 250)], "volume": 0.9},
}


class AlertManager:
    def __init__(self, asset_dir=None):
        if asset_dir is None:
            asset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generated_audio")
        self.asset_dir = os.path.abspath(asset_dir)
        os.makedirs(self.asset_dir, exist_ok=True)

        self.tone_paths = {}
        for level, cfg in SEVERITY_CONFIG.items():
            path = os.path.join(self.asset_dir, f"tone_{level.lower()}.wav")
            try:
                generate_tone_wav(path, cfg["pattern"], volume=cfg.get("volume", 0.6))
                self.tone_paths[level] = path
            except Exception as e:
                print(f"[alert_manager] Failed to synthesize {level} tone: {e}")

        self.current_level = None

    def update(self, severity):
        target = severity if severity in self.tone_paths else None
        if target == self.current_level:
            return
        winsound.PlaySound(None, winsound.SND_PURGE)
        if target is not None:
            try:
                winsound.PlaySound(
                    self.tone_paths[target],
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP
                )
            except RuntimeError as e:
                print(f"[alert_manager] Failed to play {target} tone: {e}")
        self.current_level = target

    def stop(self):
        winsound.PlaySound(None, winsound.SND_PURGE)
        self.current_level = None

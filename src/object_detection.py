"""
object_detection.py
Phone/drink detection using stock pretrained YOLOv8n. Monitor-only
(INFO severity) - never contributes to the alarm.
"""

import time
import os
from ultralytics import YOLO
from src.severity import severity_for

CLASS_PHONE = 67
CLASS_BOTTLE = 39
TARGET_CLASSES = {CLASS_PHONE: "phone", CLASS_BOTTLE: "bottle"}


class ObjectDetector:
    def __init__(self, model_path="yolov8n.pt", confidence=0.45,
                 phone_duration=1.5, drink_duration=3.0, run_every_n_frames=3):
        # If using the default model name, resolve it relative to the project root
        if model_path == "yolov8n.pt":
            model_path = os.path.join(
                os.path.abspath(os.path.join(os.path.dirname(__file__), '..')),
                "yolov8n.pt"
            )
        self.model = YOLO(model_path)
        self.confidence = confidence
        self.phone_duration_threshold = phone_duration
        self.drink_duration_threshold = drink_duration
        self.run_every_n_frames = run_every_n_frames

        self._frame_count = 0
        self._phone_start = None
        self._drink_start = None
        self._last_detections = []

    def process_frame(self, frame):
        self._frame_count += 1
        run_inference = (self._frame_count % self.run_every_n_frames == 0)

        if run_inference:
            self._last_detections = self._run_inference(frame)

        detections = self._last_detections
        now = time.time()

        phone_seen = any(d["label"] == "phone" for d in detections)
        bottle_seen = any(d["label"] == "bottle" for d in detections)

        if phone_seen:
            if self._phone_start is None:
                self._phone_start = now
            phone_duration = now - self._phone_start
        else:
            self._phone_start = None
            phone_duration = 0.0

        if bottle_seen:
            if self._drink_start is None:
                self._drink_start = now
            drink_duration = now - self._drink_start
        else:
            self._drink_start = None
            drink_duration = 0.0

        if phone_duration >= self.phone_duration_threshold:
            status = "PHONE USE DETECTED"
        elif drink_duration >= self.drink_duration_threshold:
            status = "DRINKING DETECTED"
        else:
            status = "NORMAL"

        phone_ratio = min(1.0, phone_duration / self.phone_duration_threshold) if self.phone_duration_threshold else 0.0
        drink_ratio = min(1.0, drink_duration / self.drink_duration_threshold) if self.drink_duration_threshold else 0.0
        distraction_percent = round(100 * max(phone_ratio, drink_ratio))

        return {
            "status": status, "severity": severity_for(status),
            "detections": detections,
            "phone_duration": phone_duration, "drink_duration": drink_duration,
            "distraction_percent": distraction_percent,
        }

    def _run_inference(self, frame):
        results = self.model.predict(
            frame, verbose=False, conf=self.confidence,
            classes=list(TARGET_CLASSES.keys())
        )
        detections = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append({
                    "label": TARGET_CLASSES[cls_id],
                    "confidence": conf,
                    "box": (x1, y1, x2, y2),
                })
        return detections

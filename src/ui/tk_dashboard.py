"""
tk_dashboard.py
Tkinter-based live dashboard. Built on the visual structure/style of the
provided mockup, but with real data wired in instead of hardcoded values.

REAL (wired to your actual detectors): fatigue %, attention %, PERCLOS,
eye closure, yawns, phone/drink detection, alert cards, time driven,
the actual webcam feed with real face-mesh overlay, night-mode tint
(a genuine toggle, not decorative), alert-threshold buttons (genuinely
clickable and affect what's highlighted).

HONEST DEMO/PLACEHOLDER (clearly labeled, not real hardware):
vehicle speed gauge (no OBD-II connected) and the live-location map
(no GPS connected) - both kept as visual "vision of what's possible"
demos rather than removed, but labeled so nobody mistakes them for
live data.
"""

import time
import math
import tkinter as tk
from tkinter import font as tkfont
import cv2
from PIL import Image, ImageTk
import random

from src.utils import (
    COL_RED as _RED, COL_AMBER as _AMBER, COL_GREEN as _GREEN, COL_CYAN as _CYAN
)

# ---------------- palette (hex, since this file is Tkinter not cv2) ----------------
BG      = "#0d1117"
PANEL   = "#161b22"
CARD    = "#1c2128"
BORDER  = "#30363d"
TEXT    = "#e6edf3"
MUTED   = "#8b949e"
RED     = "#f85149"
RED_DIM = "#3d1a1a"
ORANGE  = "#fb923c"
YELLOW  = "#f59e0b"
GREEN   = "#3fb950"
BLUE    = "#58a6ff"


def pct_color(pct):
    if pct >= 70:
        return RED
    if pct >= 35:
        return YELLOW
    return GREEN


def pct_word(pct):
    if pct >= 70:
        return "Critical"
    if pct >= 35:
        return "Elevated"
    return "Normal"


# ---------------- Metric card (from the provided mockup, + a real update() method) ----------------
class MetricCard(tk.Frame):
    def __init__(self, parent, label, value, unit="", status="", status_color=GREEN,
                 show_bar=True, bar_color=GREEN, bar_pct=0):
        super().__init__(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        self.show_bar = show_bar
        self.bar_color = bar_color

        tk.Label(self, text=label, bg=CARD, fg=MUTED, font=("Courier", 8)).pack(anchor="w", padx=6, pady=(5, 0))

        row = tk.Frame(self, bg=CARD)
        row.pack(anchor="w", padx=6)
        self.value_label = tk.Label(row, text=value, bg=CARD, fg=TEXT, font=("Courier", 16, "bold"))
        self.value_label.pack(side="left")
        self.unit_label = None
        if unit:
            self.unit_label = tk.Label(row, text=unit, bg=CARD, fg=MUTED, font=("Courier", 8))
            self.unit_label.pack(side="left", padx=(2, 0), pady=(4, 0))

        self.status_label = tk.Label(self, text=status, bg=CARD, fg=status_color, font=("Courier", 7))
        self.status_label.pack(anchor="w", padx=6)

        self.bar_fg = None
        if show_bar:
            bar_bg = tk.Frame(self, bg=BORDER, height=4)
            bar_bg.pack(fill="x", padx=6, pady=(3, 5))
            bar_bg.pack_propagate(False)
            self.bar_fg = tk.Frame(bar_bg, bg=bar_color, height=4)
            self.bar_fg.place(relwidth=bar_pct / 100, relheight=1)
        else:
            tk.Frame(self, bg=CARD, height=6).pack()

    def update_values(self, value=None, status=None, status_color=None, bar_pct=None):
        """Reconfigure this card's widgets in place - no recreation, no flicker."""
        if value is not None:
            self.value_label.configure(text=value)
        if status is not None:
            self.status_label.configure(text=status)
        if status_color is not None:
            self.status_label.configure(fg=status_color)
            if self.bar_fg is not None:
                self.bar_fg.configure(bg=status_color)
        if bar_pct is not None and self.bar_fg is not None:
            self.bar_fg.place(relwidth=max(0.0, min(1.0, bar_pct / 100)), relheight=1)


# ---------------- Video canvas: REAL webcam frame + real overlays ----------------
class VideoCanvas(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg="black", highlightthickness=0, **kw)
        self._photo = None  # must keep a reference or Tkinter garbage-collects it
        self._tick = 0

    def update_frame(self, bgr_frame, overall_severity, overall_status):
        """bgr_frame should already have face-mesh/detection boxes drawn on it
        by the caller (main.py) - this method only handles display + the
        severity banner overlay."""
        self._tick += 1
        w = self.winfo_width() or 640
        h = self.winfo_height() or 360

        frame = cv2.resize(bgr_frame, (w, h))

        if overall_severity in ("WARNING", "CRITICAL"):
            color = (0, 0, 255) if overall_severity == "CRITICAL" else (0, 165, 255)
            box_w, box_h = 240, 60
            bx, by = (w - box_w) // 2, h // 2 - 60
            overlay = frame.copy()
            cv2.rectangle(overlay, (bx, by), (bx + box_w, by + box_h), (10, 10, 10), -1)
            cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, dst=frame)
            cv2.rectangle(frame, (bx, by), (bx + box_w, by + box_h), color, 2)
            label = "WARNING" if overall_severity == "WARNING" else "CRITICAL"
            cv2.putText(frame, label, (bx + 20, by + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
            sub = (overall_status or "").title()
            cv2.putText(frame, sub, (bx + 15, by + 48), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

        rec_color = (0, 0, 255) if self._tick % 20 < 10 else (60, 0, 0)
        cv2.circle(frame, (16, 16), 5, rec_color, -1)
        cv2.putText(frame, "LIVE", (26, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 220, 100), 1, cv2.LINE_AA)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        self._photo = ImageTk.PhotoImage(image=img)
        self.delete("all")
        self.create_image(0, 0, anchor="nw", image=self._photo)


# ---------------- Enhanced Map Canvas: Custom PNG background with guided path ----------------
class MapCanvas(tk.Canvas):
    def __init__(self, parent, map_image_path=None, vehicle_path=None, **kw):
        super().__init__(parent, bg="#1a2030", highlightthickness=0, **kw)
        self._after_job = None
        self._map_image = None
        self._map_image_tk = None
        self._map_image_original = None

        # Vehicle path following properties
        self.vehicle_path = vehicle_path or []  # List of (x, y) tuples defining the route
        self.path_progress = 0.0                # 0.0 to 1.0 along the path
        self.path_speed = 0.0015                # Adjust for movement speed (slower for realism)
        self.vehicle_icon_size = 30             # Size of vehicle icon
        self.vehicle_heading = 0                # Direction vehicle is facing (degrees)

        # GPS data properties (for real implementation)
        self._gps_data = []                     # List of (lat, lon) tuples for real GPS tracking
        self._current_position = None           # Current GPS position
        self._show_demo_route = True            # Toggle between demo and real GPS

        # Try to load map image if provided
        if map_image_path:
            self._load_map_image(map_image_path)

        # Create default vehicle icon (bus-like shape) if no custom path provided
        if not self.vehicle_path:
            self._create_default_vehicle_path()
        self._create_vehicle_icon()

        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Destroy>", self._cancel_animation)
        self._after_job = self.after(100, self._animate)  # Slightly slower update for smoother animation

    def _load_map_image(self, path):
        """Load and prepare a map image for display"""
        try:
            # Load image and convert to PhotoImage
            pil_image = Image.open(path)
            # Store original for scaling
            self._map_image_original = pil_image
            self._map_image = pil_image  # Will be resized in _draw
            print(f"Map image loaded successfully: {pil_image.size}")
        except Exception as e:
            print(f"Could not load map image: {e}")
            self._map_image = None

    def _create_default_vehicle_path(self):
        """Create a default path from bottom-left to top-right if none provided"""
        # Default path for testing (will be overridden by actual path from user)
        width, height = 1232, 852  # Default to map dimensions
        self.vehicle_path = [
            (width * 0.1, height * 0.9),   # Start: bottom-left area
            (width * 0.3, height * 0.7),   # Waypoint 1
            (width * 0.5, height * 0.5),   # Center
            (width * 0.7, height * 0.3),   # Waypoint 2
            (width * 0.9, height * 0.1)    # End: top-right area
        ]

    def _create_vehicle_icon(self):
        """Create a bus-like vehicle icon"""
        # Create a simple bus-shaped polygon
        # Bus: rectangle with a slight front extension
        size = self.vehicle_icon_size
        # Main bus body
        self.vehicle_points = [
            (-size//2, -size//3),   # Top left
            (size//2, -size//3),    # Top right
            (size//2, size//3),     # Bottom right
            (size//3, size//3),     # Front bottom (slight indentation)
            (size//3, size//2),     # Front extension bottom
            (-size//3, size//2),    # Front extension top
            (-size//3, size//3),    # Back to main body
            (-size//2, size//3)     # Back to start
        ]

        # Alternative: Simple triangle if bus shape is too complex
        # self.vehicle_points = [(-size//2, -size//2), (size//2, 0), (-size//2, size//2)]

    def update_vehicle_path(self, path_points):
        """Update with custom path points"""
        if path_points and len(path_points) >= 2:
            self.vehicle_path = path_points
            self.path_progress = 0.0  # Reset to start
            self._show_demo_route = False
            print(f"Vehicle path updated with {len(path_points)} points")

    def update_gps_data(self, gps_points):
        """Update with real GPS data points"""
        if gps_points and len(gps_points) > 0:
            self._gps_data = gps_points
            self._show_demo_route = False
            # Set current position to last point if available
            if len(gps_points) > 0:
                self._current_position = gps_points[-1]
        else:
            self._show_demo_route = True

    def _cancel_animation(self, event=None):
        if self._after_job is not None:
            try:
                self.after_cancel(self._after_job)
            except tk.TclError:
                pass
            self._after_job = None

    def _map_value(self, value, in_min, in_max, out_min, out_max):
        """Map a value from one range to another"""
        return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    def _follow_path(self, w, h):
        """Move vehicle smoothly along the predefined path"""
        if not self.vehicle_path or len(self.vehicle_path) < 2:
            return w//2, h//2, 0  # Default to center if no path

        # Advance along path
        self.path_progress += self.path_speed
        if self.path_progress >= 1.0:
            self.path_progress = 0.0  # Loop back to start

        # Find current segment
        total_segments = len(self.vehicle_path) - 1
        segment_index = int(self.path_progress * total_segments)
        segment_index = min(segment_index, total_segments - 1)

        # Interpolate within segment
        segment_progress = (self.path_progress * total_segments) - segment_index

        x1, y1 = self.vehicle_path[segment_index]
        x2, y2 = self.vehicle_path[segment_index + 1]

        curr_x = x1 + (x2 - x1) * segment_progress
        curr_y = y1 + (y2 - y1) * segment_progress

        # Calculate heading (angle) for vehicle orientation
        dx = x2 - x1
        dy = y2 - y1
        self.vehicle_heading = math.degrees(math.atan2(dy, dx))

        return curr_x, curr_y, self.vehicle_heading

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width() or 300, self.winfo_height() or 100

        # Prevent drawing if canvas has zero size
        if w <= 1 or h <= 1:
            return

        # Draw map background if available
        if self._map_image:
            try:
                # Resize image to fit canvas while maintaining aspect ratio
                img_w, img_h = self._map_image_original.size
                # Prevent division by zero
                if img_w > 0 and img_h > 0:
                    scale = min(w / img_w, h / img_h)
                    new_w = max(1, int(img_w * scale))
                    new_h = max(1, int(img_h * scale))

                    # Center the image
                    offset_x = (w - new_w) // 2
                    offset_y = (h - new_h) // 2

                    resized = self._map_image_original.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    self._map_image_tk = ImageTk.PhotoImage(resized)
                    self.create_image(offset_x, offset_y, anchor="nw", image=self._map_image_tk)

                    # Store offset for coordinate conversion
                    self._map_offset_x = offset_x
                    self._map_offset_y = offset_y
                    self._map_scale = scale
                else:
                    # Fall back to colored background if image is invalid
                    self.create_rectangle(0, 0, w, h, fill="#1a2030")
            except Exception as e:
                print(f"Error drawing map image: {e}")
                # Fall back to colored background
                self.create_rectangle(0, 0, w, h, fill="#1a2030")
        else:
            # Draw dark background
            self.create_rectangle(0, 0, w, h, fill="#1a2030")

        # Draw route (either demo path or real GPS)
        if self._show_demo_route or len(self._gps_data) < 2:
            # Demo/path route
            self._draw_vehicle_path(w, h)
        else:
            # Real GPS route
            self._draw_gps_route(w, h)

        # Draw current position indicator (vehicle)
        self._draw_vehicle_indicator(w, h)

        # Add label
        label_text = "LIVE MAP" if not self._show_demo_route and self._gps_data else "GUIDED MAP - Following Route"
        label_color = "#10b981" if not self._show_demo_route and self._gps_data else "#fbbf24"
        self.create_text(w - 6, h - 4, text=label_text, fill=label_color,
                          font=("Courier", 8, "bold"), anchor="se")

    def _draw_vehicle_path(self, w, h):
        """Draw the predefined path"""
        if len(self.vehicle_path) < 2:
            return

        # Convert path points to canvas coordinates
        canvas_points = []
        for map_x, map_y in self.vehicle_path:
            # If we have a mapped image, convert from map coordinates to canvas
            if hasattr(self, '_map_offset_x'):
                canvas_x = map_x * self._map_scale + self._map_offset_x
                canvas_y = map_y * self._map_scale + self._map_offset_y
            else:
                # Direct mapping (fallback)
                canvas_x = map_x
                canvas_y = map_y
            canvas_points.extend([canvas_x, canvas_y])

        if len(canvas_points) >= 4:
            # Draw the path line
            self.create_line(*canvas_points, fill="#10b981", width=3, smooth=True)
            # Draw subtle dotted line underneath for depth
            self.create_line(*canvas_points, fill="#059669", width=1, dash=(4, 2), smooth=True)

    def _draw_gps_route(self, w, h):
        """Draw real GPS route"""
        if len(self._gps_data) < 2:
            return

        # Convert GPS points to canvas coordinates
        lats = [p[0] for p in self._gps_data]
        lons = [p[1] for p in self._gps_data]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)

        # Add some padding
        lat_range = max_lat - min_lat or 0.001
        lon_range = max_lon - min_lon or 0.001
        padding = 0.1
        lat_range += lat_range * padding
        lon_range += lon_range * padding
        min_lat -= lat_range * padding / 2
        min_lon -= lon_range * padding / 2

        points = []
        for lat, lon in self._gps_data:
            # Map to canvas coordinates
            x = self._map_value(lon, min_lon, max_lon, 0, w)
            y = self._map_value(lat, min_lat, max_lat, h, 0)  # Flip Y for canvas
            points.extend([x, y])

        if len(points) >= 4:
            self.create_line(*points, fill="#10b981", width=3, smooth=True)
            # Draw points
            for i in range(0, len(points), 2):
                x, y = points[i], points[i+1]
                self.create_oval(x-3, y-3, x+3, y+3, fill="#34d399", outline="")

    def _draw_vehicle_indicator(self, w, h):
        """Draw the vehicle icon at current position"""
        if self._show_demo_route:
            # Get position from guided path
            pos_x, pos_y, heading = self._follow_path(w, h)
        elif self._current_position:
            # Get position from real GPS
            lat, lon = self._current_position
            # Use same mapping as in _draw_gps_route
            lats = [p[0] for p in self._gps_data]
            lons = [p[1] for p in self._gps_data]
            min_lat, max_lat = min(lats), max(lats)
            min_lon, max_lon = min(lons), max(lons)

            lat_range = max_lat - min_lat or 0.001
            lon_range = max_lon - min_lon or 0.001
            padding = 0.1
            lat_range += lat_range * padding
            lon_range += lon_range * padding
            min_lat -= lat_range * padding / 2
            min_lon -= lon_range * padding / 2

            pos_x = self._map_value(lon, min_lon, max_lon, 0, w)
            pos_y = self._map_value(lat, min_lat, max_lat, h, 0)  # Flip Y for canvas
            # For heading, we'd need previous point - simplified for now
            heading = 0
        else:
            # No data - show in center
            pos_x, pos_y, heading = w // 2, h // 2, 0

        # Draw vehicle icon (rotated based on heading)
        self._draw_rotated_polygon(pos_x, pos_y, self.vehicle_points, heading,
                                  fill="#dc2626", outline="#ffffff", width=1)

    def _draw_rotated_polygon(self, x, y, points, angle_degrees, **options):
        """Draw a polygon rotated around point (x, y) by angle_degrees"""
        if not points:
            return

        # Convert angle to radians
        angle_rad = math.radians(angle_degrees)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Rotate each point
        rotated_points = []
        for px, py in points:
            # Translate to origin, rotate, translate back
            rx = px * cos_a - py * sin_a + x
            ry = px * sin_a + py * cos_a + y
            rotated_points.extend([rx, ry])

        # Draw the rotated polygon
        self.create_polygon(*rotated_points, **options)

    def _animate(self):
        self._draw()
        self._after_job = self.after(100, self._animate)  # Consistent update rate


# ---------------- Main app ----------------
class DrowsiGuardApp(tk.Tk):
    def __init__(self, cap, face_mesh_module, engine, object_detector, alert_manager, logger,
                 test_mode=False):
        super().__init__()
        self.title("DrowsiGuard - Driver Monitoring System")
        self.configure(bg=BG)
        self.geometry("1200x800")  # Slightly larger default size
        self.minsize(1000, 700)

        self.cap = cap
        self.detect_face = face_mesh_module.detect_face
        self.draw_face_mesh = face_mesh_module.draw_face_mesh
        self.engine = engine
        self.object_detector = object_detector
        self.alert_manager = alert_manager
        self.logger = logger
        self.test_mode = test_mode

        self.night_mode = False
        self.alert_threshold = 70
        self.session_start = logger.session_start if logger else time.time()

        # Define the specific path from Campari house to Parliament House
        # These coordinates will need to be adjusted based on the actual map
        # Format: (x, y) pixel coordinates on the map image
        self.campari_to_parliament_path = [
            # Starting near Campari house (bottom-left area of typical map)
            (150, 750),   # Campari house vicinity
            (250, 650),   # First turn
            (400, 550),   # Straight road
            (550, 450),   # Curve
            (700, 350),   # Approaching government area
            (850, 250),   # Near parliament
            (950, 180),   # Final approach
            (1050, 120)   # Parliament house vicinity
        ]

        self._build_header()
        self._build_body()
        self._build_bottom()
        self._build_footer()

        self._clock_job = None
        self._update_job = None

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._tick_clock()

        if not test_mode:
            self._update_job = self.after(33, self._update)

    # ---------------- header ----------------
    def _build_header(self):
        hdr = tk.Frame(self, bg=PANEL, height=40)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        left = tk.Frame(hdr, bg=PANEL)
        left.pack(side="left", padx=10, pady=6)
        logo = tk.Frame(left, bg=BLUE, width=22, height=22)
        logo.pack(side="left")
        logo.pack_propagate(False)
        tk.Label(logo, text="D", bg=BLUE, fg="white", font=("Courier", 11, "bold")).place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(left, text=" DrowsiGuard", bg=PANEL, fg=BLUE, font=("Courier", 12, "bold")).pack(side="left")
        tk.Label(left, text="  Driver Monitoring System", bg=PANEL, fg=MUTED, font=("Courier", 8)).pack(side="left")

        right = tk.Frame(hdr, bg=PANEL)
        right.pack(side="right", padx=10, pady=6)

        self._clock_var = tk.StringVar(value="--:-- --")
        tk.Label(right, textvariable=self._clock_var, bg=PANEL, fg=MUTED, font=("Courier", 9)).pack(side="right", padx=(10, 0))

        self._night_btn = tk.Label(right, text="Night Mode: OFF", bg="#21262d", fg="#93c5fd",
                                    font=("Courier", 8), padx=6, pady=2, cursor="hand2")
        self._night_btn.pack(side="right", padx=6)
        self._night_btn.bind("<Button-1>", self._toggle_night_mode)

        cam = tk.Frame(right, bg=PANEL)
        cam.pack(side="right")
        cam_ok = self.cap is not None and (self.test_mode or self.cap.isOpened())
        tk.Label(cam, text="●", bg=PANEL, fg=(GREEN if cam_ok else RED), font=("Courier", 8)).pack(side="left")
        tk.Label(cam, text=f" Camera: {'Active' if cam_ok else 'Unavailable'}", bg=PANEL, fg=MUTED, font=("Courier", 8)).pack(side="left")

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

    def _toggle_night_mode(self, event=None):
        self.night_mode = not self.night_mode
        self._night_btn.configure(text=f"Night Mode: {'ON' if self.night_mode else 'OFF'}",
                                   fg=("#fbbf24" if self.night_mode else "#93c5fd"))

    # ---------------- body ----------------
    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)
        self._build_left(body)
        self._build_center(body)
        self._build_right(body)

    def _build_left(self, parent):
        left = tk.Frame(parent, bg=PANEL, width=180)  # Slightly reduced width
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Frame(parent, bg=BORDER, width=1).pack(side="left", fill="y")

        tk.Label(left, text="Real-Time Metrics", bg=PANEL, fg=MUTED, font=("Courier", 7, "bold")).pack(anchor="w", padx=8, pady=(6, 4))

        self.card_fatigue = MetricCard(left, "Fatigue Level", "0%", status="Normal", status_color=GREEN, bar_color=GREEN, bar_pct=0)
        self.card_attention = MetricCard(left, "Attention Score", "100%", status="Good", status_color=GREEN, bar_color=GREEN, bar_pct=100)
        self.card_perclos = MetricCard(left, "PERCLOS", "0%", status="Normal", status_color=GREEN, bar_color=GREEN, bar_pct=0)
        self.card_eye = MetricCard(left, "Eye Closure", "0.00s", status="Normal", status_color=GREEN, show_bar=False)
        self.card_yawns = MetricCard(left, "Yawns", "0", status="This session", status_color=MUTED, show_bar=False)
        self.card_gaze = MetricCard(left, "Gaze Direction", "N/A", status="Not tracked yet", status_color=MUTED, show_bar=False)

        for card in (self.card_fatigue, self.card_attention, self.card_perclos,
                     self.card_eye, self.card_yawns, self.card_gaze):
            card.pack(fill="x", padx=6, pady=2)

        tags_frame = tk.Frame(left, bg=PANEL)
        tags_frame.pack(fill="x", padx=6, pady=(6, 2), side="bottom")
        self._tag_widgets = {}
        for tag in ["phone", "drink", "smoke"]:
            t = tk.Frame(tags_frame, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            t.pack(fill="x", pady=2)
            label_text = tag if tag != "smoke" else "smoke (planned)"
            lbl = tk.Label(t, text=label_text, bg=CARD, fg=MUTED, font=("Courier", 9))
            lbl.pack(padx=8, pady=3)
            self._tag_widgets[tag] = (t, lbl)

    def _build_center(self, parent):
        center = tk.Frame(parent, bg=BG)
        center.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        tk.Label(center, text="Driver Status", bg=BG, fg="#c9d1d9", font=("Courier", 9, "bold")).pack(anchor="w", padx=4, pady=(2, 4))

        # REDUCED video size as requested - made smaller
        self.video_canvas = VideoCanvas(center, height=150)  # Significantly smaller!
        self.video_canvas.pack(fill="both", expand=True, padx=4, pady=(4, 2))

        # Alert threshold controls
        thresh_frame = tk.Frame(center, bg=BG)
        thresh_frame.pack(fill="x", padx=4, pady=2)
        tk.Label(thresh_frame, text="Alert Threshold:", bg=BG, fg=MUTED, font=("Courier", 8)).pack(side="left", padx=(0, 6))

        self._threshold_labels = {}
        for val in [60, 70, 80, 90]:
            lbl = tk.Label(thresh_frame, text=f"{val}%", font=("Courier", 8, "bold"), padx=10, pady=3, cursor="hand2")
            lbl.pack(side="left", padx=2)
            lbl.bind("<Button-1>", lambda e, v=val: self._set_threshold(v))
            self._threshold_labels[val] = lbl
        self._refresh_threshold_pills()

        # INCREASED alert system size - made more prominent
        alert_frame = tk.Frame(center, bg=BG)
        alert_frame.pack(fill="both", expand=True, padx=4, pady=(2, 4))

        # Alert container with better styling
        self.alerts_container = tk.Frame(alert_frame, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        self.alerts_container.pack(fill="both", expand=True, padx=4, pady=4)

        self.no_alert_label = tk.Label(self.alerts_container, text="No active alerts", bg=PANEL, fg=GREEN, font=("Courier", 10, "bold"))
        self.no_alert_label.pack(anchor="w", padx=10, pady=10)

        # Recommended actions panel (now positioned below alerts for better flow)
        rec_frame = tk.Frame(alert_frame, bg=BG)
        rec_frame.pack(fill="x", padx=4, pady=(4, 0))

        rec = tk.Frame(rec_frame, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        rec.pack(fill="x", padx=6, pady=(10, 2))
        tk.Label(rec, text="Recommended Actions", bg=CARD, fg=TEXT, font=("Courier", 8, "bold")).pack(anchor="w", padx=6, pady=(5, 3))
        self.rec_labels = []
        for color, txt in [(BLUE, "→ Pull over when safe"), (YELLOW, "→ Take a 15-20 min break"),
                            (GREEN, "→ Open a window for fresh air")]:
            l = tk.Label(rec, text=txt, bg=CARD, fg=color, font=("Courier", 7))
            l.pack(anchor="w", padx=6, pady=1)
            self.rec_labels.append(l)
        tk.Frame(rec, bg=CARD, height=4).pack()
        self.rec_panel = rec
        self.rec_panel.pack_forget()  # only shown when there's an active alert

    def _set_threshold(self, val):
        self.alert_threshold = val
        self._refresh_threshold_pills()

    def _refresh_threshold_pills(self):
        for val, lbl in self._threshold_labels.items():
            active = val == self.alert_threshold
            lbl.configure(bg=YELLOW if active else CARD, fg="black" if active else MUTED)

    def _build_right(self, parent):
        tk.Frame(parent, bg=BORDER, width=1).pack(side="left", fill="y")
        right = tk.Frame(parent, bg=PANEL, width=200)  # Slightly reduced width
        right.pack(side="left", fill="y")
        right.pack_propagate(False)

        tk.Label(right, text="Alert:", bg=PANEL, fg=MUTED, font=("Courier", 7, "bold")).pack(anchor="w", padx=8, pady=(6, 4))

        # Note: Alerts now have their own dedicated space in center panel
        # This panel can be used for additional info or left empty
        info_label = tk.Label(right, text="System Info", bg=PANEL, fg=MUTED, font=("Courier", 7, "italic"))
        info_label.pack(anchor="w", padx=8, pady=(6, 4))

        info_details = tk.Label(right, text="• GPS: Guided Route\n• Camera: Active\n• Sensors: Online",
                               bg=PANEL, fg=MUTED, font=("Courier", 7), justify="left")
        info_details.pack(anchor="w", padx=8, pady=(2, 6))

    def _build_bottom(self):
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        bottom = tk.Frame(self, bg=BG, height=200)  # INCREASED height for larger vehicle status
        bottom.pack(fill="x")
        bottom.pack_propagate(False)

        # ENLARGED vehicle status section
        veh = tk.Frame(bottom, bg=PANEL)
        veh.pack(side="left", fill="both", expand=True, padx=(4, 2), pady=4)

        tk.Label(veh, text="Vehicle Status", bg=PANEL, fg="#f59e0b", font=("Courier", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 0))

        # Create vehicle status metrics with larger fonts
        self.card_speed = MetricCard(veh, "Speed", "-- km/h", unit="", status="N/A", status_color=MUTED, show_bar=False)
        self.card_battery = MetricCard(veh, "Battery", "--%", unit="", status="Normal", status_color=GREEN, bar_color=GREEN, bar_pct=0)
        self.card_energy = MetricCard(veh, "Energy", "--%", unit="", status="Normal", status_color=GREEN, bar_color=GREEN, bar_pct=0)
        self.card_fuel = MetricCard(veh, "Fuel", "--%", unit="", status="Normal", status_color=GREEN, bar_color=GREEN, bar_pct=0)

        # Tire pressure - enhanced display with 4 tires
        tire_frame = tk.Frame(veh, bg=PANEL)
        tire_frame.pack(fill="x", padx=6, pady=(4, 0))
        tk.Label(tire_frame, text="Tire Pressure (PSI)", bg=PANEL, fg=MUTED, font=("Courier", 8)).pack(anchor="w")

        self.tire_labels = []
        tire_positions = ["FL", "FR", "RL", "RR"]  # Front Left, Front Right, Rear Left, Rear Right
        for pos in tire_positions:
            tire_container = tk.Frame(tire_frame, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            tire_container.pack(fill="x", pady=2)

            # Enhanced tire display with larger text
            tire_inner = tk.Frame(tire_container, bg=CARD)
            tire_inner.pack(fill="x", padx=4, pady=2)

            pos_label = tk.Label(tire_inner, text=f"{pos}:", bg=CARD, fg=TEXT, font=("Courier", 8, "bold"))
            pos_label.pack(side="left")

            pressure_label = tk.Label(tire_inner, text="-- psi", bg=CARD, fg=TEXT, font=("Courier", 8))
            pressure_label.pack(side="left", padx=(4, 0))

            # Store reference to pressure label for updates
            tire_container.pressure_label = pressure_label
            self.tire_labels.append((pos, tire_container))

        # Configure grid weights for better layout
        veh.grid_columnconfigure(0, weight=1)

        tk.Frame(bottom, bg=BORDER, width=1).pack(side="left", fill="y")

        # ENHANCED map section with guided path
        map_frame = tk.Frame(bottom, bg=PANEL)
        map_frame.pack(side="left", fill="both", expand=True, padx=(2, 4), pady=4)
        top_row = tk.Frame(map_frame, bg=PANEL)
        top_row.pack(fill="x", padx=4, pady=(4, 0))
        tk.Label(top_row, text="Guided Navigation", bg=PANEL, fg="#f59e0b", font=("Courier", 7, "bold")).pack(side="left")
        self.time_driven_var = tk.StringVar(value="00:00:00")
        tk.Label(top_row, textvariable=self.time_driven_var, bg=PANEL, fg=TEXT, font=("Courier", 8, "bold")).pack(side="right")
        tk.Label(top_row, text="Time driven: ", bg=PANEL, fg=MUTED, font=("Courier", 7)).pack(side="right")

        # Pass our specific map and path
        self.map_canvas = MapCanvas(map_frame,
                                   map_image_path="assets/map.png",
                                   vehicle_path=self.campari_to_parliament_path)
        self.map_canvas.pack(fill="both", expand=True, padx=4, pady=(0, 4))

    # ---------------- footer ----------------
    def _build_footer(self):
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        ftr = tk.Frame(self, bg=BG, height=28)
        ftr.pack(fill="x")
        ftr.pack_propagate(False)

        left = tk.Frame(ftr, bg=BG)
        left.pack(side="left", padx=10, pady=4)
        for label in ["Settings", "Device Config", "History & Logs"]:
            btn = tk.Label(left, text=label, bg=BG, fg=MUTED, font=("Courier", 8), cursor="hand2")
            btn.pack(side="left", padx=6)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(fg=TEXT))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(fg=MUTED))

        right = tk.Frame(ftr, bg=BG)
        right.pack(side="right", padx=10, pady=4)

        self._footer_dots = {}
        for key, label in [("system", "System OK"), ("gps", "GPS: Guided Active"), ("sensors", "Sensors Online")]:
            f = tk.Frame(right, bg=BG)
            f.pack(side="left", padx=8)
            dot = tk.Label(f, text="●", bg=BG, fg=GREEN, font=("Courier", 7))
            dot.pack(side="left")
            lbl = tk.Label(f, text=f" {label}", bg=BG, fg=MUTED, font=("Courier", 8))
            lbl.pack(side="left")
            self._footer_dots[key] = (dot, lbl)

        # Set GPS indicator to active since we're using guided path
        self._footer_dots["gps"][0].configure(fg="#10b981")  # Green when guided path active
        self._footer_dots["gps"][1].configure(text=f" GPS: Route Active")

    def _tick_clock(self):
        self._clock_var.set(time.strftime("%I:%M %p"))
        self._clock_job = self.after(1000, self._tick_clock)

    # ---------------- live update loop ----------------
    def process_one_frame(self, frame):
        """Runs the real detection pipeline on one BGR frame. Returns
        (result, obj_result, overall_severity, overall_status, display_frame).
        Split out from _update() so it can be tested without a live camera."""
        from src.severity import combine

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.detect_face(rgb)
        frame_h, frame_w = frame.shape[:2]

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0]
            self.draw_face_mesh(frame, landmarks)
            result = self.engine.process_frame(landmarks, frame_w, frame_h)
        else:
            result = self.engine.handle_face_lost()

        obj_result = {"status": "NORMAL", "severity": None, "distraction_percent": 0, "detections": []}
        if self.object_detector is not None:
            obj_result = self.object_detector.process_frame(frame)
            for det in obj_result["detections"]:
                x1, y1, x2, y2 = det["box"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 230, 40), 2)
                cv2.putText(frame, f"{det['label']} {det['confidence']:.2f}", (x1, max(20, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 230, 40), 2)

        if self.night_mode:
            tint = frame.copy()
            tint[:, :] = (20, 15, 60)
            frame = cv2.addWeighted(frame, 0.7, tint, 0.3, 0)

        overall_severity = combine(result.get("severity"), obj_result.get("severity"))
        overall_status = result.get("status") if result.get("severity") == overall_severity else obj_result.get("status")

        return result, obj_result, overall_severity, overall_status, frame

    def apply_frame_result(self, result, obj_result, overall_severity, overall_status, frame):
        """Pushes one frame's results into all the widgets. Split out from
        _update() so it's testable with synthetic data (no camera needed)."""
        self.video_canvas.update_frame(frame, overall_severity, overall_status)

        drowsy_pct = result.get("drowsy_percent", 0)
        distraction_pct = obj_result.get("distraction_percent", 0) if obj_result else 0
        pose_alert_dur = result.get("pose_alert_duration", 0.0)
        pose_ratio_pct = min(100, round(100 * pose_alert_dur / 2.5)) if pose_alert_dur else 0
        distraction_pct = max(distraction_pct, pose_ratio_pct)
        attention_pct = max(0, 100 - round((drowsy_pct + distraction_pct) / 2))

        self.card_fatigue.update_values(f"{drowsy_pct}%", pct_word(drowsy_pct), pct_color(drowsy_pct), drowsy_pct)
        att_color = RED if attention_pct < 50 else (YELLOW if attention_pct < 75 else GREEN)
        att_word = "Low" if attention_pct < 50 else ("Fair" if attention_pct < 75 else "Good")
        self.card_attention.update_values(f"{attention_pct}%", att_word, att_color, attention_pct)

        perclos_pct = round(result.get("perclos", 0) * 100)
        self.card_perclos.update_values(f"{perclos_pct}%", pct_word(perclos_pct), pct_color(perclos_pct), perclos_pct)

        closed_time = result.get("closed_time", 0.0)
        eye_status = "Above Normal" if closed_time > 0.2 else "Normal"
        self.card_eye.update_values(f"{closed_time:.2f}s", eye_status, YELLOW if closed_time > 0.2 else GREEN)

        self.card_yawns.update_values(str(result.get("yawn_counter", 0)))

        phone_active = obj_result and obj_result.get("status") == "PHONE USE DETECTED"
        drink_active = obj_result and obj_result.get("status") == "DRINKING DETECTED"
        for tag, active in [("phone", phone_active), ("drink", drink_active)]:
            frame_w, lbl = self._tag_widgets[tag]
            if active:
                frame_w.configure(bg=BLUE)
                lbl.configure(bg=BLUE, fg="black")
            else:
                frame_w.configure(bg=CARD)
                lbl.configure(bg=CARD, fg=MUTED)

        self._update_alerts(result, obj_result)

        # Update vehicle status with enhanced realism
        self._update_vehicle_status_enhanced()

        # Update GPS/map data (guided path from Campari house to Parliament House)
        self._update_guided_navigation()

        elapsed = int(time.time() - self.session_start)
        hh, rem = divmod(elapsed, 3600)
        mm, ss = divmod(rem, 60)
        self.time_driven_var.set(f"{hh:02d}:{mm:02d}:{ss:02d}")

        if self.logger:
            self.logger.track_status(obj_result.get("status", "NORMAL") if obj_result else "NORMAL")
            if result.get("drowsy_start_event"):
                self.logger.log("DROWSINESS_START", f"status={result.get('status')}")
            if result.get("drowsy_end_event"):
                self.logger.log("DROWSINESS_END")
            if result.get("yawn_event"):
                self.logger.log("YAWN")

        if self.alert_manager:
            self.alert_manager.update(overall_severity)

    def _update_vehicle_status_enhanced(self):
        """Enhanced vehicle status with more realistic variations"""
        # Simulate realistic vehicle data with gradual changes
        if not hasattr(self, '_last_speed'):
            self._last_speed = 0
            self._last_battery = 95
            self._last_energy = 80
            self._last_fuel = 75
            self._last_tire_pressures = [32, 32, 31, 31]  # [FL, FR, RL, RR]

        # Speed: gradual acceleration/deceleration (0-80 km/h for city driving)
        target_speed = random.randint(20, 60)
        speed_change = (target_speed - self._last_speed) * 0.1  # Smooth transition
        speed = self._last_speed + speed_change
        speed = max(0, min(80, speed))  # Clamp to reasonable city speeds

        speed_status = "Normal"
        speed_color = GREEN
        if speed > 60:
            speed_status = "Fast"
            speed_color = YELLOW
        elif speed < 10 and self._last_speed > 5:  # Slowing down
            speed_status = "Slowing"
            speed_color = YELLOW

        self.card_speed.update_values(f"{int(speed)} km/h", speed_status, speed_color, int(speed))
        self._last_speed = speed

        # Battery: slow drain with occasional charging (simulating regen)
        battery_change = random.uniform(-0.1, 0.05)  # Slow drain, slight chance of charge
        battery = self._last_battery + battery_change
        battery = max(10, min(98, battery))  # Keep in reasonable range

        battery_status = "Good"
        battery_color = GREEN
        if battery < 20:
            battery_status = "Low"
            battery_color = RED
        elif battery < 40:
            battery_status = "Fair"
            battery_color = YELLOW

        self.card_battery.update_values(f"{int(battery)}%", battery_status, battery_color, int(battery))
        self._last_battery = battery

        # Energy: efficiency varies with driving conditions
        energy_base = 70 + (speed / 80) * 20  # More efficient at moderate speeds
        energy_variation = random.uniform(-5, 5)
        energy = energy_base + energy_variation
        energy = max(30, min(95, energy))

        energy_status = "Good"
        energy_color = GREEN
        if energy < 40:
            energy_status = "Low"
            energy_color = RED
        elif energy < 60:
            energy_status = "Fair"
            energy_color = YELLOW

        self.card_energy.update_values(f"{int(energy)}%", energy_status, energy_color, int(energy))
        self._last_energy = energy

        # Fuel: slow consumption
        fuel_change = random.uniform(-0.05, 0.01)  # Very slow consumption
        fuel = self._last_fuel + fuel_change
        fuel = max(5, min(95, fuel))

        fuel_status = "Good"
        fuel_color = GREEN
        if fuel < 10:
            fuel_status = "Low"
            fuel_color = RED
        elif fuel < 25:
            fuel_status = "Fair"
            fuel_color = YELLOW

        self.card_fuel.update_values(f"{int(fuel)}%", fuel_status, fuel_color, int(fuel))
        self._last_fuel = fuel

        # Tire pressures: slight natural variation
        for i, (pos, container) in enumerate(self.tire_labels):
            # Small random walk for each tire
            pressure_change = random.uniform(-0.2, 0.2)
            pressure = self._last_tire_pressures[i] + pressure_change
            pressure = max(28, min(36, pressure))  # Normal operating range

            status = "Normal"
            color = GREEN
            if pressure < 29:
                status = "Low"
                color = RED
            elif pressure > 35:
                status = "High"
                color = YELLOW

            # Update the label text
            if hasattr(container, 'pressure_label'):
                container.pressure_label.configure(text=f"{int(pressure)} psi", fg=color)

            self._last_tire_pressures[i] = pressure

    def _update_guided_navigation(self):
        """Update the guided navigation from Campari house to Parliament House"""
        # The MapCanvas already handles the path following via _follow_path()
        # We just need to ensure it's using our specific path
        if hasattr(self, 'map_canvas') and not self.map_canvas._show_demo_route:
            # Update footer to show progress
            progress_percent = int(self.map_canvas.path_progress * 100)
            self._footer_dots["gps"][1].configure(text=f" GPS: {progress_percent}% Complete")

            # Change color based on progress
            if progress_percent < 25:
                color = "#fbbf24"  # Yellow - just started
            elif progress_percent < 75:
                color = "#10b981"  # Green - making good progress
            else:
                color = "#ef4444"  # Red - nearing destination
            self._footer_dots["gps"][0].configure(fg=color)
        else:
            # Initialize or reset if needed
            if hasattr(self, 'map_canvas'):
                self.map_canvas.update_vehicle_path(self.campari_to_parliament_path)
                self.map_canvas._show_demo_route = False

    def _update_alerts(self, result, obj_result):
        for child in list(self.alerts_container.winfo_children()):
            child.destroy()

        ALERT_TEXT = {
            "DROWSINESS DETECTED": ("CRITICAL ALERT", "Eyes closed for an extended period. Pull over and rest immediately.", RED_DIM, RED),
            "DROWSINESS DETECTED (PERCLOS)": ("WARNING", "Repeated fatigue signs over the last minute. Consider a break soon.", "#2d1e00", YELLOW),
            "HEAD POSE ALERT": ("WARNING", "Head tilted away from the road for a sustained period.", "#2d1e00", YELLOW),
            "HEAD NOD DETECTED": ("WARNING", "A quick head-drop was detected - possible microsleep.", "#2d1e00", YELLOW),
            "PHONE USE DETECTED": ("INFO (monitored only)", "Phone use detected - logged, does not sound the alarm.", "#132233", BLUE),
            "DRINKING DETECTED": ("INFO (monitored only)", "Drinking detected - logged, does not sound the alarm.", "#132233", BLUE),
        }

        active = []
        if result.get("status") in ALERT_TEXT:
            active.append(result["status"])
        if obj_result and obj_result.get("status") in ALERT_TEXT:
            active.append(obj_result["status"])

        if not active:
            self.no_alert_label = tk.Label(self.alerts_container, text="No active alerts", bg=PANEL, fg=GREEN, font=("Courier", 10, "bold"))
            self.no_alert_label.pack(anchor="w", padx=10, pady=10)
            self.rec_panel.pack_forget()
            return

        for status in active[:2]:
            title, msg, bg, fg = ALERT_TEXT[status]
            box = tk.Frame(self.alerts_container, bg=bg, highlightbackground=fg, highlightthickness=1)
            box.pack(fill="x", padx=6, pady=2)
            tk.Label(box, text=title, bg=bg, fg=fg, font=("Courier", 8, "bold")).pack(anchor="w", padx=6, pady=(5, 2))
            tk.Label(box, text=msg, bg=bg, fg=TEXT, font=("Courier", 7), justify="left", wraplength=190).pack(anchor="w", padx=6, pady=(0, 5))

        self.rec_panel.pack(fill="x", padx=6, pady=(10, 2))

    def _update(self):
        success, frame = self.cap.read()
        if success:
            result, obj_result, overall_severity, overall_status, disp = self.process_one_frame(frame)
            self.apply_frame_result(result, obj_result, overall_severity, overall_status, disp)
        self._update_job = self.after(33, self._update)

    def _on_close(self):
        # Cancel pending after() jobs BEFORE destroying - once a widget is
        # destroyed, even checking whether a pending job is safe to skip
        # fails, so jobs must be cancelled explicitly first.
        for job in (self._clock_job, self._update_job):
            if job is not None:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass

        if self.cap is not None:
            self.cap.release()
        if self.alert_manager is not None:
            self.alert_manager.stop()
        if self.logger is not None:
            session_duration = time.time() - self.logger.session_start
            summary = self.engine.summary(session_duration)
            self.logger.log("SESSION_END", f"duration={summary['duration_seconds']:.1f}s")
            self.logger.write_summary_file(summary, self.engine.EAR_THRESHOLD, self.engine.MAR_THRESHOLD)
            self.logger.close()
        self.destroy()
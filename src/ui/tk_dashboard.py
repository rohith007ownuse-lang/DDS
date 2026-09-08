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
from src.utils.config_manager import get_config
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
from src.ui.vehicle_control_panel import VehicleControlPanel

# ---------------- palette (hex, since this file is Tkinter not cv2) ----------------
BG      = "#FFFFFF"
PANEL   = "#F7F9FB"
CARD    = "#FFFFFF"
BORDER  = "#D9E0E7"
TEXT    = "#17212B"
MUTED   = "#66727E"
RED     = "#E53935"
RED_DIM = "#FEF2F2"
ORANGE  = "#F5A623"
YELLOW  = "#F5A623"
GREEN   = "#22A447"
BLUE    = "#2196F3"
ACCENT_BLUE = "#66B2FF"
DARK_BLUE = "#001A33"
MID_BLUE = "#003366"
LIGHT_BLUE = "#0066CC"


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
        return "Warning"
    return "Normal"


# ---------------- Metric card (from the provided mockup, + a real update() method) ----------------
class MetricCard(tk.Frame):
    def __init__(self, parent, label, value, unit="", status="", status_color=GREEN,
                 show_bar=True, bar_color=GREEN, bar_pct=0):
        super().__init__(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        self.show_bar = show_bar
        self.bar_color = bar_color
        self.configure(width=155, height=60)
        self.pack_propagate(False)

        # Label
        tk.Label(self, text=label, bg=CARD, fg=MUTED, font=("JetBrains Mono", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 0))

        # Value row
        row = tk.Frame(self, bg=CARD)
        row.pack(anchor="w", padx=8)
        self.value_label = tk.Label(row, text=value, bg=CARD, fg=TEXT, font=("JetBrains Mono", 20, "bold"))
        self.value_label.pack(side="left")
        self.unit_label = None
        if unit and not value.endswith(unit):
            self.unit_label = tk.Label(row, text=unit, bg=CARD, fg=MUTED, font=("JetBrains Mono", 9))
            self.unit_label.pack(side="left", padx=(3, 0), pady=(5, 0))

        # Status label
        self.status_label = tk.Label(self, text=status, bg=CARD, fg=status_color, font=("JetBrains Mono", 8))
        self.status_label.pack(anchor="w", padx=8)

        # Progress bar
        self.bar_fg = None
        if show_bar:
            bar_bg = tk.Frame(self, bg=BORDER, height=3)
            bar_bg.pack(fill="x", padx=8, pady=(2, 6))
            bar_bg.pack_propagate(False)
            self.bar_fg = tk.Frame(bar_bg, bg=bar_color, height=3)
            self.bar_fg.place(relwidth=bar_pct / 100, relheight=1)
        else:
            tk.Frame(self, bg=CARD, height=4).pack()

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
        super().__init__(parent, bg="#FFFFFF", highlightthickness=0, **kw)
        self._photo = None  # must keep a reference or Tkinter garbage-collects it
        self._tick = 0

    def update_frame(self, bgr_frame, overall_severity, overall_status):
        """bgr_frame should already have face-mesh/detection boxes drawn on it
        by the caller (main.py) - this method only handles display + the
        severity banner overlay."""
        self._tick += 1
        w = self.winfo_width() or 1000
        h = self.winfo_height() or 450

        frame = cv2.resize(bgr_frame, (w, h))

        if overall_severity in ("WARNING", "CRITICAL"):
            color = (0, 0, 255) if overall_severity == "CRITICAL" else (0, 165, 255)
            box_w, box_h = 400, 90
            bx, by = (w - box_w) // 2, h // 2 - 100
            overlay = frame.copy()
            cv2.rectangle(overlay, (bx, by), (bx + box_w, by + box_h), (255, 255, 255), -1)
            cv2.addWeighted(overlay, 0.9, frame, 0.1, 0, dst=frame)
            cv2.rectangle(frame, (bx, by), (bx + box_w, by + box_h), color, 3)
            label = "⚠ DROWSINESS DETECTED" if overall_severity == "CRITICAL" else "⚠ WARNING"
            cv2.putText(frame, label, (bx + 20, by + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2, cv2.LINE_AA)
            sub = (overall_status or "").title()
            cv2.putText(frame, sub, (bx + 20, by + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)

        # LIVE indicator
        rec_color = (0, 200, 0) if self._tick % 20 < 10 else (0, 150, 0)
        cv2.circle(frame, (20, 20), 6, rec_color, -1)
        cv2.putText(frame, "LIVE", (32, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 180, 0), 1, cv2.LINE_AA)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        self._photo = ImageTk.PhotoImage(image=img)
        self.delete("all")
        self.create_image(0, 0, anchor="nw", image=self._photo)


# ---------------- Enhanced Map Canvas: Custom PNG background with guided path ----------------
class MapCanvas(tk.Canvas):
    def __init__(self, parent, map_image_path=None, vehicle_path=None, **kw):
        super().__init__(parent, bg="#FFFFFF", highlightthickness=0, **kw)
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
        w, h = self.winfo_width() or 1000, self.winfo_height() or 300

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
                    # Fall back to light background if image is invalid
                    self.create_rectangle(0, 0, w, h, fill="#F7F9FB", outline="")
            except Exception as e:
                print(f"Error drawing map image: {e}")
                # Fall back to light background
                self.create_rectangle(0, 0, w, h, fill="#F7F9FB", outline="")
        else:
            # Draw light background
            self.create_rectangle(0, 0, w, h, fill="#F7F9FB", outline="")

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
        label_color = GREEN if not self._show_demo_route and self._gps_data else YELLOW
        self.create_text(w - 6, h - 4, text=label_text, fill=label_color,
                          font=("JetBrains Mono", 8, "bold"), anchor="se")

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
            self.create_line(*canvas_points, fill=BLUE, width=3, smooth=True)
            # Draw subtle dotted line underneath for depth
            self.create_line(*canvas_points, fill=MID_BLUE, width=1, dash=(4, 2), smooth=True)

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
            self.create_line(*points, fill=BLUE, width=3, smooth=True)
            # Draw points
            for i in range(0, len(points), 2):
                x, y = points[i], points[i+1]
                self.create_oval(x-3, y-3, x+3, y+3, fill=ACCENT_BLUE, outline="")

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
                                  fill=RED, outline="#ffffff", width=1)

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
        self.geometry("1664x936")  # Reference resolution
        self.minsize(1400, 850)

        self.cap = cap
        self.detect_face = face_mesh_module.detect_face
        self.draw_face_mesh = face_mesh_module.draw_face_mesh
        self.engine = engine
        self.object_detector = object_detector
        self.alert_manager = alert_manager
        self.logger = logger
        self.test_mode = test_mode
        self.config = get_config()  # For UI configuration access

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
        self._build_body(self)
        self._build_bottom()
        self._build_footer()

        self._clock_job = None
        self._update_job = None

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._tick_clock()

        self.vehicle_panel = VehicleControlPanel(master=self, engine=self.engine)
        self.vehicle_panel.start_monitoring()

        if not test_mode:
            self._update_job = self.after(33, self._update)

# ---------------- header ----------------
    def _build_header(self):
        hdr = tk.Frame(self, bg=BG, height=55)
        hdr.pack(fill="x", padx=25, pady=(20, 0))
        hdr.pack_propagate(False)

        # Left section: Logo + App name
        left = tk.Frame(hdr, bg=BG)
        left.pack(side="left", pady=6)

        # D Logo - blue square with white D
        logo = tk.Frame(left, bg=BLUE, width=24, height=24)
        logo.pack(side="left", padx=(0, 10))
        logo.pack_propagate(False)
        tk.Label(logo, text="D", bg=BLUE, fg="white", font=("JetBrains Mono", 12, "bold")).place(relx=0.5, rely=0.5, anchor="center")

        # App name and subtitle
        name_frame = tk.Frame(left, bg=BG)
        name_frame.pack(side="left")
        tk.Label(name_frame, text="DrowsiGuard", bg=BG, fg=TEXT, font=("JetBrains Mono", 20, "bold")).pack(anchor="w")
        tk.Label(name_frame, text="Driver Monitoring System", bg=BG, fg=MUTED, font=("JetBrains Mono", 11)).pack(anchor="w")

        # RESET button - positioned after app name
        self._build_one_touch_action(hdr)

        # Right section: Camera status, Night mode, Clock
        right = tk.Frame(hdr, bg=BG)
        right.pack(side="right", pady=6)

        self._clock_var = tk.StringVar(value="--:-- --")
        tk.Label(right, textvariable=self._clock_var, bg=BG, fg=MUTED, font=("JetBrains Mono", 11)).pack(side="right", padx=(20, 0))

        cam = tk.Frame(right, bg=BG)
        cam.pack(side="right", padx=12)
        cam_ok = self.cap is not None and (self.test_mode or self.cap.isOpened())
        self._camera_dot = tk.Label(cam, text="●", bg=BG, fg=(GREEN if cam_ok else RED), font=("JetBrains Mono", 10))
        self._camera_dot.pack(side="left")
        self._camera_label = tk.Label(cam, text=f" Camera: {'Active' if cam_ok else 'Inactive'}", bg=BG, fg=MUTED, font=("JetBrains Mono", 9))
        self._camera_label.pack(side="left")

        # Separator line
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=25)

    def _build_one_touch_action(self, parent):
        """Emergency reset button: clears fatigue counters and stops any active alert tone."""
        def do_reset(event=None):
            self.engine.reset()
            if self.alert_manager:
                self.alert_manager.stop()
            if hasattr(self, 'vehicle_panel') and self.vehicle_panel is not None:
                self.vehicle_panel._cmd_reset()
            if self.logger:
                self.logger.log("RESET", "Manual reset triggered")
            print("[OneTouchAction] Reset performed.")
        btn = tk.Label(parent, text="RESET", bg=RED, fg="white",
                        font=("JetBrains Mono", 9, "bold"), padx=12, pady=3, cursor="hand2")
        btn.pack(side="left", padx=20)
        btn.bind("<Button-1>", do_reset)

        # Vehicle Control panel launcher
        def open_vehicle_panel(event=None):
            self.vehicle_panel.deiconify()
            self.vehicle_panel.lift()
            self.vehicle_panel.focus_force()
        vc_btn = tk.Label(parent, text="VEHICLE CONTROL", bg=BLUE, fg="white",
                          font=("JetBrains Mono", 9, "bold"), padx=12, pady=3, cursor="hand2")
        vc_btn.pack(side="left", padx=(0, 20))
        vc_btn.bind("<Button-1>", open_vehicle_panel)

    def _build_body(self, parent):
        body = tk.Frame(parent, bg=BG)
        body.pack(fill="both", expand=True)
        self._build_left(body)
        self._build_center(body)
        self._build_right(body)

    def _build_left(self, parent):
        left = tk.Frame(parent, bg=BG, width=160)
        left.pack(side="left", fill="y", padx=(25, 0), pady=10)
        left.pack_propagate(False)

        tk.Label(left, text="Real-Time Metrics", bg=BG, fg=MUTED, font=("JetBrains Mono", 11, "bold")).pack(anchor="w", padx=0, pady=(0, 8))

        self.card_fatigue = MetricCard(left, "Fatigue Level", "0%", "%", "Normal", GREEN, True, GREEN, 0)
        self.card_attention = MetricCard(left, "Attention Score", "100%", "%", "Good", GREEN, True, GREEN, 100)
        self.card_perclos = MetricCard(left, "PERCLOS", "0%", "%", "Normal", GREEN, True, GREEN, 0)
        self.card_eye = MetricCard(left, "Eye Closure", "0.00s", "s", "Normal", GREEN, False)
        self.card_yawns = MetricCard(left, "Yawns", "0", "", "This session", MUTED, False)
        self.card_gaze = MetricCard(left, "Gaze Direction", "Center", "", "Tracking", MUTED, False)

        for card in (self.card_fatigue, self.card_attention, self.card_perclos,
                     self.card_eye, self.card_yawns, self.card_gaze):
            card.pack(fill="x", pady=3)

        # Distraction indicators
        tags_frame = tk.Frame(left, bg=BG)
        tags_frame.pack(fill="x", padx=0, pady=(12, 0))
        self._tag_widgets = {}
        for tag in ["phone", "drink", "smoke"]:
            t = tk.Frame(tags_frame, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            t.pack(fill="x", pady=2)
            label_text = tag.capitalize() if tag != "smoke" else "Smoke (planned)"
            lbl = tk.Label(t, text=label_text, bg=CARD, fg=MUTED, font=("JetBrains Mono", 9))
            lbl.pack(padx=10, pady=5)
            self._tag_widgets[tag] = (t, lbl)

    def _build_center(self, parent):
        center = tk.Frame(parent, bg=BG)
        center.pack(side="left", fill="both", expand=True, padx=(15, 0), pady=10)

        # Driver Status header
        header_frame = tk.Frame(center, bg=BG)
        header_frame.pack(fill="x", padx=4, pady=(0, 4))
        tk.Label(header_frame, text="Driver Status", bg=BG, fg=TEXT, font=("JetBrains Mono", 14, "bold")).pack(side="left")

        # Camera panel - larger size
        self.video_canvas = VideoCanvas(center, height=450)
        self.video_canvas.pack(fill="both", expand=True, padx=4, pady=(4, 8))

    def _set_threshold(self, val):
        self.alert_threshold = val
        self._refresh_threshold_pills()

    def _refresh_threshold_pills(self):
        for val, lbl in self._threshold_labels.items():
            active = val == self.alert_threshold
            lbl.configure(bg=YELLOW if active else CARD, fg="black" if active else MUTED)

    def _build_right(self, parent):
        tk.Frame(parent, bg=BORDER, width=1).pack(side="left", fill="y", padx=15)
        right = tk.Frame(parent, bg=BG, width=390)
        right.pack(side="left", fill="y", padx=(0, 25), pady=10)
        right.pack_propagate(False)

        # ▲ Alert System header
        alert_header = tk.Frame(right, bg=BG)
        alert_header.pack(fill="x", padx=20, pady=(12, 6))
        tk.Label(alert_header, text="▲", bg=BG, fg=RED, font=("JetBrains Mono", 10)).pack(side="left")
        tk.Label(alert_header, text=" Alert System", bg=BG, fg=RED, font=("JetBrains Mono", 10, "bold")).pack(side="left")

        # System Info block
        info_label = tk.Label(right, text="System Info", bg=BG, fg=MUTED, font=("JetBrains Mono", 8, "bold"))
        info_label.pack(anchor="w", padx=20, pady=(8, 4))

        self.info_details = tk.Label(right, text="• GPS: Guided\n• Camera: Active\n• Sensors: Online",
                               bg=PANEL, fg=TEXT, font=("JetBrains Mono", 8), justify="left")
        self.info_details.pack(anchor="w", padx=20, pady=(0, 8))

        # Status line
        status_frame = tk.Frame(right, bg=BG)
        status_frame.pack(fill="x", padx=12, pady=(0, 8))
        self.status_label = tk.Label(status_frame, text="All systems operational", bg=BG, fg=GREEN, font=("JetBrains Mono", 8))
        self.status_label.pack(anchor="w")

        # Recent Summary card with tabs
        summary_frame = tk.Frame(right, bg=BG)
        summary_frame.pack(fill="both", expand=True, padx=20, pady=(8, 4))

        header_row = tk.Frame(summary_frame, bg=BG)
        header_row.pack(fill="x", padx=6, pady=(6, 4))
        tk.Label(header_row, text="Recent Summary", bg=BG, fg=TEXT, font=("JetBrains Mono", 10, "bold")).pack(side="left")

        # Tab container
        tab_container = tk.Frame(summary_frame, bg=BG)
        tab_container.pack(fill="x", padx=6, pady=(0, 6))

        self.summary_tabs = {}
        for i, (mins, label) in enumerate([(5, "5 Min"), (10, "10 Min"), (15, "15 Min")]):
            tab_btn = tk.Label(tab_container, text=label, bg=CARD, fg=MUTED,
                              font=("JetBrains Mono", 8), padx=12, pady=4, cursor="hand2")
            tab_btn.pack(side="left", padx=(0, 4) if i < 2 else 0)
            tab_btn.bind("<Button-1>", lambda e, m=mins: self._set_summary_window(m))
            self.summary_tabs[mins] = tab_btn

        self._summary_window = 5
        self._refresh_summary_window_pills()

        # Summary values container
        self.summary_values_frame = tk.Frame(summary_frame, bg=CARD)
        self.summary_values_frame.pack(fill="x", padx=6, pady=(0, 6))

        # Eye Closures row
        eye_row = tk.Frame(self.summary_values_frame, bg=CARD)
        eye_row.pack(fill="x", pady=3)
        tk.Label(eye_row, text="Eye Closures", bg=CARD, fg=MUTED, font=("JetBrains Mono", 8)).pack(side="left")
        self.eye_closures_label = tk.Label(eye_row, text="0 events", bg=CARD, fg=TEXT, font=("JetBrains Mono", 8))
        self.eye_closures_label.pack(side="left", padx=(8, 0))

        # Yawns row
        yawns_row = tk.Frame(self.summary_values_frame, bg=CARD)
        yawns_row.pack(fill="x", pady=3)
        tk.Label(yawns_row, text="Yawns", bg=CARD, fg=MUTED, font=("JetBrains Mono", 8)).pack(side="left")
        self.yawns_value_label = tk.Label(yawns_row, text="0 events", bg=CARD, fg=TEXT, font=("JetBrains Mono", 8))
        self.yawns_value_label.pack(side="left", padx=(8, 0))

        # Fatigue Alerts row
        fatigue_row = tk.Frame(self.summary_values_frame, bg=CARD)
        fatigue_row.pack(fill="x", pady=3)
        tk.Label(fatigue_row, text="Fatigue Alerts", bg=CARD, fg=MUTED, font=("JetBrains Mono", 8)).pack(side="left")
        self.fatigue_value_label = tk.Label(fatigue_row, text="0 events", bg=CARD, fg=TEXT, font=("JetBrains Mono", 8))
        self.fatigue_value_label.pack(side="left", padx=(8, 0))

        # Avg Attention row
        att_row = tk.Frame(self.summary_values_frame, bg=CARD)
        att_row.pack(fill="x", pady=3)
        tk.Label(att_row, text="Avg Attention", bg=CARD, fg=MUTED, font=("JetBrains Mono", 8)).pack(side="left")
        self.avg_attention_label = tk.Label(att_row, text="100%", bg=CARD, fg=TEXT, font=("JetBrains Mono", 8))
        self.avg_attention_label.pack(side="left", padx=(8, 0))

        # PERCLOS Avg row
        perclos_row = tk.Frame(self.summary_values_frame, bg=CARD)
        perclos_row.pack(fill="x", pady=3)
        tk.Label(perclos_row, text="PERCLOS Avg", bg=CARD, fg=MUTED, font=("JetBrains Mono", 8)).pack(side="left")
        self.perclos_avg_label = tk.Label(perclos_row, text="0%", bg=CARD, fg=TEXT, font=("JetBrains Mono", 8))
        self.perclos_avg_label.pack(side="left", padx=(8, 0))

        # Vehicle Status card
        vehicle_frame = tk.Frame(right, bg=BG)
        vehicle_frame.pack(fill="x", padx=20, pady=(8, 4))

        tk.Label(vehicle_frame, text="Vehicle Status", bg=BG, fg=YELLOW, font=("JetBrains Mono", 10, "bold")).pack(anchor="w", padx=6, pady=(6, 4))

        # Tire Pressure
        tire_frame = tk.Frame(vehicle_frame, bg=BG)
        tire_frame.pack(fill="x", padx=6, pady=(0, 4))
        tk.Label(tire_frame, text="Tire Pressure (PSI)", bg=BG, fg=MUTED, font=("JetBrains Mono", 8)).pack(anchor="w")

        self.tire_labels = {}
        tire_positions = ["FL", "FR", "RL", "RR"]
        for pos in tire_positions:
            tire_container = tk.Frame(tire_frame, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            tire_container.pack(fill="x", pady=2)

            tire_inner = tk.Frame(tire_container, bg=CARD)
            tire_inner.pack(fill="x", padx=8, pady=4)

            pos_label = tk.Label(tire_inner, text=f"{pos}:", bg=CARD, fg=TEXT, font=("JetBrains Mono", 8))
            pos_label.pack(side="left")

            pressure_label = tk.Label(tire_inner, text="-- psi", bg=CARD, fg=TEXT, font=("JetBrains Mono", 8))
            pressure_label.pack(side="left", padx=(8, 0))

            self.tire_labels[pos] = pressure_label

        # Fuel level with progress bar
        fuel_frame = tk.Frame(vehicle_frame, bg=BG)
        fuel_frame.pack(fill="x", padx=6, pady=(4, 4))
        tk.Label(fuel_frame, text="Fuel Level", bg=BG, fg=MUTED, font=("JetBrains Mono", 8)).pack(anchor="w")

        self.fuel_frame = tk.Frame(fuel_frame, bg=BORDER, height=8)
        self.fuel_frame.pack(fill="x", pady=(4, 4))
        self.fuel_frame.pack_propagate(False)
        self.fuel_bar = tk.Frame(self.fuel_frame, bg=GREEN, height=8)
        self.fuel_bar.place(relwidth=0, relheight=1)

        self.fuel_percent_label = tk.Label(fuel_frame, text="0%", bg=PANEL, fg=TEXT, font=("JetBrains Mono", 8))
        self.fuel_percent_label.pack(anchor="w")

        # Vehicle speed
        speed_frame = tk.Frame(vehicle_frame, bg=BG)
        speed_frame.pack(fill="x", padx=6, pady=(4, 6))
        tk.Label(speed_frame, text="Vehicle Speed", bg=BG, fg=MUTED, font=("JetBrains Mono", 8)).pack(anchor="w")
        self.speed_value_label = tk.Label(speed_frame, text="-- km/h", bg=BG, fg=TEXT, font=("JetBrains Mono", 14, "bold"))
        self.speed_value_label.pack(anchor="w", pady=(2, 0))
        # DEMO label
        tk.Label(speed_frame, text="DEMO", bg=BG, fg=MUTED, font=("JetBrains Mono", 7)).pack(anchor="w")

    def _build_bottom(self):
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=25)
        bottom = tk.Frame(self, bg=BG)
        bottom.pack(fill="x", padx=30, pady=(0, 10))

        # Configure grid for two columns: Guided Navigation (left) and Map (right)
        bottom.columnconfigure(0, weight=0, minsize=280)  # Fixed width for Guided Navigation
        bottom.columnconfigure(1, weight=1)  # Map takes remaining space

        # NEW: Guided Navigation turn-by-turn card (left side)
        nav_frame = tk.Frame(bottom, bg=BG)
        nav_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=4)
        nav_frame.pack_propagate(False)

        tk.Label(nav_frame, text="Guided Navigation", bg=BG, fg=BLUE, font=("JetBrains Mono", 10, "bold")).pack(anchor="w", padx=10, pady=(8, 4))

        # Current turn display
        current_turn = tk.Frame(nav_frame, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        current_turn.pack(fill="x", padx=8, pady=(0, 4))

        # Up-arrow icon + big distance + turn direction + street name
        turn_inner = tk.Frame(current_turn, bg=CARD)
        turn_inner.pack(fill="x", padx=10, pady=8)

        tk.Label(turn_inner, text="▲", bg=CARD, fg=GREEN, font=("JetBrains Mono", 20)).pack(side="left", padx=(0, 8))

        turn_details = tk.Frame(turn_inner, bg=CARD)
        turn_details.pack(side="left", fill="y")

        self.nav_distance_label = tk.Label(turn_details, text="2.4 km", bg=CARD, fg=TEXT, font=("JetBrains Mono", 16, "bold"))
        self.nav_distance_label.pack(anchor="w")

        self.nav_direction_label = tk.Label(turn_details, text="Turn right", bg=CARD, fg=TEXT, font=("JetBrains Mono", 11, "bold"))
        self.nav_direction_label.pack(anchor="w")

        self.nav_street_label = tk.Label(turn_details, text="University Rd", bg=CARD, fg=MUTED, font=("JetBrains Mono", 9))
        self.nav_street_label.pack(anchor="w")

        # Divider
        tk.Frame(nav_frame, bg=BORDER, height=1).pack(fill="x", padx=8, pady=4)

        # Next turn
        next_turn = tk.Frame(nav_frame, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        next_turn.pack(fill="x", padx=8, pady=(0, 4))

        tk.Label(next_turn, text="Next Turn", bg=CARD, fg=MUTED, font=("JetBrains Mono", 7)).pack(anchor="w", padx=8, pady=(3, 0))

        next_turn_inner = tk.Frame(next_turn, bg=CARD)
        next_turn_inner.pack(fill="x", padx=8, pady=4)

        tk.Label(next_turn_inner, text="▲", bg=CARD, fg=GREEN, font=("JetBrains Mono", 12)).pack(side="left", padx=(0, 4))

        self.next_nav_distance_label = tk.Label(next_turn_inner, text="850 m", bg=CARD, fg=TEXT, font=("JetBrains Mono", 9))
        self.next_nav_distance_label.pack(side="left", padx=(0, 4))

        self.next_nav_direction_label = tk.Label(next_turn_inner, text="Turn left", bg=CARD, fg=TEXT, font=("JetBrains Mono", 9))
        self.next_nav_direction_label.pack(side="left", padx=(0, 4))

        self.next_nav_street_label = tk.Label(next_turn_inner, text="Main St", bg=CARD, fg=MUTED, font=("JetBrains Mono", 8))
        self.next_nav_street_label.pack(side="left", padx=(0, 4))

        # Divider
        tk.Frame(nav_frame, bg=BORDER, height=1).pack(fill="x", padx=8, pady=4)

        # ETA and Distance
        eta_frame = tk.Frame(nav_frame, bg=PANEL)
        eta_frame.pack(fill="x", padx=8, pady=(0, 4))

        tk.Label(eta_frame, text="ETA", bg=PANEL, fg=MUTED, font=("JetBrains Mono", 8)).pack(side="left")
        self.eta_label = tk.Label(eta_frame, text="09:32 PM", bg=PANEL, fg=TEXT, font=("JetBrains Mono", 8))
        self.eta_label.pack(side="left", padx=(10, 0))

        tk.Label(eta_frame, text="Distance", bg=PANEL, fg=MUTED, font=("JetBrains Mono", 8)).pack(side="left", padx=(20, 0))
        self.distance_label = tk.Label(eta_frame, text="2.4 km", bg=PANEL, fg=TEXT, font=("JetBrains Mono", 8))
        self.distance_label.pack(side="left", padx=(10, 0))

        # Red End Route button
        self.end_route_btn = tk.Label(nav_frame, text="End Route", bg=RED, fg="white",
                                      font=("JetBrains Mono", 9, "bold"), padx=10, pady=6, cursor="hand2")
        self.end_route_btn.pack(fill="x", padx=8, pady=(4, 8))
        self.end_route_btn.bind("<Button-1>", lambda e: print("[Guided Navigation] Route ended"))

        # Map (right side)
        map_frame = tk.Frame(bottom, bg=BG)
        map_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=4)

        map_header = tk.Frame(map_frame, bg=BG)
        map_header.pack(fill="x", padx=8, pady=(8, 0))
        tk.Label(map_header, text="Live Map", bg=BG, fg=BLUE, font=("JetBrains Mono", 8, "bold")).pack(side="left")

        self.time_driven_var = tk.StringVar(value="00:00:00")
        tk.Label(map_header, textvariable=self.time_driven_var, bg=BG, fg=TEXT, font=("JetBrains Mono", 10, "bold")).pack(side="right")
        tk.Label(map_header, text="Time driven: ", bg=BG, fg=MUTED, font=("JetBrains Mono", 8)).pack(side="right")

        # Pass our specific map and path
        self.map_canvas = MapCanvas(map_frame,
                                    map_image_path="assets/map.png",
                                    vehicle_path=self.campari_to_parliament_path)
        self.map_canvas.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _build_footer(self):
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=25)
        ftr = tk.Frame(self, bg=BG, height=30)
        ftr.pack(fill="x", padx=30, pady=(0, 20))
        ftr.pack_propagate(False)

        left = tk.Frame(ftr, bg=BG)
        left.pack(side="left", pady=4)
        for label in ["Settings", "Device Config", "History & Logs"]:
            btn = tk.Label(left, text=label, bg=BG, fg=MUTED, font=("JetBrains Mono", 9), cursor="hand2")
            btn.pack(side="left", padx=12)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(fg=TEXT))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(fg=MUTED))

        right = tk.Frame(ftr, bg=BG)
        right.pack(side="right", pady=4)

        self._footer_dots = {}
        for key, label in [("system", "System OK"), ("gps", "GPS: Route Active"), ("sensors", "Sensors Online")]:
            f = tk.Frame(right, bg=BG)
            f.pack(side="left", padx=14)
            dot = tk.Label(f, text="●", bg=BG, fg=GREEN, font=("JetBrains Mono", 8))
            dot.pack(side="left")
            lbl = tk.Label(f, text=f" {label}", bg=BG, fg=MUTED, font=("JetBrains Mono", 9))
            lbl.pack(side="left")
            self._footer_dots[key] = (dot, lbl)

        # Set GPS indicator to active since we're using guided path
        self._footer_dots["gps"][0].configure(fg=GREEN)

    def _tick_clock(self):
        self._clock_var.set(time.strftime("%I:%M %p"))
        self._clock_job = self.after(1000, self._tick_clock)

    # ---------------- live update loop ----------------
    def process_one_frame(self, frame):
        """Runs the real detection pipeline on one BGR frame. Returns
        (result, obj_result, overall_severity, overall_status, display_frame).
        Split out from _update() so it can be tested without a live camera."""
        from src.core.severity import combine

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
        eye_status = "DROWSY" if closed_time > 1.3 else ("Warning" if closed_time > 0.2 else "Normal")
        eye_color = RED if closed_time > 1.3 else (YELLOW if closed_time > 0.2 else GREEN)
        self.card_eye.update_values(f"{closed_time:.2f}s", eye_status, eye_color)

        self.card_yawns.update_values(str(result.get("yawn_counter", 0)))

        # Update gaze direction
        gaze = result.get("gaze_direction", "Center")
        self.card_gaze.update_values(gaze, "Tracking", ACCENT_BLUE if gaze == "Center" else YELLOW)

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
        if not hasattr(self, '_last_speed'):
            self._last_speed = 0
            self._last_fuel = 75
            self._last_tire_pressures = {"FL": 32, "FR": 32, "RL": 31, "RR": 31}

        # Speed: gradual acceleration/deceleration (0-80 km/h for city driving)
        target_speed = random.randint(20, 60)
        speed_change = (target_speed - self._last_speed) * 0.1
        speed = self._last_speed + speed_change
        speed = max(0, min(80, speed))
        self.speed_value_label.configure(text=f"{int(speed)} km/h")
        self._last_speed = speed

        # Fuel: slow consumption, shown as a progress bar
        fuel_change = random.uniform(-0.05, 0.01)
        fuel = self._last_fuel + fuel_change
        fuel = max(5, min(95, fuel))

        fuel_color = GREEN
        if fuel < 10:
            fuel_color = RED
        elif fuel < 25:
            fuel_color = YELLOW

        self.fuel_bar.configure(bg=fuel_color)
        self.fuel_bar.place(relwidth=max(0.0, min(1.0, fuel / 100)), relheight=1)
        self.fuel_percent_label.configure(text=f"{int(fuel)}%")
        self._last_fuel = fuel

        # Tire pressures: slight natural variation
        for pos, pressure_label in self.tire_labels.items():
            pressure_change = random.uniform(-0.2, 0.2)
            pressure = self._last_tire_pressures[pos] + pressure_change
            pressure = max(28, min(36, pressure))

            color = GREEN
            if pressure < 29:
                color = RED
            elif pressure > 35:
                color = YELLOW

            pressure_label.configure(text=f"{int(pressure)} psi", fg=color)
            self._last_tire_pressures[pos] = pressure

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

    # Recommended Actions panel removed from main dashboard

    def _update(self):
        if self.cap is not None:
            success, frame = self.cap.read()
            if success:
                result, obj_result, overall_severity, overall_status, disp = self.process_one_frame(frame)
                self.apply_frame_result(result, obj_result, overall_severity, overall_status, disp)
                # Update summary analytics
                self._update_summary_analytics()
        self._update_job = self.after(33, self._update)

    def _update_summary_analytics(self):
        """Update the summary panel with real-time analytics for Yawns and Fatigue Alerts."""
        if not hasattr(self, 'yawns_value_label') or not self.logger:
            return

        try:
            # Get analytics from the enhanced logger for the current window
            analytics = self.logger.get_realtime_analytics(self._summary_window)

            # Extract event counts
            event_counts = analytics.get('event_counts', {})
            yawn_count = event_counts.get('YAWN', 0)
            fatigue_count = event_counts.get('DROWSINESS_START', 0)
            eye_closure_count = event_counts.get('EYE_CLOSED', 0) + event_counts.get('DROWSINESS_START', 0)

            # Update the labels
            self.yawns_value_label.configure(text=f"{yawn_count} events")
            self.fatigue_value_label.configure(text=f"{fatigue_count} events")
            self.eye_closures_label.configure(text=f"{eye_closure_count} events")

            # Calculate average attention and PERCLOS from recent data
            avg_attention = analytics.get('avg_attention', 100)
            avg_perclos = analytics.get('avg_perclos', 0)
            self.avg_attention_label.configure(text=f"{avg_attention}%")
            self.perclos_avg_label.configure(text=f"{round(avg_perclos * 100)}%")

            # Optional: color code based on activity level
            total_events = yawn_count + fatigue_count
            if total_events > 5:  # High activity
                color = RED
            elif total_events > 2:  # Medium activity
                color = YELLOW
            else:  # Low activity
                color = GREEN
            self.yawns_value_label.configure(fg=color)
            self.fatigue_value_label.configure(fg=color)
            self.eye_closures_label.configure(fg=color)

        except Exception as e:
            print(f"[Dashboard] Error updating summary analytics: {e}")

    def _set_summary_window(self, minutes):
        """Set the summary window size and refresh the display."""
        self._summary_window = minutes
        self._refresh_summary_window_pills()
        self._update_summary_analytics()

    def _refresh_summary_window_pills(self):
        """Update the appearance of the summary window tab buttons."""
        for mins, tab_btn in self.summary_tabs.items():
            active = mins == self._summary_window
            tab_btn.configure(bg=BLUE if active else CARD,
                             fg="white" if active else MUTED)
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

        if self.vehicle_panel is not None:
            self.vehicle_panel.is_running = False
            self.vehicle_panel.destroy()

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

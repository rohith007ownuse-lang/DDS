"""
utils.py
Visual toolkit for the HUD-style dashboard: color palette + drawing
primitives (arc meters, corner brackets, glow lines, status chips).
No detection logic lives here.
"""

import math
import cv2
import numpy as np

CANVAS_W = 1400
CANVAS_H = 900
TOP_BANNER_H = 40
SIDEBAR_W = 260

COL_BG        = (10, 8, 6)
COL_PANEL     = (28, 22, 16)
COL_PANEL_EDGE= (60, 50, 35)
COL_TEXT      = (235, 240, 235)
COL_SUBTEXT   = (140, 150, 150)
COL_CYAN      = (255, 230, 40)
COL_CYAN_DIM  = (120, 100, 20)
COL_AMBER     = (0, 170, 255)
COL_RED       = (50, 50, 255)
COL_GREEN     = (110, 220, 90)
COL_GRAY      = (90, 90, 90)


def distance(p1, p2):
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


def put_text(canvas, text, org, scale=0.55, color=COL_TEXT, thickness=1,
             font=cv2.FONT_HERSHEY_SIMPLEX):
    cv2.putText(canvas, text, org, font, scale, color, thickness, cv2.LINE_AA)


def rounded_rect(canvas, pt1, pt2, color, radius=10, thickness=-1):
    x1, y1 = pt1
    x2, y2 = pt2
    cv2.rectangle(canvas, (x1 + radius, y1), (x2 - radius, y2), color, thickness)
    cv2.rectangle(canvas, (x1, y1 + radius), (x2, y2 - radius), color, thickness)
    cv2.ellipse(canvas, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, thickness)
    cv2.ellipse(canvas, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, thickness)
    cv2.ellipse(canvas, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, color, thickness)
    cv2.ellipse(canvas, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, color, thickness)


def glow_line(canvas, pt1, pt2, color, thickness=2, glow=4):
    overlay = canvas.copy()
    cv2.line(overlay, pt1, pt2, color, thickness + glow, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.25, canvas, 0.75, 0, dst=canvas)
    cv2.line(canvas, pt1, pt2, color, thickness, cv2.LINE_AA)


def draw_corner_brackets(canvas, pt1, pt2, color, length=26, thickness=2):
    x1, y1 = pt1
    x2, y2 = pt2
    corners = [
        ((x1, y1), (1, 1)), ((x2, y1), (-1, 1)),
        ((x1, y2), (1, -1)), ((x2, y2), (-1, -1)),
    ]
    for (cx, cy), (dx, dy) in corners:
        cv2.line(canvas, (cx, cy), (cx + dx * length, cy), color, thickness, cv2.LINE_AA)
        cv2.line(canvas, (cx, cy), (cx, cy + dy * length), color, thickness, cv2.LINE_AA)


def draw_arc_meter(canvas, center, radius, percent, color, label, value_text=None,
                    bg_color=(45, 38, 28), thickness=8):
    percent = max(0, min(100, percent))
    start_angle = -90
    end_angle = start_angle + int(360 * percent / 100)
    cv2.ellipse(canvas, center, (radius, radius), 0, 0, 360, bg_color, thickness, cv2.LINE_AA)
    if percent > 0:
        cv2.ellipse(canvas, center, (radius, radius), 0, start_angle, end_angle, color, thickness, cv2.LINE_AA)
    text = value_text if value_text is not None else f"{int(percent)}%"
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    put_text(canvas, text, (center[0] - tw // 2, center[1] + th // 2), 0.6, COL_TEXT, 2)
    (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
    put_text(canvas, label, (center[0] - lw // 2, center[1] + radius + 20), 0.4, COL_SUBTEXT, 1)


def draw_chip(canvas, pt1, pt2, label, active, active_color, radius=8):
    color = active_color if active else (40, 38, 34)
    text_color = COL_BG if active else COL_SUBTEXT
    rounded_rect(canvas, pt1, pt2, color, radius=radius)
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    cx = (pt1[0] + pt2[0]) // 2 - tw // 2
    cy = (pt1[1] + pt2[1]) // 2 + th // 2
    put_text(canvas, label, (cx, cy), 0.42, text_color, 1)


def pulse_color(base_color, t, speed=6.0, min_scale=0.4):
    scale = min_scale + (1 - min_scale) * (0.5 + 0.5 * math.sin(t * speed))
    return tuple(int(c * scale) for c in base_color)

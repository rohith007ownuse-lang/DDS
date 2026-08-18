"""
severity.py
Single source of truth mapping every possible detector status to a
severity tier: None (no alert), "INFO", "WARNING", or "CRITICAL".
"""

SEVERITY_ORDER = {"INFO": 0, "WARNING": 1, "CRITICAL": 2}

STATUS_SEVERITY = {
    "NORMAL": None,
    "NO FACE": None,
    "EYES CLOSED": None,
    "HEAD NOD DETECTED": "WARNING",
    "HEAD POSE ALERT": "WARNING",
    "DROWSINESS DETECTED": "CRITICAL",
    "DROWSINESS DETECTED (PERCLOS)": "CRITICAL",
    "PHONE USE DETECTED": "INFO",
    "DRINKING DETECTED": "INFO",
}


def severity_for(status):
    return STATUS_SEVERITY.get(status)


def combine(*severities):
    active = [s for s in severities if s]
    if not active:
        return None
    return max(active, key=lambda s: SEVERITY_ORDER[s])

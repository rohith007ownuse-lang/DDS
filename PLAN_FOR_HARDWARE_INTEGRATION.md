# Hardware Integration Plan for Driver Drowsiness Detection System

## Overview
This plan outlines the integration of hardware control (Arduino UNO + L298N + HC-SR04 + Servo + HC-05) into the existing DriverDrowsinessDetectionSystem to create a complete closed-loop drowsiness detection and vehicle control system.

## Current System Status
- ✅ Computer vision detection (OpenCV/MediaPipe)
- ✅ Fatigue analysis engine (EAR, MAR, head pose, PERCLOS)
- ✅ Alert management system (audio tones)
- ✅ Tkinter dashboard for visualization
- ✅ Session logging
- ❌ Hardware control integration (Arduino communication)
- ❌ Bidirectional communication for obstacle avoidance

## Integration Architecture

### Communication Protocol
Simple serial protocol over Bluetooth/USB:
- `R` - RUN / Driver Alert (normal operation)
- `D` - DROWSINESS EMERGENCY STOP
- `S` - Normal system stop
- `C` - Clear emergency / resume operation
- `F` - Force forward
- `B` - Backward
- `L` - Left turn
- `T` - Right turn
- `X` - Stop motors immediately

### Data Flow
```
[Camera] → [OpenCV] → [MediaPipe] → [FatigueEngine] 
                                          ↓
                                 [Drowsiness Decision] 
                                          ↓
                                 [Serial Command] → [Bluetooth/USB] 
                                          ↓
                                      [Arduino UNO] 
                                          ↓
                     [L298N Motor Control] ↔ [HC-SR04 Ultrasonic] ↔ [Servo Scanner]
                                          ↓
                                 [Vehicle Movement Control]
```

## Implementation Plan

### Phase 1: Serial Communication Layer
1. Create `src/hardware/serial_communicator.py`
2. Implement singleton SerialManager class
3. Add connection handling, error recovery, and automatic reconnection
4. Implement state-change command sending (optimization)
5. Add heartbeat/command acknowledgment mechanism

### Phase 2: FatigueEngine Integration
1. Modify `src/core/fatigue_engine.py` to return drowsiness state changes
2. Add serial command transmission on state transitions:
   - NORMAL → DROWSY: Send "D"
   - DROWSY → NORMAL: Send "C" then "R" after delay
3. Add configurable serial port settings
4. Add connection status monitoring

### Phase 3: Alarm System Enhancement
1. Keep existing AlertManager for audio feedback
2. Add optional hardware alarm (buzzer on Arduino) as backup
3. Synchronize software and hardware alarm activation

### Phase 4: Configuration
1. Add hardware settings to config files:
   - Serial port (`/dev/ttyACM0`, `/dev/rfcomm0`, `COM5`)
   - Baud rate (9600)
   - Connection timeout
   - Retry attempts
   - Command delay

### Phase 5: Testing & Validation
1. Unit tests for serial communicator
2. Integration tests with mock Arduino
3. Real hardware testing with safety precautions
4. Latency measurement and optimization

## Files to Create/Modify

### New Files:
- `src/hardware/__init__.py`
- `src/hardware/serial_communicator.py`
- `src/hardware/command_protocol.py`
- `src/hardware/arduino_interface.py` (optional abstraction layer)

### Modified Files:
- `src/core/fatigue_engine.py` - Add serial command output
- `src/__init__.py` - Export hardware module
- `main.py` - Add hardware initialization and cleanup
- `src/utils/config_manager.py` - Add hardware configuration (if exists)
- `src/tk_dashboard.py` - Add hardware status indicators

## Safety Considerations

### Fail-Safe Design:
1. **Arduino Side**: 
   - Independent obstacle avoidance (ultrasonic + servo)
   - Emergency stop on loss of serial communication
   - Timeout-based recovery

2. **Python Side**:
   - Serial communication errors don't crash detection
   - Visual indication of communication status
   - Manual override via dashboard
   - Automatic retry with exponential backoff

### Communication Reliability:
1. Heartbeat commands every 500ms when connected
2. Command acknowledgment from Arduino
3. Connection loss detection (>2s without heartbeat)
4. Automatic reconnection attempts
5. Queue commands if temporarily disconnected

## Configuration Parameters

### Serial Communication:
```ini
[hardware]
enabled = true
serial_port = /dev/ttyACM0
baud_rate = 9600
timeout = 1.0
heartbeat_interval = 0.5
max_reconnect_attempts = 5
reconnect_delay = 2.0
command_delay = 0.05  # seconds between commands
```

### Safety Thresholds (Arduino side):
```ini
[safety]
min_safe_distance = 25  # cm
obstacle_check_interval = 0.1  # seconds
servo_scan_angle_left = 150
servo_scan_angle_right = 30
servo_center_angle = 90
motor_speed = 170  # PWM value (0-255)
```

## Implementation Details

### SerialCommunicator Class:
```python
class SerialCommunicator:
    def __init__(self, port, baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.last_command = None
        self.is_connected = False
        self._lock = threading.Lock()
        
    def connect(self):
        # Attempt to establish serial connection
        
    def disconnect(self):
        # Close serial connection safely
        
    def send_command(self, command):
        # Send command only if different from last (state change)
        
    def send_heartbeat(self):
        # Send periodic heartbeat to maintain connection
        
    def is_available(self):
        # Check if serial communication is operational
```

### FatigueEngine Modifications:
Add output callback or return enhanced state dict with:
- `command_to_send`: "R", "D", "C", etc.
- `command_changed`: Boolean indicating if command changed from previous frame
- `connection_status`: Boolean for serial comm health

## Testing Strategy

### Unit Tests:
1. SerialCommunicator connection/disconnection
2. Command deduplication logic
3. Error handling and reconnection
4. Thread safety

### Integration Tests:
1. Mock Arduino testing with virtual serial port
2. End-to-end drowsiness detection → command sending
3. Connection loss and recovery scenarios
4. Timing validation (command latency < 100ms)

### Hardware Tests:
1. Breadboard testing with actual components
2. Range testing for Bluetooth serial
3. Power consumption measurements
4. Electromagnetic interference validation

## Dependencies
- `pyserial` (already likely installed via dependencies)
- No additional major dependencies required

## Rollback Plan
1. Feature flag to disable hardware integration
2. Graceful degradation to software-only alerts
3. Preserve all existing functionality when hardware unavailable
4. Clear logging when hardware integration is disabled

## Estimated Effort
- Phase 1 (Serial layer): 4-6 hours
- Phase 2 (FatigueEngine integration): 2-3 hours  
- Phase 3 (Alarm enhancement): 1-2 hours
- Phase 4 (Configuration): 1-2 hours
- Phase 5 (Testing): 4-6 hours
- Total: 12-19 hours

## Success Criteria
1. System detects drowsiness and sends "D" command within 200ms
2. Arduino receives command and stops motors within 100ms
3. System recovers from serial disconnection within 2 seconds
4. No false positives during normal operation
5. All existing functionality preserved when hardware disabled
6. Dashboard shows hardware connection status
7. Latency from eye closure detection to motor stop < 500ms
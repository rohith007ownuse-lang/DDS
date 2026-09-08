"""
serial_communicator.py
Handles serial communication with Arduino hardware for vehicle control.
Provides reliable, state-optimized communication with automatic reconnection.
"""

import serial
import threading
import time
import queue
from typing import Optional, Callable
from src.utils import COL_RED as _RED, COL_AMBER as _AMBER, COL_GREEN as _GREEN, COL_CYAN as _CYAN
from src.utils.config_manager import get_config


class SerialCommunicator:
    """
    Manages serial communication with Arduino hardware.
    Features:
    - Automatic connection/reconnection
    - State-change command optimization (avoids spamming same command)
    - Thread-safe operation
    - Command queuing with priority
    - Heartbeat monitoring
    """

    def __init__(self, port: str = None, baudrate: int = None):
        self.config = get_config()
        self.hardware_config = self.config.get('hardware', {})

        # Use provided params or config
        self.port = port or self.hardware_config.get('serial_port', '/dev/ttyACM0')
        self.baudrate = baudrate or self.hardware_config.get('baud_rate', 9600)
        self.timeout = self.hardware_config.get('timeout', 1.0)

        # Connection state
        self.serial_connection: Optional[serial.Serial] = None
        self.is_connected = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        # Command optimization
        self.last_command_sent: Optional[str] = None
        self.command_queue = queue.Queue()
        self.command_delay = self.hardware_config.get('command_delay', 0.05)

        # Heartbeat and monitoring
        self.heartbeat_interval = self.hardware_config.get('heartbeat_interval', 0.5)
        self.last_heartbeat = 0
        self.heartbeat_cmd = "H"  # Heartbeat command
        self.last_heartbeat_response = 0
        self.heartbeat_timeout = 2.0  # Consider disconnected if no heartbeat response

        # Reconnection settings
        self.max_reconnect_attempts = self.hardware_config.get('max_reconnect_attempts', 5)
        self.reconnect_delay = self.hardware_config.get('reconnect_delay', 2.0)
        self.reconnect_attempts = 0

        # Callback for connection status changes
        self.on_connect_callback: Optional[Callable[[bool], None]] = None
        self.on_command_sent_callback: Optional[Callable[[str], None]] = None

        # Worker thread
        self._worker_thread: Optional[threading.Thread] = None

        # Statistics
        self.stats = {
            'commands_sent': 0,
            'commands_skipped': 0,
            'reconnections': 0,
            'connection_time': 0,
            'last_error': None
        }

    def set_callbacks(self, on_connect: Callable[[bool], None] = None,
                      on_command_sent: Callable[[str], None] = None):
        """Set callback functions for connection and command events."""
        self.on_connect_callback = on_connect
        self.on_command_sent_callback = on_command_sent

    def start(self) -> bool:
        """Start the serial communication worker thread."""
        if self._worker_thread and self._worker_thread.is_alive():
            return True

        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

        # Wait a moment for initial connection attempt
        time.sleep(0.1)
        return self.is_connected

    def stop(self):
        """Stop the serial communication and clean up resources."""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)

        self.disconnect()

    def _worker_loop(self):
        """Main worker loop handling connection, commands, and heartbeats."""
        while not self._stop_event.is_set():
            try:
                # Ensure connection
                if not self.is_connected:
                    self._attempt_connection()

                # Process commands if connected
                if self.is_connected:
                    self._process_command_queue()
                    self._send_heartbeat_if_needed()
                    self._check_heartbeat_timeout()

                # Sleep briefly to prevent busy waiting
                time.sleep(0.01)

            except Exception as e:
                self.stats['last_error'] = str(e)
                print(f"[SerialCommunicator] Worker loop error: {e}")
                self.is_connected = False
                self._notify_connection_change(False)
                time.sleep(self.reconnect_delay)

    def _attempt_connection(self):
        """Attempt to establish serial connection."""
        with self._lock:
            if self.is_connected:
                return

            try:
                print(f"[SerialCommunicator] Attempting to connect to {self.port}@{self.baudrate}...")
                self.serial_connection = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    write_timeout=self.timeout
                )

                # Clear any initial data
                time.sleep(0.1)
                self.serial_connection.reset_input_buffer()
                self.serial_connection.reset_output_buffer()

                self.is_connected = True
                self.reconnect_attempts = 0
                self.stats['connection_time'] = time.time()
                self.stats['last_error'] = None

                print(f"[SerialCommunicator] Connected to {self.port}")
                self._notify_connection_change(True)

            except serial.SerialException as e:
                self.stats['last_error'] = str(e)
                print(f"[SerialCommunicator] Connection failed: {e}")
                self.is_connected = False
                self.serial_connection = None
                self._notify_connection_change(False)

                # Handle reconnection attempts
                self.reconnect_attempts += 1
                if self.reconnect_attempts >= self.max_reconnect_attempts:
                    print(f"[SerialCommunicator] Max reconnection attempts reached ({self.max_reconnect_attempts})")
                    # Continue trying but don't spam console
                    time.sleep(self.reconnect_delay * 2)
                else:
                    print(f"[SerialCommunicator] Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts} in {self.reconnect_delay}s...")
                    time.sleep(self.reconnect_delay)

            except Exception as e:
                self.stats['last_error'] = str(e)
                print(f"[SerialCommunicator] Unexpected connection error: {e}")
                self.is_connected = False
                self.serial_connection = None
                self._notify_connection_change(False)
                time.sleep(self.reconnect_delay)

    def disconnect(self):
        """Disconnect from serial port."""
        with self._lock:
            if self.serial_connection and self.serial_connection.is_open:
                try:
                    self.serial_connection.close()
                except Exception as e:
                    print(f"[SerialCommunicator] Error closing serial connection: {e}")
                finally:
                    self.serial_connection = None

            was_connected = self.is_connected
            self.is_connected = False
            if was_connected:
                print("[SerialCommunicator] Disconnected")
                self._notify_connection_change(False)

    def _process_command_queue(self):
        """Process commands from the queue."""
        try:
            # Get command without blocking
            command_data = self.command_queue.get_nowait()
            command = command_data.get('command')
            priority = command_data.get('priority', 0)  # Higher number = higher priority

            # For now, we process FIFO; priority could be implemented with PriorityQueue
            self._send_command(command)

        except queue.Empty:
            pass  # No commands to process
        except Exception as e:
            print(f"[SerialCommunicator] Error processing command queue: {e}")

    def _send_command(self, command: str) -> bool:
        """
        Send a command to the Arduino.
        Uses state-change optimization to avoid sending duplicate commands.
        """
        if not self.is_connected or not self.serial_connection:
            return False

        # State-change optimization: don't send same command consecutively
        if command == self.last_command_sent:
            self.stats['commands_skipped'] += 1
            return True  # Considered successful (no need to send)

        try:
            with self._lock:
                if self.serial_connection and self.serial_connection.is_open:
                    # Add newline for Arduino compatibility
                    cmd_bytes = f"{command}\n".encode('utf-8')
                    self.serial_connection.write(cmd_bytes)
                    self.serial_connection.flush()

                    self.last_command_sent = command
                    self.stats['commands_sent'] += 1

                    if self.on_command_sent_callback:
                        self.on_command_sent_callback(command)

                    print(f"[SerialCommunicator] Sent command: '{command}'")
                    time.sleep(self.command_delay)  # Small delay to prevent overwhelming
                    return True

        except serial.SerialException as e:
            self.stats['last_error'] = str(e)
            print(f"[SerialCommunicator] Serial error sending command '{command}': {e}")
            self.is_connected = False
            self._notify_connection_change(False)
        except Exception as e:
            self.stats['last_error'] = str(e)
            print(f"[SerialCommunicator] Error sending command '{command}': {e}")

        return False

    def send_command(self, command: str, priority: int = 0):
        """
        Public method to queue a command for sending.
        """
        self.command_queue.put({
            'command': command,
            'priority': priority,
            'timestamp': time.time()
        })

    def send_command_immediate(self, command: str) -> bool:
        """
        Send a command immediately (bypassing queue) for urgent situations.
        Still uses state-change optimization.
        """
        return self._send_command(command)

    def _send_heartbeat_if_needed(self):
        """Send heartbeat signal if interval has passed."""
        now = time.time()
        if now - self.last_heartbeat >= self.heartbeat_interval:
            self._send_command(self.heartbeat_cmd)
            self.last_heartbeat = now

    def _check_heartbeat_timeout(self):
        """Check if heartbeat timeout has occurred."""
        now = time.time()
        if (now - self.last_heartbeat_response > self.heartbeat_timeout and
                self.last_heartbeat_response > 0):  # Only check after first heartbeat
            print("[SerialCommunicator] Heartbeat timeout - considering disconnected")
            self.is_connected = False
            self._notify_connection_change(False)

    def heartbeat_received(self):
        """Call when heartbeat response is received from Arduino."""
        self.last_heartbeat_response = time.time()

    def _notify_connection_change(self, connected: bool):
        """Notify callbacks of connection status change."""
        if self.on_connect_callback:
            try:
                self.on_connect_callback(connected)
            except Exception as e:
                print(f"[SerialCommunicator] Error in connection callback: {e}")

    def get_stats(self) -> dict:
        """Get communication statistics."""
        stats = self.stats.copy()
        stats.update({
            'is_connected': self.is_connected,
            'port': self.port,
            'baudrate': self.baudrate,
            'queue_size': self.command_queue.qsize(),
            'last_command': self.last_command_sent,
            'uptime': time.time() - stats['connection_time'] if stats['connection_time'] > 0 else 0
        })
        return stats

    def is_available(self) -> bool:
        """Check if serial communication is available and connected."""
        return self.is_connected and self.serial_connection is not None and self.serial_connection.is_open


# Global serial communicator instance
_serial_communicator = None


def get_serial_communicator() -> SerialCommunicator:
    """Get or create the global serial communicator instance."""
    global _serial_communicator
    if _serial_communicator is None:
        _serial_communicator = SerialCommunicator()
    return _serial_communicator


def init_serial_communicator(port: str = None, baudrate: int = None) -> SerialCommunicator:
    """Initialize the serial communicator with optional parameters."""
    global _serial_communicator
    _serial_communicator = SerialCommunicator(port, baudrate)
    return _serial_communicator
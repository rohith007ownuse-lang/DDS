/*
 * drowsi_guard_car.ino
 * DrowsiGuard - Driver Drowsiness Detection System (DDS)
 * Arduino UNO + L298N 4WD vehicle control firmware.
 *
 * The AI system (Python) sends single-character serial commands over
 * USB/Bluetooth. The Arduino controls the L298N motor driver to move/stop
 * the vehicle.
 *
 * SAFETY BEHAVIOR (PROGRESSIVE BRAKING):
 *   In response to a safety trigger (drowsy eyes or face loss) the Python
 *   side sends "G" (GRADUAL BRAKE). The Arduino then REDUCES the L298N
 *   ENA/ENB PWM progressively (normal -> slow -> slower -> very slow ->
 *   stopped) instead of instantly cutting the motors. The STOP state is
 *   LATCHED: even if the condition clears, the vehicle stays stopped until
 *   an explicit RESET ("R" / "C").
 *
 * Commands:
 *   F  -> Forward
 *   B  -> Backward
 *   L  -> Turn left
 *   T  -> Turn right      (NOTE: 'R' is reserved for RESET)
 *   S  -> INSTANT stop (manual STOP button - cuts motors, does NOT latch)
 *   G  -> GRADUAL BRAKE   (safety stop - progressive PWM ramp, latched)
 *   R  -> RESET           (clears the latched stop - manual restart)
 *   C  -> Clear/reset     (alias of R)
 *   H  -> Heartbeat acknowledgment (keeps the serial link alive)
 *   W<0-255> -> Set motor speed (PWM), e.g. "W170"
 *
 * IMPORTANT: Because the AI side uses 'R' for RESET and 'R' is also a
 * natural "right turn" letter, 'R' is reserved as RESET to match the
 * safety spec. Right turn is sent as 'T' from the Python side.
 */

/* ---- L298N motor driver connections (as per project spec) ---- */
#define ENA 5   // Arduino D5  -> L298N ENA (Left motor enable / PWM)
#define IN1 4   // Arduino D4  -> L298N IN1
#define IN2 7   // Arduino D7  -> L298N IN2
#define ENB 6   // Arduino D6  -> L298N ENB (Right motor enable / PWM)
#define IN3 8   // Arduino D8  -> L298N IN3
#define IN4 12  // Arduino D12 -> L298N IN4

/* ---- Default speed (0-255 PWM) ---- */
#define DEFAULT_SPEED 170

/* ---- Gradual-braking profile (total ramp ~ brake_duration) ---- */
#define BRAKE_STEPS        12            // number of PWM reduction steps
#define BRAKE_STEP_DELAY_MS 120          // ms per step (~1.44s full ramp)

int motorSpeed = DEFAULT_SPEED;
bool emergencyStopped = false;   // Latched safety-stop flag

/* ------------------------------------------------------------------ */
/* Motor control primitives                                            */
/* ------------------------------------------------------------------ */

void stopMotors() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);
}

void moveForward() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
  analogWrite(ENA, motorSpeed);
  analogWrite(ENB, motorSpeed);
}

void moveBackward() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
  analogWrite(ENA, motorSpeed);
  analogWrite(ENB, motorSpeed);
}

void turnLeft() {
  // Right motors forward, left motors backward -> turn left
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
  analogWrite(ENA, motorSpeed);
  analogWrite(ENB, motorSpeed);
}

void turnRight() {
  // Left motors forward, right motors backward -> turn right
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
  analogWrite(ENA, motorSpeed);
  analogWrite(ENB, motorSpeed);
}

/* ------------------------------------------------------------------ */
/* Emergency stop - latched until reset                                */
/* ------------------------------------------------------------------ */

// Check the serial buffer for an early RESET during braking.
bool resetRequested() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == 'R' || c == 'r' || c == 'C' || c == 'c') return true;
  }
  return false;
}

void latchStop() {
  emergencyStopped = true;
}

void clearEmergencyStop() {
  emergencyStopped = false;
  stopMotors();  // remain at standstill until a movement command is given
}

// INSTANT stop: cut all motors immediately (manual STOP button).
// Does NOT latch - the driver can resume driving afterwards.
void instantStop() {
  stopMotors();
}

// PROGRESSIVE braking: ramp ENA/ENB PWM from the current speed down to 0,
// then latch the stop. Renders "normal -> slow -> slower -> very slow -> stop"
void gradualBrake() {
  latchStop();

  // Keep the direction wiring so the PWM reduction actually slows the car.
  int from = motorSpeed;
  int steps = BRAKE_STEPS;

  for (int i = steps; i >= 0; i--) {
    int spd = map(i, 0, steps, 0, from);  // linear ramp down
    analogWrite(ENA, spd);
    analogWrite(ENB, spd);

    // Allow manual RESET to abort an in-progress brake safely.
    if (resetRequested()) {
      clearEmergencyStop();
      return;
    }
    delay(BRAKE_STEP_DELAY_MS);
  }

  stopMotors();
  Serial.println("STOPPED");
}

/* ------------------------------------------------------------------ */
/* Setup / loop                                                        */
/* ------------------------------------------------------------------ */

void setup() {
  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(ENB, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  Serial.begin(9600);
  stopMotors();
}

void loop() {
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) return;

    char cmd = line.charAt(0);

    // Speed command: W<0-255>
    if (cmd == 'W' || cmd == 'w') {
      String numStr = line.substring(1);
      int spd = numStr.toInt();
      motorSpeed = constrain(spd, 0, 255);
      // Re-apply speed to current movement if not emergency-stopped
      if (!emergencyStopped) {
        analogWrite(ENA, motorSpeed);
        analogWrite(ENB, motorSpeed);
      }
      Serial.print("SPEED:");
      Serial.println(motorSpeed);
      return;
    }

    // Heartbeat acknowledgment
    if (cmd == 'H' || cmd == 'h') {
      Serial.println("ACK");
      return;
    }

    // INSTANT stop (manual) - highest priority.
    if (cmd == 'S' || cmd == 's') {
      instantStop();
      Serial.println("STOPPED");
      return;
    }

    // GRADUAL BRAKE (safety stop from AI) - progressive PWM ramp, latched.
    if (cmd == 'G' || cmd == 'g') {
      gradualBrake();
      return;
    }

    // RESET: clears the latched emergency stop (manual restart).
    if (cmd == 'R' || cmd == 'r' || cmd == 'C' || cmd == 'c') {
      clearEmergencyStop();
      Serial.println("RESET");
      return;
    }

    // Movement commands are ignored while emergency-stopped (latched).
    if (emergencyStopped) {
      Serial.println("ESTOP");
      return;
    }

    switch (cmd) {
      case 'F': case 'f': moveForward();  Serial.println("FWD");  break;
      case 'B': case 'b': moveBackward(); Serial.println("BACK"); break;
      case 'L': case 'l': turnLeft();     Serial.println("LEFT"); break;
      case 'T': case 't': turnRight();    Serial.println("RIGHT"); break;
      default:
        // Unknown / unsupported command - stay safe.
        stopMotors();
        Serial.println("UNKNOWN");
        break;
    }
  }
}

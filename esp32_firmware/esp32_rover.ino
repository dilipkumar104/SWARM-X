/*
 * ═══════════════════════════════════════════════════════════════════════
 *  ESP32 ROVER FIRMWARE
 *  SWARM-X Project
 * ═══════════════════════════════════════════════════════════════════════
 *
 *  Features:
 *    1. Reads HC-SR04 ultrasonic sensor distance
 *    2. Sends "DIST:XX" every 200ms via Serial (UART)
 *    3. Receives single-char motor commands: F, B, L, R, S
 *    4. Drives 4 DC motors via L298N motor driver (PWM + DIR)
 *
 *  Serial Protocol:
 *    TX (ESP32 → Pi):  "DIST:25\n"
 *    RX (Pi → ESP32):  'F', 'B', 'L', 'R', 'S'
 *
 *  Wiring: See README.md for full pin mapping
 * ═══════════════════════════════════════════════════════════════════════
 */

// ─────────────────────────────────────────────────────────────────────
//  ULTRASONIC SENSOR PINS (HC-SR04)
// ─────────────────────────────────────────────────────────────────────
#define TRIG_PIN    5
#define ECHO_PIN    18

// ─────────────────────────────────────────────────────────────────────
//  MOTOR DRIVER PINS (L298N)
//  Left side:  Motor A (front-left) + Motor B (rear-left)
//  Right side: Motor C (front-right) + Motor D (rear-right)
// ─────────────────────────────────────────────────────────────────────

// Left motors (Motor A + B share direction, individual enable)
#define LEFT_EN     13   // ENA on L298N — PWM speed control
#define LEFT_IN1    12   // IN1 — direction
#define LEFT_IN2    14   // IN2 — direction

// Right motors (Motor C + D share direction, individual enable)
#define RIGHT_EN    27   // ENB on L298N — PWM speed control
#define RIGHT_IN3   26   // IN3 — direction
#define RIGHT_IN4   25   // IN4 — direction

// ─────────────────────────────────────────────────────────────────────
//  PWM CONFIGURATION
// ─────────────────────────────────────────────────────────────────────
#define PWM_FREQ        1000   // 1 kHz
#define PWM_RESOLUTION  8      // 8-bit (0–255)
#define PWM_CHANNEL_L   0      // LEDC channel for left motors
#define PWM_CHANNEL_R   1      // LEDC channel for right motors
#define MOTOR_SPEED     200    // Default speed (0–255)

// ─────────────────────────────────────────────────────────────────────
//  TIMING
// ─────────────────────────────────────────────────────────────────────
#define DIST_SEND_INTERVAL  200   // Send distance every 200ms
unsigned long lastDistTime = 0;


// ═════════════════════════════════════════════════════════════════════
//  SETUP
// ═════════════════════════════════════════════════════════════════════
void setup() {
  // ── Serial ────────────────────────────────────────────────────────
  Serial.begin(115200);
  Serial.println("ESP32 Rover starting...");

  // ── Ultrasonic sensor ─────────────────────────────────────────────
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // ── Motor direction pins ──────────────────────────────────────────
  pinMode(LEFT_IN1, OUTPUT);
  pinMode(LEFT_IN2, OUTPUT);
  pinMode(RIGHT_IN3, OUTPUT);
  pinMode(RIGHT_IN4, OUTPUT);

  // ── PWM setup using LEDC ──────────────────────────────────────────
  ledcAttach(LEFT_EN, PWM_FREQ, PWM_RESOLUTION);
  ledcAttach(RIGHT_EN, PWM_FREQ, PWM_RESOLUTION);

  // ── Start with motors stopped ─────────────────────────────────────
  stopMotors();

  Serial.println("ESP32 Rover ready!");
}


// ═════════════════════════════════════════════════════════════════════
//  MAIN LOOP
// ═════════════════════════════════════════════════════════════════════
void loop() {
  // ── 1. Send ultrasonic distance at fixed interval ─────────────────
  unsigned long now = millis();
  if (now - lastDistTime >= DIST_SEND_INTERVAL) {
    lastDistTime = now;
    float distance = readUltrasonic();
    Serial.print("DIST:");
    Serial.println((int)distance);
  }

  // ── 2. Check for incoming motor commands ──────────────────────────
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    executeCommand(cmd);
  }
}


// ═════════════════════════════════════════════════════════════════════
//  ULTRASONIC SENSOR
// ═════════════════════════════════════════════════════════════════════

/**
 * Read distance from HC-SR04 ultrasonic sensor.
 * Returns distance in centimeters.
 * Returns -1 if no echo received (timeout).
 */
float readUltrasonic() {
  // Send a 10µs trigger pulse
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Measure echo pulse duration (timeout after 30ms ≈ ~500cm)
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);

  if (duration == 0) {
    return -1.0;  // No echo — object too far or sensor error
  }

  // Speed of sound ≈ 343 m/s → 0.0343 cm/µs → distance = duration * 0.0343 / 2
  float distance = (duration * 0.0343) / 2.0;
  return distance;
}


// ═════════════════════════════════════════════════════════════════════
//  MOTOR CONTROL
// ═════════════════════════════════════════════════════════════════════

/**
 * Execute a single-character motor command.
 *   F → Forward    (all motors forward)
 *   B → Backward   (all motors backward)
 *   L → Turn left  (left motors stop, right motors forward)
 *   R → Turn right (right motors stop, left motors forward)
 *   S → Stop       (all motors stop)
 */
void executeCommand(char cmd) {
  switch (cmd) {
    case 'F': case 'f':
      moveForward();
      break;
    case 'B': case 'b':
      moveBackward();
      break;
    case 'L': case 'l':
      turnLeft();
      break;
    case 'R': case 'r':
      turnRight();
      break;
    case 'S': case 's':
      stopMotors();
      break;
    default:
      // Ignore unknown commands (newlines, etc.)
      break;
  }
}

/** All motors forward */
void moveForward() {
  // Left motors forward
  digitalWrite(LEFT_IN1, HIGH);
  digitalWrite(LEFT_IN2, LOW);
  ledcWrite(LEFT_EN, MOTOR_SPEED);

  // Right motors forward
  digitalWrite(RIGHT_IN3, HIGH);
  digitalWrite(RIGHT_IN4, LOW);
  ledcWrite(RIGHT_EN, MOTOR_SPEED);
}

/** All motors backward */
void moveBackward() {
  // Left motors backward
  digitalWrite(LEFT_IN1, LOW);
  digitalWrite(LEFT_IN2, HIGH);
  ledcWrite(LEFT_EN, MOTOR_SPEED);

  // Right motors backward
  digitalWrite(RIGHT_IN3, LOW);
  digitalWrite(RIGHT_IN4, HIGH);
  ledcWrite(RIGHT_EN, MOTOR_SPEED);
}

/** Left motors stop, right motors forward → turn left */
void turnLeft() {
  // Left motors stop
  digitalWrite(LEFT_IN1, LOW);
  digitalWrite(LEFT_IN2, LOW);
  ledcWrite(LEFT_EN, 0);

  // Right motors forward
  digitalWrite(RIGHT_IN3, HIGH);
  digitalWrite(RIGHT_IN4, LOW);
  ledcWrite(RIGHT_EN, MOTOR_SPEED);
}

/** Right motors stop, left motors forward → turn right */
void turnRight() {
  // Left motors forward
  digitalWrite(LEFT_IN1, HIGH);
  digitalWrite(LEFT_IN2, LOW);
  ledcWrite(LEFT_EN, MOTOR_SPEED);

  // Right motors stop
  digitalWrite(RIGHT_IN3, LOW);
  digitalWrite(RIGHT_IN4, LOW);
  ledcWrite(RIGHT_EN, 0);
}

/** Stop all motors */
void stopMotors() {
  digitalWrite(LEFT_IN1, LOW);
  digitalWrite(LEFT_IN2, LOW);
  ledcWrite(LEFT_EN, 0);

  digitalWrite(RIGHT_IN3, LOW);
  digitalWrite(RIGHT_IN4, LOW);
  ledcWrite(RIGHT_EN, 0);
}

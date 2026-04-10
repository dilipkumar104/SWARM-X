/*
 * ══════════════════════════════════════════════════════════════
 *  SWARM-X  —  ESP32 Ultrasonic Publisher (micro-ROS)
 * ══════════════════════════════════════════════════════════════
 *
 *  Hardware : ESP32 Dev Module + HC-SR04 ultrasonic sensor
 *  Protocol : micro-ROS over USB Serial (115200 baud)
 *  Topic    : /ultrasonic/range  (sensor_msgs/msg/Range)
 *  Rate     : 10 Hz
 *
 *  Wiring (HC-SR04 → ESP32):
 *      VCC  → 5V  (or VIN)
 *      GND  → GND
 *      TRIG → GPIO 5
 *      ECHO → GPIO 18
 *
 *  ⚠ The HC-SR04 ECHO pin outputs 5V logic.  Most ESP32 GPIO
 *    are 5V-tolerant on input, but for safety you can use a
 *    voltage divider (2× resistors) on the ECHO line.
 *
 *  Dependencies:
 *      - Arduino core for ESP32
 *      - micro_ros_arduino library
 *
 *  Build:
 *      Board  → "ESP32 Dev Module"
 *      Upload → 115200 baud
 * ══════════════════════════════════════════════════════════════
 */

#include <micro_ros_arduino.h>

#include <stdio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

#include <sensor_msgs/msg/range.h>

// ── Pin definitions ──────────────────────────────────────────
#define TRIG_PIN  5
#define ECHO_PIN  18

// ── Built-in LED (used as connection indicator) ──────────────
#define LED_PIN   2    // Most ESP32 dev boards: GPIO 2

// ── Timing ───────────────────────────────────────────────────
#define PUBLISH_HZ       10          // 10 Hz  → 100 ms period
#define PUBLISH_PERIOD_MS (1000 / PUBLISH_HZ)

// ── Sensor constants (HC-SR04) ───────────────────────────────
#define SOUND_SPEED_CM_US  0.0343f   // cm per μs (at ~20 °C)
#define MIN_RANGE_M        0.02f     // 2 cm
#define MAX_RANGE_M        4.00f     // 400 cm
#define FOV_RAD            0.2618f   // ~15° half-angle

// ── micro-ROS objects ────────────────────────────────────────
rcl_publisher_t             publisher;
sensor_msgs__msg__Range     range_msg;
rclc_executor_t             executor;
rclc_support_t              support;
rcl_allocator_t             allocator;
rcl_node_t                  node;
rcl_timer_t                 timer;

// ── Connection state ─────────────────────────────────────────
enum AgentState { WAITING_AGENT, AGENT_AVAILABLE, AGENT_CONNECTED, AGENT_DISCONNECTED };
AgentState state = WAITING_AGENT;

// ── Error-check macro ────────────────────────────────────────
#define RCCHECK(fn)  { rcl_ret_t temp_rc = fn; if (temp_rc != RCL_RET_OK) { error_loop(); } }
#define RCSOFTCHECK(fn) { rcl_ret_t temp_rc = fn; (void)temp_rc; }

// ══════════════════════════════════════════════════════════════
//  ERROR HANDLER  — blinks LED rapidly forever
// ══════════════════════════════════════════════════════════════
void error_loop() {
    while (1) {
        digitalWrite(LED_PIN, !digitalRead(LED_PIN));
        delay(100);
    }
}

// ══════════════════════════════════════════════════════════════
//  READ HC-SR04  — returns distance in metres
// ══════════════════════════════════════════════════════════════
float read_ultrasonic_m() {
    // Send a 10 μs trigger pulse
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);

    // Measure ECHO pulse width (timeout: 30 ms ≈ 5.15 m)
    long duration_us = pulseIn(ECHO_PIN, HIGH, 30000);

    if (duration_us == 0) {
        // Timeout — no echo received
        return INFINITY;
    }

    // distance = (time × speed) / 2   (round-trip)
    float distance_cm = (duration_us * SOUND_SPEED_CM_US) / 2.0f;
    float distance_m  = distance_cm / 100.0f;

    return distance_m;
}

// ══════════════════════════════════════════════════════════════
//  TIMER CALLBACK  — called at PUBLISH_HZ
// ══════════════════════════════════════════════════════════════
void timer_callback(rcl_timer_t * timer, int64_t last_call_time) {
    RCLC_UNUSED(last_call_time);
    if (timer == NULL) return;

    // Read sensor
    float distance = read_ultrasonic_m();

    // Fill Range message
    range_msg.range = distance;

    // Timestamp (approximate — micro-ROS sets epoch offset)
    int64_t now = rmw_uros_epoch_millis();
    range_msg.header.stamp.sec  = (int32_t)(now / 1000);
    range_msg.header.stamp.nanosec = (uint32_t)((now % 1000) * 1000000);

    // Publish
    RCSOFTCHECK(rcl_publish(&publisher, &range_msg, NULL));

    // Blink LED on each publish (quick flash)
    digitalWrite(LED_PIN, HIGH);
    delay(5);
    digitalWrite(LED_PIN, LOW);
}

// ══════════════════════════════════════════════════════════════
//  micro-ROS AGENT LIFECYCLE
// ══════════════════════════════════════════════════════════════

bool create_entities() {
    allocator = rcl_get_default_allocator();

    // Support init
    RCCHECK(rclc_support_init(&support, 0, NULL, &allocator));

    // Create node: "esp32_ultrasonic"
    RCCHECK(rclc_node_init_default(&node, "esp32_ultrasonic", "", &support));

    // Create publisher on /ultrasonic/range
    RCCHECK(rclc_publisher_init_best_effort(
        &publisher,
        &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, Range),
        "/ultrasonic/range"
    ));

    // Create timer
    RCCHECK(rclc_timer_init_default(
        &timer,
        &support,
        RCL_MS_TO_NS(PUBLISH_PERIOD_MS),
        timer_callback
    ));

    // Create executor with 1 handle (the timer)
    RCCHECK(rclc_executor_init(&executor, &support.context, 1, &allocator));
    RCCHECK(rclc_executor_add_timer(&executor, &timer));

    // Sync time with agent
    RCSOFTCHECK(rmw_uros_sync_session(1000));

    return true;
}

void destroy_entities() {
    rmw_context_t * rmw_context = rcl_context_get_rmw_context(&support.context);
    (void) rmw_uros_set_context_entity_destroy_session_timeout(rmw_context, 0);

    rcl_publisher_fini(&publisher, &node);
    rcl_timer_fini(&timer);
    rclc_executor_fini(&executor);
    rcl_node_fini(&node);
    rclc_support_fini(&support);
}

// ══════════════════════════════════════════════════════════════
//  SETUP
// ══════════════════════════════════════════════════════════════
void setup() {
    // ── GPIO ──────────────────────────────────────────────────
    pinMode(TRIG_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);
    pinMode(LED_PIN,  OUTPUT);
    digitalWrite(LED_PIN, LOW);

    // ── Serial transport for micro-ROS ────────────────────────
    set_microros_transports();

    // ── Pre-fill static fields of the Range message ──────────
    range_msg.radiation_type = sensor_msgs__msg__Range__ULTRASOUND;
    range_msg.field_of_view  = FOV_RAD;
    range_msg.min_range      = MIN_RANGE_M;
    range_msg.max_range      = MAX_RANGE_M;

    // Frame ID — micro_ros_arduino uses a static char array
    // We point header.frame_id to a compile-time string
    static char frame_id[] = "ultrasonic_link";
    range_msg.header.frame_id.data     = frame_id;
    range_msg.header.frame_id.size     = strlen(frame_id);
    range_msg.header.frame_id.capacity = sizeof(frame_id);

    state = WAITING_AGENT;
}

// ══════════════════════════════════════════════════════════════
//  LOOP  — state machine for agent connection
// ══════════════════════════════════════════════════════════════
void loop() {
    switch (state) {

        case WAITING_AGENT:
            // Ping the agent — LED off while waiting
            if (RMW_RET_OK == rmw_uros_ping_agent(100, 1)) {
                state = AGENT_AVAILABLE;
            }
            break;

        case AGENT_AVAILABLE:
            // Agent found → create all ROS entities
            if (create_entities()) {
                state = AGENT_CONNECTED;
                digitalWrite(LED_PIN, HIGH);   // Solid LED = connected
            } else {
                state = WAITING_AGENT;         // Retry
            }
            break;

        case AGENT_CONNECTED:
            // Normal operation — spin executor
            RCSOFTCHECK(rclc_executor_spin_some(&executor, RCL_MS_TO_NS(100)));

            // Periodic connectivity check
            if (RMW_RET_OK != rmw_uros_ping_agent(100, 1)) {
                state = AGENT_DISCONNECTED;
            }
            break;

        case AGENT_DISCONNECTED:
            // Lost agent — tear down and wait for reconnect
            destroy_entities();
            digitalWrite(LED_PIN, LOW);
            state = WAITING_AGENT;
            break;

        default:
            break;
    }
}

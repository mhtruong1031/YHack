"""
Raspberry Pi hardware configuration: GPIO, ultrasonic, servos, WebSocket bind.
"""

# --- GPIO (BCM) ---
ULTRASONIC_TRIG_PIN = 23
ULTRASONIC_ECHO_PIN = 24
LED1_PIN = 17

# Hobby servos (AngularServo): one signal pin each
SERVO_MOTOR_A_PIN = 5
SERVO_MOTOR_B_PIN = 12
SERVO_MOTOR_C_PIN = 19

SERVO_MIN_ANGLE = -90
SERVO_MAX_ANGLE = 90

# HC-SR04 / DistanceSensor max range (meters)
ULTRASONIC_MAX_DISTANCE_M = 4.0

# --- Calibration ---
CALIBRATION_DURATION_SEC = 5.0
CALIBRATION_SAMPLE_INTERVAL_SEC = 0.05

# --- WebSocket server (Pi listens; laptop connects) ---
WS_HOST = "0.0.0.0"
WS_PORT = 8765

# --- Sort motor motion ---
MOTOR_HOLD_SEC = 2.0

# Angles (degrees) per classification — B positive vs negative for waste vs compost
ANGLE_WASTE_A = 90
ANGLE_WASTE_B = 45
ANGLE_RECYCLABLE_B = 90
ANGLE_COMPOST_B = -45
ANGLE_COMPOST_C = 90

"""
Raspberry Pi hardware configuration: servos, simulated distance, WebSocket bind.
"""

import os

# Motor driver: "gpiozero" = GPIO PWM (BCM pins below). "servokit" = PCA9685 I2C
# (same as servo_test3.py / Adafruit Servo HAT).
_SERVO_BACKEND_RAW = (os.environ.get("SERVO_BACKEND") or "gpiozero").strip().lower()
SERVO_BACKEND = (
    _SERVO_BACKEND_RAW if _SERVO_BACKEND_RAW in ("gpiozero", "servokit") else "gpiozero"
)

SERVOKIT_NUM_CHANNELS = int(os.environ.get("SERVOKIT_NUM_CHANNELS", "16"), 10)
SERVOKIT_I2C_ADDRESS = int(os.environ.get("SERVOKIT_I2C_ADDRESS", "0x40"), 16)
SERVOKIT_CHANNEL_A = int(os.environ.get("SERVOKIT_CHANNEL_A", "0"), 10)
SERVOKIT_CHANNEL_B = int(os.environ.get("SERVOKIT_CHANNEL_B", "1"), 10)
SERVOKIT_CHANNEL_C = int(os.environ.get("SERVOKIT_CHANNEL_C", "2"), 10)

# Hobby servos (AngularServo): one signal pin each — used only when SERVO_BACKEND=gpiozero
SERVO_MOTOR_A_PIN = 5
SERVO_MOTOR_B_PIN = 12
SERVO_MOTOR_C_PIN = 19

SERVO_MIN_ANGLE = -90
SERVO_MAX_ANGLE = 90

# --- Simulated distance (no ultrasonic) ---
# Laptop uses ready.calibrated_avg_cm − PROXIMITY_MARGIN_CM as the “occupied” threshold.
# If SIMULATED_DISTANCE_CM stays above that value, proximity-based sorts never fire (use camera / lighting on server).
SIMULATED_DISTANCE_CM = 100.0
SIMULATED_CALIBRATED_AVG_CM = 100.0

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

"""
Raspberry Pi hardware configuration: servos, simulated distance, WebSocket bind.
"""

# Hobby servos (AngularServo): one signal pin each
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

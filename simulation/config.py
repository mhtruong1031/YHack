"""
Simulation WebSocket bind, timing, and GPIO constants (mirrors hardware/config.py BCM + angles).
"""

# --- Mirrored from hardware/config.py (avoid package import cycles) ---
ULTRASONIC_ECHO_PIN = 24
LED1_PIN = 17
SERVO_MOTOR_A_PIN = 5
SERVO_MOTOR_B_PIN = 12
SERVO_MOTOR_C_PIN = 19

ANGLE_WASTE_A = 90
ANGLE_WASTE_B = 45
ANGLE_RECYCLABLE_B = 90
ANGLE_COMPOST_B = -45
ANGLE_COMPOST_C = 90

# --- Simulation-only ---
SIM_WS_HOST = "127.0.0.1"
SIM_WS_PORT = 18765
SIM_MOTOR_HOLD_SEC = 0.15
SIM_BASELINE_CM = 50.0
SIM_RESET_SLEEP_SEC = 0.05

"""
Raspberry Pi hardware configuration: servos, simulated distance, WebSocket bind.
"""

import os

# --- Simulated distance (no ultrasonic) ---
# Laptop uses ready.calibrated_avg_cm − PROXIMITY_MARGIN_CM as the “occupied” threshold.
# If SIMULATED_DISTANCE_CM stays above that value, proximity-based sorts never fire (use camera / lighting on server).
SIMULATED_DISTANCE_CM = 100.0
SIMULATED_CALIBRATED_AVG_CM = 100.0

# --- WebSocket server (Pi listens; laptop connects) ---
WS_HOST = "0.0.0.0"
WS_PORT = 8765

# --- Subprocess servo scripts (servo_test3.py / 4 / 5) ---
MOTOR_SCRIPT_TIMEOUT_SEC = float(os.environ.get("MOTOR_SCRIPT_TIMEOUT_SEC", "120"))

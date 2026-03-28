"""
Harness-only WebSocket message types for driving virtual GPIO (not used by server/main.py).

- BCM 24 (ECHO): input value is simulated distance in cm.
- Outputs: servo angles (degrees) on BCM 5, 12, 19; LED state 0/1 on BCM 17.
"""

TYPE_PIN_INPUT = "pin_input"
TYPE_GET_PIN_OUTPUTS = "get_pin_outputs"
TYPE_PIN_OUTPUTS = "pin_outputs"

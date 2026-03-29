"""
Optional PCA9685 / Adafruit ServoKit sweep test.

Production sorting runs servo_test3/4/5.py via subprocess from motors.py (same as manual runs).
"""

from adafruit_servokit import ServoKit
import time

kit = ServoKit(channels=16, address=0x40)

# Center all
for ch in [0, 1, 2]:
    kit.servo[ch].angle = 90
time.sleep(2)

# Sweep all one at a time
for ch in [0, 1, 2]:
    print(f"Testing servo {ch}")
    kit.servo[ch].angle = 0
    time.sleep(2)
    kit.servo[ch].angle = 180
    time.sleep(2)
    kit.servo[ch].angle = 90
    time.sleep(2)

print("All servos tested")

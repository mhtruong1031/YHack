"""
Optional PCA9685 / Adafruit ServoKit sweep test — not the production gpiozero stack.

Production sorting uses gpiozero AngularServo on BCM pins (see motors.py).
Run this only when debugging I2C servos at address 0x40.
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

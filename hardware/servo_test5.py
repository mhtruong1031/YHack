from adafruit_servokit import ServoKit
import time

kit = ServoKit(channels=16, address=0x40)

# Center all
kit.servo[2].angle = 90
time.sleep(2)

# Sweep all one at a time
kit.servo[2].angle = 180
time.sleep(1)
kit.servo[2].angle = 90
time.sleep(2)

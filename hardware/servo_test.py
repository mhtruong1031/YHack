from adafruit_servokit import ServoKit
import time

kit = ServoKit(channels=16, address=0x40)

# center both
kit.servo[0].angle = 90
kit.servo[1].angle = 90
time.sleep(2)

# servo 0
kit.servo[0].angle = 80
time.sleep(1)
kit.servo[0].angle = 100
time.sleep(1)
kit.servo[0].angle = 90
time.sleep(1)

# servo 1
kit.servo[1].angle = 80
time.sleep(1)
kit.servo[1].angle = 100
time.sleep(1)
kit.servo[1].angle = 90
time.sleep(1)

print("Two-servo test complete")


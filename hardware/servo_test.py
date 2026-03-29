from adafruit_servokit import ServoKit
import time

kit = ServoKit(channels=16, address=0x40)

# center both
kit.servo[0].angle = 0
kit.servo[1].angle = 0
time.sleep(2)

# servo 0
kit.servo[0].angle = 180
time.sleep(1)
kit.servo[0].angle = 0
time.sleep(1)
kit.servo[0].angle = 180
time.sleep(1)

# servo 1
kit.servo[1].angle = 180
time.sleep(1)
kit.servo[1].angle = 0
time.sleep(1)
kit.servo[1].angle = 180
time.sleep(1)

print("Two-servo test complete")


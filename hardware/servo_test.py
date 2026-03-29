from adafruit_servokit import ServoKit
import time

kit = ServoKit(channels=16, address=0x40)

<<<<<<< HEAD
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
=======
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
>>>>>>> fccfe0bed8d1506c98569061735aa00aed683f5d

print("All servos tested")
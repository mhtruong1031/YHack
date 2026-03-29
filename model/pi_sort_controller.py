import time
import cv2
import requests
import RPi.GPIO as GPIO
from adafruit_servokit import ServoKit

# =========================
# Config
# =========================
ASUS_PREDICT_URL = "http://10.66.151.86:8000/predict""

CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

TRIG = 23
ECHO = 24
DISTANCE_THRESHOLD_CM = 10.0
TRIGGER_STABLE_DELAY = 0.5
SORT_COOLDOWN_SEC = 3.0
CONFIDENCE_THRESHOLD = 0.75

kit = ServoKit(channels=16, address=0x40)

RECYCLE_SERVO_CH = 0
COMPOST_SERVO_CH = 1
WASTE_SERVO_CH = 2

REST_ANGLE = 90
OPEN_ANGLE = 140
SERVO_HOLD_TIME = 2.0

# =========================
# Sensor setup
# =========================
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.output(TRIG, False)
time.sleep(2)

def get_distance():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    pulse_start = time.time()
    timeout = pulse_start + 0.05

    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
        if pulse_start > timeout:
            return None

    pulse_end = time.time()
    timeout = pulse_end + 0.05

    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()
        if pulse_end > timeout:
            return None

    pulse_duration = pulse_end - pulse_start
    return round(pulse_duration * 17150, 2)

# =========================
# Servo control
# =========================
def reset_servos():
    kit.servo[RECYCLE_SERVO_CH].angle = REST_ANGLE
    kit.servo[COMPOST_SERVO_CH].angle = REST_ANGLE
    kit.servo[WASTE_SERVO_CH].angle = REST_ANGLE
    time.sleep(0.5)

def route_item(disposal_category):
    reset_servos()

    if disposal_category == "recycle":
        kit.servo[RECYCLE_SERVO_CH].angle = OPEN_ANGLE
    elif disposal_category == "compost":
        kit.servo[COMPOST_SERVO_CH].angle = OPEN_ANGLE
    else:
        kit.servo[WASTE_SERVO_CH].angle = OPEN_ANGLE

    time.sleep(SERVO_HOLD_TIME)
    reset_servos()

# =========================
# ASUS prediction
# =========================
def predict_with_asus(frame):
    ok, buffer = cv2.imencode(".jpg", frame)
    if not ok:
        raise RuntimeError("Failed to encode frame")

    files = {
        "file": ("frame.jpg", buffer.tobytes(), "image/jpeg")
    }

    response = requests.post(ASUS_PREDICT_URL, files=files, timeout=10)
    response.raise_for_status()
    return response.json()

# =========================
# Main
# =========================
def main():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    reset_servos()
    last_sort_time = 0

    print("System running. Press Ctrl+C to stop.")

    try:
        while True:
            distance = get_distance()
            print("Distance:", distance)

            now = time.time()
            if (
                distance is not None
                and distance < DISTANCE_THRESHOLD_CM
                and (now - last_sort_time) > SORT_COOLDOWN_SEC
            ):
                print("Object detected, stabilizing...")
                time.sleep(TRIGGER_STABLE_DELAY)

                ret, frame = cap.read()
                if not ret:
                    print("Failed to capture frame")
                    continue

                result = predict_with_asus(frame)
                predicted_class = result["predicted_class"]
                confidence = result["confidence"]
                disposal_category = result["disposal_category"]

                print(
                    f"Predicted class: {predicted_class} | "
                    f"Confidence: {confidence:.2f} | "
                    f"Category: {disposal_category}"
                )

                if confidence >= CONFIDENCE_THRESHOLD:
                    route_item(disposal_category)
                else:
                    print("Confidence too low, skipping sort.")

                last_sort_time = time.time()

            time.sleep(0.2)

    finally:
        cap.release()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
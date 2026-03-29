import cv2
import requests

ASUS_PREDICT_URL = "http://10.66.218.112:8000/predict"
CAMERA_INDEX = 0

cap = cv2.VideoCapture(CAMERA_INDEX)
ret, frame = cap.read()
cap.release()

if not ret:
    raise RuntimeError("Failed to capture frame")

ok, buffer = cv2.imencode(".jpg", frame)
if not ok:
    raise RuntimeError("Failed to encode frame")

files = {
    "file": ("frame.jpg", buffer.tobytes(), "image/jpeg")
}

response = requests.post(ASUS_PREDICT_URL, files=files, timeout=10)
print(response.json())
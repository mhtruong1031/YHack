import cv2
import requests

ASUS_PREDICT_URL = "http://10.66.218.112:8000/predict"
CAMERA_INDEX = 0

cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)

if not cap.isOpened():
    raise RuntimeError(f"Could not open camera at index {CAMERA_INDEX}")

print("Press 's' to capture and send frame to ASUS")
print("Press 'q' to quit")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture frame")
        break

    cv2.imshow("Pi Camera Preview", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("s"):
        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            print("Failed to encode frame")
            continue

        files = {
            "file": ("frame.jpg", buffer.tobytes(), "image/jpeg")
        }

        try:
            response = requests.post(ASUS_PREDICT_URL, files=files, timeout=10)
            response.raise_for_status()
            result = response.json()
            print("Prediction result:", result)
        except Exception as e:
            print("Request failed:", e)

    elif key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
import cv2

url = "http://10.66.241.75:8080/video"
cap = cv2.VideoCapture(url)

if not cap.isOpened():
    print("Could not open Samsung camera stream")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to read frame")
        break

    cv2.imshow("Samsung Camera", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
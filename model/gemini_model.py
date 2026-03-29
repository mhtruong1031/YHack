import os
import time
import json
import cv2
from google import genai
from google.genai import types

# =========================
# Config
# =========================
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
MODEL_NAME = "gemini-3-flash-preview"

CAMERA_INDEX = 0

# Make trigger less sensitive by increasing this
MIN_CHANGED_AREA = 12000

COOLDOWN_SECONDS = 3.0
BASELINE_RESET_SECONDS = 2.0

# Optional: set this False if you are running headless
SHOW_PREVIEW = False

client = genai.Client(api_key=GEMINI_API_KEY)

# Structured response schema
response_schema = {
    "type": "object",
    "properties": {
        "predicted_class": {"type": "string"},
        "disposal_category": {
            "type": "string",
            "enum": ["recycle", "compost", "waste"]
        },
        "estimated_value_usd": {"type": "number"}
    },
    "required": ["predicted_class", "disposal_category", "estimated_value_usd"]
}


def call_gemini_with_frame(frame_bgr):
    ok, buffer = cv2.imencode(".jpg", frame_bgr)
    if not ok:
        raise RuntimeError("Failed to encode frame as JPEG")

    prompt = (
        "You are classifying one trash item for a smart waste sorter. "
        "Return JSON only. "
        "Rules: "
        "1. predicted_class should be a short item name. "
        "2. disposal_category must be exactly one of: recycle, compost, waste. "
        "3. estimated_value_usd should be a numeric estimate of the recyclable refund or reuse value. "
        "If the item has no meaningful recycling value, return 0.0. "
        "4. Assume this is a single item in an intake chamber."
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            prompt,
            types.Part.from_bytes(
                data=buffer.tobytes(),
                mime_type="image/jpeg",
            ),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.1,
        ),
    )

    return json.loads(response.text)


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera at index {CAMERA_INDEX}")

    baseline = None
    last_trigger_time = 0
    last_result = None

    print("Running camera baseline detector. Press q to quit.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read frame")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if baseline is None:
                baseline = gray.copy()
                continue

            diff = cv2.absdiff(baseline, gray)
            thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
            changed_area = cv2.countNonZero(thresh)

            now = time.time()
            object_present = changed_area > MIN_CHANGED_AREA

            if not object_present and (now - last_trigger_time) > BASELINE_RESET_SECONDS:
                baseline = gray.copy()

            if object_present and (now - last_trigger_time) > COOLDOWN_SECONDS:
                print(f"Object detected by camera. Changed area: {changed_area}")
                try:
                    result = call_gemini_with_frame(frame)
                    last_result = result
                    print("Gemini result:", result)

                    # Next steps:
                    # route_item(result["disposal_category"])
                    # if result["disposal_category"] == "recycle":
                    #     trigger_plinko(result["estimated_value_usd"])

                except Exception as e:
                    print("Gemini request failed:", e)

                last_trigger_time = time.time()

            if SHOW_PREVIEW:
                display = frame.copy()

                cv2.putText(
                    display,
                    f"Changed area: {changed_area}",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2,
                )

                if last_result is not None:
                    cv2.rectangle(display, (10, 50), (620, 150), (30, 30, 30), -1)
                    cv2.putText(
                        display,
                        f"Item: {last_result['predicted_class']}",
                        (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 255),
                        2,
                    )
                    cv2.putText(
                        display,
                        f"Category: {last_result['disposal_category']}",
                        (20, 110),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2,
                    )
                    cv2.putText(
                        display,
                        f"Estimated value: ${last_result['estimated_value_usd']:.2f}",
                        (20, 140),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 0),
                        2,
                    )

                cv2.imshow("Smart Bin Camera Trigger", display)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
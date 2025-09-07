# python flaskapi3.py

from flask import Flask, request, jsonify
import cv2
import time
from ultralytics import YOLO
import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

print("starting script")

# print("trying to open webcam")
# cap = cv2.VideoCapture(0)
# if not cap.isOpened():
#     print("webcam didn't work")
#     exit()
# print("yippee")

# # loading model
# model_id = "yolov8n.pt"
# try:
#     print("loading model")
#     model = YOLO(model_id)
#     print("model loaded successfully")
# except Exception as e:
#     print(f"error: {e}")
#     cap.release()
#     exit()

target_classes = [
    "person", "car", "traffic cone", "bicycle", "motorcycle", "bus", "truck",
    "traffic light", "stop sign", "parking meter", "bench", "dog", "cat",
    "backpack", "handbag"
]

app = Flask(__name__)

print("trying to open webcam")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("webcam didn't work")
    exit()
print("yippee")

# loading model
model_id = "yolov8n.pt"
try:
    print("loading model")
    model = YOLO(model_id)
    print("model loaded successfully")
except Exception as e:
    print(f"error: {e}")
    cap.release()
    exit()

@app.route("/get_obstacles/", methods=["POST"])
def get_obstacles():
    # webcam
    last_capture = time.time()
    while True:
        ret, frame = cap.read()
        if not ret:
            print("failed to capture frame")
            break
        if time.time() - last_capture > 5:
            print("saving frame")
            frame = cv2.resize(frame, (640, 640))
            cv2.imwrite('frame.jpg', frame)
            if not os.path.exists('frame.jpg'):
                print("frame not saved")
                continue
            print("processing image")
            try:
                results = model(frame, conf=0.4)
                detected_objects = []
                for result in results:
                    for box in result.boxes:
                        cls_id = int(box.cls)
                        label = model.names[cls_id]
                        confidence = box.conf.item()
                        if label in target_classes:
                            detected_objects.append(f"{label} (confidence: {confidence:.2f})")

                description = ""
                if detected_objects:
                    description = f"Detected: {', '.join(detected_objects)}."
                    if "person" in [obj.split()[0] for obj in detected_objects]:
                        description += " people are present in the scene."
                    if any(obj.split()[0] in ["car", "bus", "truck", "motorcycle", "bicycle"] for obj in detected_objects):
                        description += " possible oncoming traffic detected (vehicles)."
                    if "traffic cone" in [obj.split()[0] for obj in detected_objects]:
                        description += " orange cones detected, indicating potential hazards."
                    if any(obj.split()[0] in ["traffic light", "stop sign"] for obj in detected_objects):
                        description += " traffic signs detected, possibly near a crosswalk."
                    if any(obj.split()[0] in ["bench", "parking meter"] for obj in detected_objects):
                        description += " pedestrian area detected, increasing likelihood of a crosswalk."
                    if any(obj.split()[0] in ["dog", "cat"] for obj in detected_objects):
                        description += " animals detected, potential road hazards."
                else:
                    description = "no relevant objects detected."

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 100, 200)
                edge_count = cv2.countNonZero(edges)
                if edge_count > 1500:
                    description += " possible crosswalk detected (striped pattern, edge count: {}).".format(edge_count)

                _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                pothole_detected = any(cv2.contourArea(cnt) > 500 for cnt in contours)
                if pothole_detected:
                    description += " possible pothole detected (dark patch on road)."

                print("description:", description, flush=True)

                # bounding boxes for visualization
                annotated_frame = results[0].plot()
                cv2.imshow('YOLOv8 Detections', annotated_frame)

                return {
                    "description": description,
                    "obstacles": detected_objects
                }

            except Exception as e:
                print(f"error: {e}")
            last_capture = time.time()

        cv2.imshow('webcam feed', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("finished")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, threaded=True)
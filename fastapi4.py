# uvicorn fastapi4:app --reload --port 8000

from huggingface_hub import snapshot_download

# snapshot_download(repo_id="HuggingFaceTB/SmolVLM-500M-Instruct")
# snapshot_download(repo_id="HuggingFaceTB/SmolVLM-256M-Instruct")

import os

from torch import device

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from fastapi import FastAPI
import cv2
import time
from transformers import AutoModelForVision2Seq, AutoProcessor, AutoModelForImageTextToText
from PIL import Image
import torch

print("starting script")

model_id = "HuggingFaceTB/SmolVLM-256M-Instruct"
try:
    print("loading model and processor")
    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModelForImageTextToText.from_pretrained(
        model_id, torch_dtype=torch.float32, device_map="cpu"
    )

    print("model loaded")
except Exception as e:
    print(f"error loading model: {e}")
    exit()

app = FastAPI()


@app.post("/get_obstacles/")
def get_obstacles():
    webcam
    print("trying to open webcam")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("webcam didnt work")
        exit()
    print("yippee")

    app = FastAPI()

    last_capture = time.time()
    while True:
        ret, frame = cap.read()
        if not ret:
            print("failed to capture frame")
            break
        if time.time() - last_capture > 5:
            print("saving frame")
            frame = cv2.resize(frame, (224, 224))
            cv2.imwrite('frame.jpg', frame)
            if not os.path.exists('frame.jpg'):
                print("error: frame not saved.")
                continue
            print("processing image")
            try:
                image = Image.open('frame.jpg').convert("RGB")
                prompt = "<image> Describe what you see in the image."
                # prompt = "<image> Are there any people in the image? If so describe them briefly."
                # prompt = "<image> Identify any potential hazards in the image such as oncoming traffic, potholes, or orange cones."
                # prompt = "<image> Is there a crosswalk in the image? Describe its appearance."

                inputs = processor(
                    text=[prompt], images=[image], return_tensors="pt"
                ).to("cpu")
                print("inputs prepared:", inputs.keys())
                with torch.no_grad():
                    print("running inference")
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=50,
                        temperature=0.7,
                        do_sample=True
                    )
                description = processor.decode(outputs[0], skip_special_tokens=True)

                description = description.replace("<image>", "").strip()
                print("description:", description, flush=True)

                return {"description": description}

            except Exception as e:
                print(f"error during inference: {e}")
            last_capture = time.time()

        cv2.imshow('webcam feed', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    # app = FastAPI()
    #
    # last_capture = time.time()
    # while True:
    #     print("processing image")
    #     try:
    #         image = Image.open('frame.jpg').convert("RGB")
    #         prompt = "<image> Describe what you see in the image."
    #         inputs = processor(
    #             text=[prompt], images=[image], return_tensors="pt"
    #         ).to("cpu")
    #         print("inputs prepared:", inputs.keys())
    #         with torch.no_grad():
    #             print("running inference")
    #             outputs = model.generate(
    #                 **inputs,
    #                 max_new_tokens=50,
    #                 temperature=0.7,
    #                 do_sample=True
    #             )
    #         description = processor.decode(outputs[0], skip_special_tokens=True)
    #
    #         description = description.replace("<image>", "").strip()
    #         print("description:", description, flush=True)
    #
    #         return {"description": description}
    #
    #     except Exception as e:
    #         print(f"error during inference: {e}")

# print(get_obstacles())

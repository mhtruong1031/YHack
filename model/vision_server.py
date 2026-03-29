import os
import io
import cv2
import torch
import torch.nn as nn
from PIL import Image
from fastapi import FastAPI, File, UploadFile
from torchvision import transforms
import numpy as np

MODEL_SAVE_PATH = "/home/asus/YHack/model/garbage_cnn_model.pth"
IMAGE_SIZE = 224
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

DISPOSAL_MAP = {
    "paper": "recycle",
    "cardboard": "recycle",
    "metal": "recycle",
    "plastic": "recycle",
    "green-glass": "recycle",
    "brown-glass": "recycle",
    "white-glass": "recycle",
    "biological": "compost",
    "battery": "waste",
    "trash": "waste",
    "clothes": "waste",
    "shoes": "waste",
}


app = FastAPI()

class CnnModel(nn.Module):
    def __init__(self, num_classes: int):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),

            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2),

            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2),

            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(256 * 14 * 14, 512),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        return self.classifier(self.features(x))

def get_disposal_category(predicted_class):
    return DISPOSAL_MAP.get(predicted_class, "waste")

def load_model():
    checkpoint = torch.load(MODEL_SAVE_PATH, map_location=DEVICE)
    class_names = checkpoint["class_names"]
    model = CnnModel(num_classes=len(class_names)).to(DEVICE)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, class_names

MODEL, CLASS_NAMES = load_model()

TRANSFORM = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    input_tensor = TRANSFORM(image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        outputs = MODEL(input_tensor)
        probs = torch.softmax(outputs, dim=1)
        conf, pred = torch.max(probs, 1)

    predicted_class = CLASS_NAMES[pred.item()]
    confidence = float(conf.item())
    disposal_category = get_disposal_category(predicted_class)

    return {
        "predicted_class": predicted_class,
        "confidence": confidence,
        "disposal_category": disposal_category
    }
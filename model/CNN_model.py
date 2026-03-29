import os
import random

import cv2
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms


# =========================
# Configuration
# =========================
DATASET_DIR = "/home/asus/YHack/model/garbage_classification"
MODEL_SAVE_PATH = "/home/asus/YHack/model/garbage_cnn_model.pth"
IMAGE_SIZE = 224
BATCH_SIZE = 32
EPOCHS = 40
LEARNING_RATE = 3e-4
TRAIN_SPLIT = 0.8
SEED = 42
EARLY_STOP_PATIENCE = 7
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Logitech Brio 100 webcam
CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

# Map dataset classes to disposal groups
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


# =========================
# Device Info
# =========================
print("torch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("CUDA device count:", torch.cuda.device_count())
if torch.cuda.is_available():
    print("Current device:", torch.cuda.current_device())
    print("GPU name:", torch.cuda.get_device_name(0))
    print("Using device: cuda")
else:
    print("Using device: cpu")


# =========================
# Reproducibility
# =========================
def set_seed(seed=42):
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# =========================
# CNN Model
# =========================
class CnnModel(nn.Module):
    def __init__(self, num_classes: int):
        super(CnnModel, self).__init__()

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
        x = self.features(x)
        x = self.classifier(x)
        return x


# =========================
# Data Loaders
# =========================
def get_dataloaders(dataset_dir):
    train_transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    full_dataset = datasets.ImageFolder(root=dataset_dir)
    class_names = full_dataset.classes

    num_samples = len(full_dataset)
    train_size = int(TRAIN_SPLIT * num_samples)
    val_size = num_samples - train_size

    generator = torch.Generator().manual_seed(SEED)
    train_dataset, val_dataset = random_split(
        full_dataset, [train_size, val_size], generator=generator
    )

    train_dataset.dataset = datasets.ImageFolder(
        root=dataset_dir, transform=train_transform
    )
    val_dataset.dataset = datasets.ImageFolder(
        root=dataset_dir, transform=val_transform
    )

    train_loader = DataLoader(
        train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=2
    )
    val_loader = DataLoader(
        val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=2
    )

    return train_loader, val_loader, class_names, train_dataset


# =========================
# Class Weights
# =========================
def compute_class_weights(train_dataset, num_classes):
    counts = [0] * num_classes
    for idx in train_dataset.indices:
        _, label = train_dataset.dataset.samples[idx]
        counts[label] += 1

    counts = torch.tensor(counts, dtype=torch.float)
    weights = counts.sum() / (counts * len(counts))
    return weights


# =========================
# Train and Validate
# =========================
def train_model():
    set_seed(SEED)

    train_loader, val_loader, class_names, train_dataset = get_dataloaders(DATASET_DIR)
    num_classes = len(class_names)

    model = CnnModel(num_classes=num_classes).to(DEVICE)
    class_weights = compute_class_weights(train_dataset, num_classes).to(DEVICE)

    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=2
    )

    best_val_acc = 0.0
    epochs_without_improvement = 0

    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for images, labels in train_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)

        train_loss = running_loss / total
        train_acc = correct / total

        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(DEVICE), labels.to(DEVICE)

                outputs = model(images)
                loss = criterion(outputs, labels)

                val_loss += loss.item() * images.size(0)
                _, preds = torch.max(outputs, 1)
                val_correct += (preds == labels).sum().item()
                val_total += labels.size(0)

        val_loss /= val_total
        val_acc = val_correct / val_total

        scheduler.step(val_acc)

        current_lr = optimizer.param_groups[0]["lr"]
        print(
            f"Epoch [{epoch + 1}/{EPOCHS}] | "
            f"LR: {current_lr:.6f} | "
            f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.4f} | "
            f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.4f}"
        )

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            epochs_without_improvement = 0
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "class_names": class_names,
                },
                MODEL_SAVE_PATH,
            )
            print(f"Best model saved to {MODEL_SAVE_PATH}")
        else:
            epochs_without_improvement += 1

        if epochs_without_improvement >= EARLY_STOP_PATIENCE:
            print("Early stopping triggered.")
            break

    print(f"Training finished. Best validation accuracy: {best_val_acc:.4f}")


# =========================
# Load Model
# =========================
def load_model(model_path):
    checkpoint = torch.load(model_path, map_location=DEVICE)
    class_names = checkpoint["class_names"]

    model = CnnModel(num_classes=len(class_names)).to(DEVICE)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    return model, class_names


# =========================
# Utility Functions
# =========================
def get_disposal_category(predicted_class):
    return DISPOSAL_MAP.get(predicted_class, "waste")


def detect_object_region(frame):
    """
    Detect the main object using contour-based localization.
    Works best when one trash item is clearly visible.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(blur, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges = cv2.dilate(edges, kernel, iterations=2)
    edges = cv2.erode(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    h, w = frame.shape[:2]
    min_area = 0.02 * (h * w)

    valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]
    if not valid_contours:
        return None

    largest = max(valid_contours, key=cv2.contourArea)
    x, y, bw, bh = cv2.boundingRect(largest)

    pad = 10
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(w, x + bw + pad)
    y2 = min(h, y + bh + pad)

    return (x1, y1, x2, y2)


def get_box_color(category):
    if category == "recycle":
        return (0, 255, 0)
    elif category == "compost":
        return (0, 165, 255)
    else:
        return (0, 0, 255)


def draw_label_block(frame, predicted_class, disposal_category, confidence):
    """
    Draw the camera overlay text.
    """
    cv2.rectangle(frame, (10, 10), (450, 145), (30, 30, 30), -1)

    cv2.putText(
        frame,
        f"Classification: {disposal_category.upper()}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        get_box_color(disposal_category),
        2,
    )

    cv2.putText(
        frame,
        f"Item: {predicted_class}",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (255, 255, 255),
        2,
    )

    cv2.putText(
        frame,
        f"Confidence: {confidence * 100:.1f}%",
        (20, 120),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (255, 255, 0),
        2,
    )


# =========================
# Predict one frame
# =========================
def predict_frame(model, frame, class_names):
    transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    box = detect_object_region(frame)

    if box is not None:
        x1, y1, x2, y2 = box
        roi = frame[y1:y2, x1:x2]
    else:
        roi = frame

    rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb)
    input_tensor = transform(pil_image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        outputs = model(input_tensor)
        probs = torch.softmax(outputs, dim=1)
        conf, pred = torch.max(probs, 1)

    predicted_class = class_names[pred.item()]
    confidence = conf.item()
    disposal_category = get_disposal_category(predicted_class)

    return predicted_class, confidence, disposal_category, box


# =========================
# Live Camera Inference
# =========================
def run_camera_inference():
    if not os.path.exists(MODEL_SAVE_PATH):
        raise FileNotFoundError(
            f"Model file not found: {MODEL_SAVE_PATH}. Train first."
        )

    model, class_names = load_model(MODEL_SAVE_PATH)

    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        raise RuntimeError(f"Could not open webcam at index: {CAMERA_INDEX}")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Webcam opened at {actual_width}x{actual_height}")
    print("Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame from webcam")
            break

        predicted_class, confidence, disposal_category, box = predict_frame(
            model, frame, class_names
        )

        color = get_box_color(disposal_category)

        if box is not None:
            x1, y1, x2, y2 = box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
        else:
            cv2.putText(
                frame,
                "No object detected",
                (20, 180),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )

        draw_label_block(frame, predicted_class, disposal_category, confidence)

        cv2.imshow("Trash Classification", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


# =========================
# Main
# =========================
if __name__ == "__main__":
    print("1. Train model")
    print("2. Run live camera inference")
    choice = input("Enter 1 or 2: ").strip()

    if choice == "1":
        train_model()
    elif choice == "2":
        run_camera_inference()
    else:
        print("Invalid choice")
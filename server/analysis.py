"""
Trash classification via PyTorch CnnTrash + camera on the server machine.

Weights: ``torch.save(model.state_dict(), path)`` and set config.CNN_MODEL_WEIGHTS_PATH.
"""

from typing import Literal, cast

import cv2
import numpy as np
import torch

import config
from CnnTrash import CnnTrash

Classification = Literal["waste", "recyclable", "compost"]

_model: CnnTrash | None = None


def get_frame() -> np.ndarray:
    """Capture one frame from OpenCV using CAMERA_DEVICE_INDEX."""
    cap = cv2.VideoCapture(config.CAMERA_DEVICE_INDEX)
    try:
        ok, frame = cap.read()
    finally:
        cap.release()
    if not ok or frame is None:
        raise RuntimeError(
            f"Camera read failed (index {config.CAMERA_DEVICE_INDEX})"
        )
    return frame


def _frame_to_tensor(frame: np.ndarray) -> torch.Tensor:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    size = config.CNN_IMAGE_SIZE
    resized = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_AREA)
    t = torch.from_numpy(resized).permute(2, 0, 1).float() / 255.0
    return t.unsqueeze(0)


def _get_model() -> CnnTrash:
    global _model
    if _model is None:
        n = len(config.CNN_CLASS_LABELS)
        m = CnnTrash(num_classes=n)
        path = (config.CNN_MODEL_WEIGHTS_PATH or "").strip()
        if path:
            state = torch.load(path, map_location="cpu")
            m.load_state_dict(state, strict=True)
        m.eval()
        _model = m
    return _model


def run_cnn(frame: np.ndarray) -> Classification:
    """Run CnnTrash on a BGR frame; map argmax index to label."""
    model = _get_model()
    x = _frame_to_tensor(frame)
    with torch.no_grad():
        logits = model(x)
        idx = int(logits.argmax(dim=1).item())
    return cast(Classification, config.CNN_CLASS_LABELS[idx])


def analysis_with_frame() -> tuple[Classification, bytes]:
    """
    Capture one frame, encode JPEG, classify (or placeholder label if no weights).
    """
    frame = get_frame()
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok or buf is None:
        raise RuntimeError("JPEG encode failed")
    jpeg_bytes = buf.tobytes()
    if not (config.CNN_MODEL_WEIGHTS_PATH or "").strip():
        return "waste", jpeg_bytes
    return run_cnn(frame), jpeg_bytes


def analysis() -> Classification:
    """
    Capture one view and classify trash type.
    Without weights path, returns a placeholder for pipeline testing.
    """
    return analysis_with_frame()[0]

"""PyTorch CNN architecture for trash classification."""

import torch
import torch.nn as nn


class CnnTrash(nn.Module):
    """
    Placeholder until full architecture is implemented.
    Exposes num_classes for analysis.py; forward returns zero logits of the right shape.
    """

    def __init__(self, num_classes: int = 3) -> None:
        super().__init__()
        self.num_classes = num_classes

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b = x.shape[0]
        return torch.zeros(b, self.num_classes, device=x.device, dtype=x.dtype)

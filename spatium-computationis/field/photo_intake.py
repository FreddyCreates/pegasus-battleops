"""
Field — Photo Intake  ⟁
Accepts image files and converts them to base64 for the Ingressus pipeline.
"""

from __future__ import annotations

import base64
from pathlib import Path


def encode_image(path: str | Path) -> str:
    """Read an image file and return base64-encoded bytes."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def prepare_field_photo_input(
    image_path: str | Path,
    project_id: str | None = None,
    submitted_by: str | None = None,
    notes: str = "",
) -> dict:
    """
    Prepare a RawInput-compatible dict from a field photo file.
    Pass the result directly to ingressus.process() via RawInput(**result).
    """
    b64 = encode_image(image_path)
    return {
        "input_type": "photo",
        "content": b64,
        "filename": str(Path(image_path).name),
        "project_id": project_id,
        "submitted_by": submitted_by,
        "metadata": {"notes": notes},
    }

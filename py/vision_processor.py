"""Universal vision processor used by the screen analyzer and executor.

This is intentionally conservative (no heavy ML dependencies). It focuses on
robust preprocessing, OCR (pytesseract), simple UI element detection via
contours/color heuristics, and utilities to verify coordinates.

The interface is minimal: UniversalVisionProcessor.process_image(path) -> dict
"""
from __future__ import annotations
import os
try:
    import cv2
    _CV2_AVAILABLE = True
except Exception:
    cv2 = None
    _CV2_AVAILABLE = False

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except Exception:
    np = None
    _NUMPY_AVAILABLE = False

try:
    from PIL import Image, ImageFilter, ImageEnhance
    _PIL_AVAILABLE = True
except Exception:
    Image = None
    ImageFilter = None
    ImageEnhance = None
    _PIL_AVAILABLE = False
try:
    import pytesseract
    _PYTESS_AVAILABLE = True
except Exception:
    pytesseract = None
    _PYTESS_AVAILABLE = False
import json
import logging
from typing import Dict, Any, List, Tuple, Optional

LOG = logging.getLogger(__name__)


def _pil_from_path(path: str):
    if _PIL_AVAILABLE:
        return Image.open(path).convert("RGB")
    # Minimal fallback: try cv2-based read if available
    if _CV2_AVAILABLE and _NUMPY_AVAILABLE:
        bgr = cv2.imread(path)
        if bgr is None:
            raise FileNotFoundError(path)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        # build a PIL-like object using numpy array wrapper if needed
        from types import SimpleNamespace
        return SimpleNamespace(size=(rgb.shape[1], rgb.shape[0]),
                               convert=lambda mode: None)
    raise RuntimeError("No image backend available (Pillow or OpenCV required)")


class UniversalVisionProcessor:
    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self.confidence_threshold = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.4"))

    def enhance_image(self, pil):
        # Simple enhancement pipeline
        img = pil
        img = img.filter(ImageFilter.MedianFilter(size=3))
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.1)
        return img

    def ocr_image(self, pil) -> List[Dict[str, Any]]:
        if not _PYTESS_AVAILABLE:
            LOG.debug("pytesseract not available, skipping OCR")
            return []
        try:
            data = pytesseract.image_to_data(pil, output_type=pytesseract.Output.DICT)
        except Exception as e:
            LOG.exception("pytesseract failed: %s", e)
            return []

        texts = []
        n = len(data.get("text", []))
        for i in range(n):
            text = data.get("text", [""])[i]
            if not text or text.strip() == "":
                continue
            try:
                conf = float(data.get("conf", ["-1"])[i])
            except Exception:
                conf = -1.0
            x = int(data.get("left", [0])[i])
            y = int(data.get("top", [0])[i])
            w = int(data.get("width", [0])[i])
            h = int(data.get("height", [0])[i])
            texts.append({"text": text.strip(), "conf": conf, "bbox": [x, y, w, h]})
        return texts

    def detect_buttons(self, cv_img) -> List[Dict[str, Any]]:
        buttons: List[Dict[str, Any]] = []
        # If OpenCV or numpy are not available, skip button detection and return empty list.
        if not _CV2_AVAILABLE or not _NUMPY_AVAILABLE:
            LOG.debug("cv2 or numpy not available, skipping button detection")
            return buttons

        # Very simple button detection: look for reasonably-sized rectangular
        # contours with a border-like appearance. This is heuristic.
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        h_img, w_img = gray.shape[:2]
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            area = w * h
            # heuristics: buttons are not tiny, not full-screen, and roughly rectangular
            if area < 400 or area > (w_img * h_img * 0.5):
                continue
            aspect = w / float(h) if h else 0
            if aspect < 0.3 or aspect > 10:
                continue
            # approximate rectangle
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            if len(approx) >= 4 and len(approx) <= 10:
                buttons.append({"bbox": [int(x), int(y), int(w), int(h)], "area": int(area)})

        return buttons

    def process_image(self, image_path: str) -> Dict[str, Any]:
        """Process a screenshot and return a structured analysis dict.

        Keys:
          - texts: list of OCR text dicts (text, conf, bbox)
          - buttons: list of detected buttons with bbox
          - width/height: image size
        """
        pil = _pil_from_path(image_path)
        enhanced = self.enhance_image(pil)

        texts = self.ocr_image(enhanced)

        buttons: List[Dict[str, Any]] = []
        # if cv2/numpy are available try the stronger path
        if _CV2_AVAILABLE and _NUMPY_AVAILABLE:
            try:
                cv_img = cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
                buttons = self.detect_buttons(cv_img)
            except Exception:
                LOG.exception("Error during cv2-based detection; falling back to no-button result")

        w, h = pil.size
        result = {"texts": texts, "buttons": buttons, "width": w, "height": h, "path": image_path}
        return result

    def coords_within(self, x: int, y: int, image_info: Dict[str, Any]) -> bool:
        try:
            w = int(image_info.get("width", 0))
            h = int(image_info.get("height", 0))
            return 0 <= x < w and 0 <= y < h
        except Exception:
            return False

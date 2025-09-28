import cv2
import numpy as np
from typing import Tuple

def detect_marking_roi(img: np.ndarray) -> Tuple[np.ndarray, tuple]:
    """
    Minimal classical detector for prototype:
    - Center crop (60%) + histogram equalization to improve low contrast.
    Returns ROI and bbox (x,y,w,h) in original coordinates.
    """
    h, w = img.shape[:2]
    x1, y1 = int(0.2 * w), int(0.2 * h)
    x2, y2 = int(0.8 * w), int(0.8 * h)
    roi = img[y1:y2, x1:x2].copy()

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    roi_eq = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    return roi_eq, (x1, y1, x2 - x1, y2 - y1)

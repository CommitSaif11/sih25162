from typing import Tuple
import cv2
import numpy as np
import pytesseract

def _preprocess(img: np.ndarray, use_adaptive: bool = True) -> np.ndarray:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.bilateralFilter(g, 5, 50, 50)
    g = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX)
    if use_adaptive:
        th = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY, 25, 10)
        return th
    else:
        _, th = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return th

def ocr_text(
    img: np.ndarray,
    psm: int = 6,
    whitelist: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.+",
    use_adaptive: bool = True,
) -> Tuple[str, float]:
    proc = _preprocess(img, use_adaptive=use_adaptive)
    cfg = f"--oem 3 --psm {psm} -c tessedit_char_whitelist={whitelist}"
    data = pytesseract.image_to_data(proc, output_type=pytesseract.Output.DICT, config=cfg)
    words, confs = [], []
    for txt, conf in zip(data.get("text", []), data.get("conf", [])):
        if txt and txt.strip():
            words.append(txt.strip())
        try:
            c = float(conf)
            if c >= 0:
                confs.append(c)
        except Exception:
            pass
    text = " ".join(words).upper()
    avg_conf = float(sum(confs) / len(confs)) / 100.0 if confs else 0.0
    return text, avg_conf
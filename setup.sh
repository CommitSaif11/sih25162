#!/usr/bin/env bash
set -euo pipefail

# AOI IC Marking Verification — Smart Automation (Software-Only)
# Local init -> push -> run in GitHub Codespaces (no Docker needed)
# Usage:
#   bash setup.sh
# After pushing, open Codespaces and run: bash run.sh

PROJECT_DIR="."
echo "==> Creating project in ${PROJECT_DIR}"

mkdir -p "${PROJECT_DIR}/.devcontainer"
mkdir -p "${PROJECT_DIR}/src/app" "${PROJECT_DIR}/src/pipeline" "${PROJECT_DIR}/src/engine" "${PROJECT_DIR}/src/utils" "${PROJECT_DIR}/src/kb"

# ---------------- .gitignore ----------------
cat > "${PROJECT_DIR}/.gitignore" << 'EOF'
__pycache__/
*.pyc
.venv/
.env
.DS_Store
*.log
EOF

# ---------------- requirements.txt ----------------
cat > "${PROJECT_DIR}/requirements.txt" << 'EOF'
fastapi==0.111.0
uvicorn==0.30.6
pydantic==2.8.2
python-multipart==0.0.9
opencv-python==4.10.0.84
numpy==2.1.1
Pillow==10.4.0
regex==2024.9.11
pyyaml==6.0.2
loguru==0.7.2
watchdog==5.0.2
pytesseract==0.3.13
EOF

# ---------------- run.sh ----------------
cat > "${PROJECT_DIR}/run.sh" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
PORT="${PORT:-8000}"

# If running locally (not Codespaces), create venv and install deps
if [ ! -d ".venv" ]; then
  python3 -m venv .venv || python -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate || true
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Starting API on http://127.0.0.1:${PORT}"
exec uvicorn src.app.main:app --host 0.0.0.0 --port "${PORT}"
EOF
chmod +x "${PROJECT_DIR}/run.sh"

# ---------------- .devcontainer/devcontainer.json ----------------
cat > "${PROJECT_DIR}/.devcontainer/devcontainer.json" << 'EOF'
{
  "name": "AOI IC Marking (Python)",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "postCreateCommand": "sudo apt-get update && sudo apt-get install -y libgl1 libglib2.0-0 tesseract-ocr libzbar0 && pip install --upgrade pip && pip install -r requirements.txt",
  "forwardPorts": [8000],
  "portsAttributes": {
    "8000": {
      "label": "AOI API",
      "onAutoForward": "openBrowser"
    }
  },
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-toolsai.jupyter"
      ]
    }
  }
}
EOF

# ---------------- README.md ----------------
cat > "${PROJECT_DIR}/README.md" << 'EOF'
# AOI IC Marking Verification — Smart Automation (Codespaces Prototype)

Run in GitHub Codespaces
1) Push this repo and open it in Codespaces (Code > Create codespace on main).
2) Wait for setup (installs OpenCV + Tesseract + Python deps).
3) Start API: `bash run.sh`
4) Open forwarded URL → `/` for upload form, or test via:
   curl -F "file=@/workspaces/<repo>/sample.jpg" -F "part_id=example_part" http://127.0.0.1:8000/inspect

Endpoints
- GET /health
- GET /           (simple HTML upload form)
- POST /inspect   (multipart: file + part_id)

KB
- Edit/add YAML files in src/kb/. Example: src/kb/example_part.yaml

Notes
- OCR uses Tesseract (pytesseract) by default for lightweight setup.
- You can later add EasyOCR/PaddleOCR if needed.
EOF

# ---------------- src/app/main.py ----------------
cat > "${PROJECT_DIR}/src/app/main.py" << 'EOF'
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from loguru import logger
import cv2
import numpy as np

from src.pipeline.detector import detect_marking_roi
from src.pipeline.ocr import ocr_text
from src.engine.decision import decide
from src.engine.kb import load_kb

app = FastAPI(title="AOI IC Marking Verification (Smart Automation)")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def index():
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>AOI IC Marking Verification</title>
<style>
body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; }
.card { max-width: 720px; padding: 1.5rem; border: 1px solid #e5e7eb; border-radius: 12px; }
label { display:block; margin-top: 1rem; font-weight:600; }
button { margin-top: 1rem; padding: 0.6rem 1rem; border:0; border-radius:8px; background:#0B3D91; color:#fff; cursor:pointer; }
small { color:#6b7280; }
</style>
</head>
<body>
<h2>AOI IC Marking Verification</h2>
<div class="card">
  <form id="f" enctype="multipart/form-data" method="post" action="/inspect">
    <label>Part ID <small>(e.g., example_part)</small></label>
    <input type="text" name="part_id" value="example_part" required>
    <label>IC Image</label>
    <input type="file" name="file" accept="image/*" required>
    <button type="submit">Inspect</button>
  </form>
  <pre id="out" style="white-space:pre-wrap;margin-top:1rem;"></pre>
</div>
<script>
const form = document.getElementById('f');
const out = document.getElementById('out');
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  out.textContent = "Processing...";
  const fd = new FormData(form);
  const res = await fetch('/inspect', { method: 'POST', body: fd });
  const json = await res.json();
  out.textContent = JSON.stringify(json, null, 2);
});
</script>
</body>
</html>"""

@app.post("/inspect")
async def inspect(file: UploadFile = File(...), part_id: str = Form(...)):
    kb = load_kb(part_id)
    if kb is None:
        return JSONResponse({"verdict": "Suspect", "reason_codes": ["KB_PART_UNKNOWN"], "scores": {}, "extracted": {}}, status_code=200)

    content = await file.read()
    npimg = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if img is None:
        return JSONResponse({"error": "Invalid image"}, status_code=400)

    roi, bbox = detect_marking_roi(img)
    text, ocr_conf = ocr_text(roi)

    logger.info(f"OCR text='{text}' conf={ocr_conf:.3f} bbox={bbox}")
    decision = decide(text=text, kb=kb, extra={"ocr_conf": ocr_conf})
    decision["bbox"] = bbox
    decision["extracted"] = {"text": text}
    return JSONResponse(decision, status_code=200)
EOF

# ---------------- src/pipeline/detector.py ----------------
cat > "${PROJECT_DIR}/src/pipeline/detector.py" << 'EOF'
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
EOF

# ---------------- src/pipeline/ocr.py ----------------
cat > "${PROJECT_DIR}/src/pipeline/ocr.py" << 'EOF'
from typing import Tuple
import cv2
import numpy as np
import pytesseract

def _preprocess(img: np.ndarray) -> np.ndarray:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.bilateralFilter(g, 5, 50, 50)
    g = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX)
    # Adaptive threshold helps with laser-etched low contrast
    th = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                               cv2.THRESH_BINARY, 25, 10)
    return th

def ocr_text(img: np.ndarray) -> Tuple[str, float]:
    proc = _preprocess(img)
    cfg = "--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.+"
    # Use image_to_data to compute average confidence
    data = pytesseract.image_to_data(proc, output_type=pytesseract.Output.DICT, config=cfg)
    words = []
    confs = []
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
EOF

# ---------------- src/engine/decision.py ----------------
cat > "${PROJECT_DIR}/src/engine/decision.py" << 'EOF'
import re
from typing import Dict, Any, List

def _match_regex(text: str, pattern: str) -> bool:
    if not pattern:
        return True
    try:
        return re.search(pattern, text) is not None
    except re.error:
        return False

def decide(text: str, kb: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    reason_codes: List[str] = []
    scores = {"ocr_conf": float(extra.get("ocr_conf", 0.0))}
    text_up = (text or "").upper()

    # Part code
    part_ok = _match_regex(text_up, kb.get("patterns", {}).get("part_code", ""))
    if not part_ok:
        reason_codes.append("RULE_PARTCODE_FAIL")

    # Date code
    dc_pat = kb.get("patterns", {}).get("date_code", "")
    dc_ok = _match_regex(text_up, dc_pat)
    if dc_pat and not dc_ok:
        reason_codes.append("RULE_DATECODE_FAIL")

    # Lot code
    lc_pat = kb.get("patterns", {}).get("lot_code", "")
    lc_ok = _match_regex(text_up, lc_pat)
    if lc_pat and not lc_ok:
        reason_codes.append("RULE_LOTCODE_FAIL")

    # Logo hint (simple contains)
    logo = kb.get("logo_hint", "")
    logo_ok = True
    if logo:
        logo_ok = logo.upper() in text_up
        if not logo_ok:
            reason_codes.append("RULE_LOGO_FAIL")

    penalties = len(reason_codes)
    ocr_conf = scores["ocr_conf"]
    base = 0.8 if part_ok else 0.4
    final_conf = max(0.0, min(1.0, base * (0.6 + 0.4 * ocr_conf) - 0.15 * penalties))
    scores["final_conf"] = final_conf

    if penalties == 0 and final_conf >= 0.75:
        verdict = "Genuine"
    elif penalties <= 1 and final_conf >= 0.5:
        verdict = "Suspect"
    else:
        verdict = "Reject"

    return {"verdict": verdict, "reason_codes": reason_codes, "scores": scores}
EOF

# ---------------- src/engine/kb.py ----------------
cat > "${PROJECT_DIR}/src/engine/kb.py" << 'EOF'
import os
import yaml
from typing import Optional, Dict, Any

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "kb")

def load_kb(part_id: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(KB_DIR, f"{part_id}.yaml")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
EOF

# ---------------- src/kb/example_part.yaml ----------------
cat > "${PROJECT_DIR}/src/kb/example_part.yaml" << 'EOF'
part_id: example_part
oem: "Acme Semiconductor"
part_number: "ACM1234"
package: "QFN-48"
logo_hint: "ACME"
patterns:
  part_code: "\\bACM1234\\b"
  date_code: "\\b(24|25)[0-5][0-9]\\b"     # YYWW
  lot_code: "\\bL[0-9A-Z]{4,6}\\b"
notes: |
  Example KB entry. Update regex patterns per OEM marking guide.
EOF

# ---------------- src/utils/__init__.py ----------------
cat > "${PROJECT_DIR}/src/utils/__init__.py" << 'EOF'
# utils package
EOF

echo "==> Done. Next steps:"
echo "1) git add ."
echo "2) git commit -m 'init: aoi smart automation prototype'"
echo "3) git branch -M main && git remote add origin <your_repo_url> && git push -u origin main"
echo "4) Open the repo in GitHub Codespaces"
echo "5) In Codespaces terminal: bash run.sh"
echo "   - Then open the forwarded Port 8000 URL (auto-opens) and use the upload form."
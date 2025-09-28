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

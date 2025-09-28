from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
from typing import Optional

from src.pipeline.detector import detect_marking_roi
from src.pipeline.ocr import ocr_text
from src.engine.decision import decide
from src.engine.kb import load_kb, list_kb

app = FastAPI(title="AOI IC Marking Verification (Smart Automation)")

# Serve static assets
app.mount("/static", StaticFiles(directory="src/static"), name="static")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/kb")
def kb_list():
    return {"parts": list_kb()}

@app.get("/", response_class=HTMLResponse)
def index():
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>AOI IC Marking Verification</title>
<link rel="stylesheet" href="/static/css/styles.css">
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<header class="topbar">
  <div class="brand">Smart Automation — IC Top-Mark Verification</div>
  <nav class="links">
    <a href="/docs" target="_blank">API Docs</a>
    <a href="/health" target="_blank">Health</a>
    <a href="https://github.com/CommitSaif11/sih25162" target="_blank">Repo</a>
  </nav>
</header>

<main class="container">
  <section class="card">
    <h2>Inspect Image</h2>

    <div class="controls">
      <div class="field">
        <label for="part_id">Part ID</label>
        <select id="part_id"></select>
        <small>From KB (yaml files). Choose or type your own.</small>
      </div>

      <details class="advanced">
        <summary>Advanced OCR Options</summary>
        <div class="grid">
          <div class="field">
            <label for="psm">Tesseract PSM</label>
            <select id="psm">
              <option value="6" selected>6 (Assume a block of text)</option>
              <option value="7">7 (Single text line)</option>
              <option value="8">8 (Single word)</option>
              <option value="11">11 (Sparse text)</option>
              <option value="13">13 (Raw line)</option>
            </select>
          </div>
          <div class="field">
            <label for="adaptive">Adaptive Threshold</label>
            <label class="switch">
              <input type="checkbox" id="adaptive" checked>
              <span class="slider"></span>
            </label>
          </div>
          <div class="field">
            <label for="whitelist">Whitelist</label>
            <input id="whitelist" type="text" value="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.+">
          </div>
        </div>
      </details>
    </div>

    <div class="uploader" id="dropzone">
      <input id="file" type="file" accept="image/*" hidden>
      <p><strong>Drag & drop</strong> an image here or <button id="chooseBtn" type="button">Choose File</button></p>
      <small>PNG/JPG recommended. Centered marking works best with current prototype.</small>
    </div>

    <div class="preview-row">
      <div class="panel">
        <h3>Preview</h3>
        <div class="stage">
          <img id="preview" alt="preview" />
          <canvas id="overlay"></canvas>
        </div>
      </div>
      <div class="panel">
        <h3>Result</h3>
        <div id="result" class="result">
          <div class="muted">No result yet.</div>
        </div>
        <div class="actions">
          <button id="inspectBtn" type="button" class="primary">Inspect</button>
          <button id="clearBtn" type="button" class="ghost">Clear</button>
        </div>
      </div>
    </div>
  </section>

  <section class="card">
    <div class="row">
      <h2>History</h2>
      <div class="spacer"></div>
      <button id="exportCsv" class="ghost">Export CSV</button>
      <button id="copyJson" class="ghost">Copy Last JSON</button>
    </div>
    <div class="table-wrap">
      <table id="history">
        <thead>
          <tr>
            <th>Time</th>
            <th>Part</th>
            <th>Verdict</th>
            <th>Conf</th>
            <th>Reasons</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  </section>
</main>

<footer class="footer">
  <small>Built for BEL environments. Offline-capable prototype.</small>
</footer>

<script src="/static/js/app.js"></script>
</body>
</html>"""

@app.post("/inspect")
async def inspect(
    file: UploadFile = File(...),
    part_id: str = Form(...),
    psm: int = Form(6),
    adaptive: int = Form(1),  # 1=true, 0=false
    whitelist: Optional[str] = Form(None),
):
    kb = load_kb(part_id)
    if kb is None:
        return JSONResponse(
            {
                "verdict": "Suspect",
                "reason_codes": ["KB_PART_UNKNOWN"],
                "scores": {},
                "extracted": {},
            },
            status_code=200,
        )

    content = await file.read()
    npimg = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if img is None:
        return JSONResponse({"error": "Invalid image"}, status_code=400)

    roi, bbox = detect_marking_roi(img)
    text, ocr_conf = ocr_text(
        roi,
        psm=psm,
        whitelist=whitelist or "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.+",
        use_adaptive=bool(adaptive),
    )

    decision = decide(text=text, kb=kb, extra={"ocr_conf": ocr_conf})
    decision["bbox"] = bbox
    decision["extracted"] = {"text": text}
    return JSONResponse(decision, status_code=200)
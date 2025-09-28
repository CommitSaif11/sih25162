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

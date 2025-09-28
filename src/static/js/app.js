const $ = (q) => document.querySelector(q);
const partSel = $("#part_id");
const fileInput = $("#file");
const chooseBtn = $("#chooseBtn");
const dz = $("#dropzone");
const img = $("#preview");
const overlay = $("#overlay");
const inspectBtn = $("#inspectBtn");
const clearBtn = $("#clearBtn");
const resultBox = $("#result");
const psmSel = $("#psm");
const adaptiveChk = $("#adaptive");
const whitelistIn = $("#whitelist");
const historyTable = $("#history tbody");
const exportCsvBtn = $("#exportCsv");
const copyJsonBtn = $("#copyJson");

let lastJson = null;
let currentBlob = null;
let history = [];

async function loadKB() {
  try {
    const r = await fetch("/kb");
    const j = await r.json();
    const parts = j.parts || [];
    // make it editable: allow typing as well
    partSel.innerHTML = "";
    for (const p of parts) {
      const opt = document.createElement("option");
      opt.value = p.part_id;
      opt.textContent = p.part_id + (p.part_number ? ` (${p.part_number})` : "");
      partSel.appendChild(opt);
    }
    // default to example_part if available, else first
    const idx = parts.findIndex(p => p.part_id === "example_part");
    if (idx >= 0) partSel.selectedIndex = idx;
  } catch (e) {
    // fallback to example_part
    const opt = document.createElement("option");
    opt.value = "example_part";
    opt.textContent = "example_part";
    partSel.appendChild(opt);
  }
}

// File selection handlers
chooseBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => previewFile(fileInput.files?.[0]));
["dragenter","dragover"].forEach(ev => dz.addEventListener(ev, e => {e.preventDefault(); dz.classList.add("drag");}));
["dragleave","drop"].forEach(ev => dz.addEventListener(ev, e => {e.preventDefault(); dz.classList.remove("drag");}));
dz.addEventListener("drop", (e) => {
  const f = e.dataTransfer.files?.[0];
  if (f) previewFile(f);
});

function previewFile(f) {
  if (!f) return;
  currentBlob = f;
  const url = URL.createObjectURL(f);
  img.src = url;
  img.onload = () => {
    img.style.display = "block";
    overlay.width = img.naturalWidth;
    overlay.height = img.naturalHeight;
    overlay.style.width = img.clientWidth + "px";
    overlay.style.height = img.clientHeight + "px";
    overlay.style.display = "block";
    clearOverlay();
  };
}

function clearOverlay() {
  const ctx = overlay.getContext("2d");
  ctx.clearRect(0,0,overlay.width, overlay.height);
}

function drawBBox(bbox) {
  if (!bbox || !img.complete) return;
  const [x,y,w,h] = bbox;
  const ctx = overlay.getContext("2d");
  clearOverlay();
  ctx.lineWidth = Math.max(2, Math.round(overlay.width / 400));
  ctx.strokeStyle = "#3b82f6";
  ctx.fillStyle = "rgba(59,130,246,0.15)";
  ctx.strokeRect(x,y,w,h);
  ctx.fillRect(x,y,w,h);
}

function verdictBadge(verdict) {
  const c = verdict === "Genuine" ? "ok" : verdict === "Suspect" ? "warn" : "err";
  return `<span class="badge ${c}">${verdict}</span>`;
}
function confBadge(label, v) {
  const c = v >= 0.75 ? "ok" : v >= 0.5 ? "warn" : "err";
  return `<span class="badge ${c}">${label}: ${(v*100).toFixed(1)}%</span>`;
}
function reasonsChips(reasons) {
  if (!reasons || !reasons.length) return `<span class="badge ok">No rule failures</span>`;
  return reasons.map(r => `<span class="badge err">${r}</span>`).join(" ");
}

function renderResult(j) {
  lastJson = j;
  const v = j.verdict || "Unknown";
  const ocr = j.scores?.ocr_conf ?? 0;
  const f = j.scores?.final_conf ?? 0;
  const text = j.extracted?.text || "";
  resultBox.innerHTML = `
    <div style="margin-bottom:8px">${verdictBadge(v)} ${confBadge("Final", f)} ${confBadge("OCR", ocr)}</div>
    <div class="kv">
      <div>Extracted Text</div><div>${text || "<span class='muted'>—</span>"}</div>
      <div>Reasons</div><div>${reasonsChips(j.reason_codes || [])}</div>
      <div>BBox</div><div>${(j.bbox || []).join(", ") || "<span class='muted'>—</span>"}</div>
      <div>Raw JSON</div><div><code id="rawJson" style="font-size:12px">${escapeHtml(JSON.stringify(j))}</code></div>
    </div>
  `;
  if (j.bbox) drawBBox(j.bbox);
  addHistory(j);
}

function addHistory(j) {
  const tr = document.createElement("tr");
  const verdict = j.verdict || "Unknown";
  const conf = j.scores?.final_conf ?? 0;
  const reasons = (j.reason_codes || []).join(" ");
  const ts = new Date().toLocaleTimeString();
  const part = partSel.value;
  tr.innerHTML = `<td>${ts}</td><td>${part}</td><td>${verdict}</td><td>${(conf*100).toFixed(1)}%</td><td>${reasons}</td>`;
  historyTable.prepend(tr);
  history.unshift({ ts, part, verdict, conf, reasons, json: j });
}

function exportCSV() {
  if (!history.length) return;
  const rows = [["time","part","verdict","final_conf","reasons"]];
  history.forEach(h => rows.push([h.ts, h.part, h.verdict, h.conf, h.reasons]));
  const csv = rows.map(r => r.map(x => `"${String(x).replace(/"/g,'""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], {type:"text/csv"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "inspection_history.csv";
  a.click();
}

function copyLastJson() {
  if (!lastJson) return;
  const s = JSON.stringify(lastJson, null, 2);
  navigator.clipboard.writeText(s);
}

function escapeHtml(s){return s.replace(/[&<>'"]/g,c=>({ "&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;" }[c]))}

inspectBtn.addEventListener("click", async () => {
  if (!currentBlob) {
    alert("Choose an image first.");
    return;
  }
  const fd = new FormData();
  fd.append("part_id", partSel.value || "example_part");
  fd.append("file", currentBlob);
  fd.append("psm", psmSel.value);
  fd.append("adaptive", adaptiveChk.checked ? "1" : "0");
  fd.append("whitelist", whitelistIn.value || "");
  resultBox.innerHTML = `<div class="muted">Processing...</div>`;
  try {
    const res = await fetch("/inspect", { method: "POST", body: fd });
    const j = await res.json();
    renderResult(j);
  } catch (e) {
    resultBox.innerHTML = `<div class="badge err">Request failed</div>`;
  }
});

clearBtn.addEventListener("click", () => {
  currentBlob = null;
  img.removeAttribute("src");
  img.style.display = "none";
  overlay.style.display = "none";
  clearOverlay();
  resultBox.innerHTML = `<div class="muted">No result yet.</div>`;
});

exportCsvBtn.addEventListener("click", exportCSV);
copyJsonBtn.addEventListener("click", copyLastJson);

// Init
loadKB();
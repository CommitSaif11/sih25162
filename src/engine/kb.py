import os
import yaml
from typing import Optional, Dict, Any, List

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "kb")

def load_kb(part_id: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(KB_DIR, f"{part_id}.yaml")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def list_kb() -> List[Dict[str, str]]:
    parts = []
    if not os.path.isdir(KB_DIR):
        return parts
    for fn in sorted(os.listdir(KB_DIR)):
        if not fn.endswith(".yaml"):
            continue
        path = os.path.join(KB_DIR, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                y = yaml.safe_load(f) or {}
            parts.append({
                "part_id": os.path.splitext(fn)[0],
                "oem": str(y.get("oem", "")),
                "part_number": str(y.get("part_number", "")),
            })
        except Exception:
            parts.append({"part_id": os.path.splitext(fn)[0], "oem": "", "part_number": ""})
    return parts
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

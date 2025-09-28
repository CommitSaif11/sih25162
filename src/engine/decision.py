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

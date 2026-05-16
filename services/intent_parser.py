# ================================================================
# 📁 intent_parser.py
# 📝 Purpose: LLM-first price/gender/brand extraction from user text
#             with regex fallback for speed/reliability.
# ================================================================

import re
import json
from typing import Dict
from services.llm_router import call_llm


_BRANDS = [
    "j.", "khaadi", "sapphire", "alkaram", "bonanza", "gul ahmed",
    "ndure", "sana safinaz", "cross stitch", "maria b", "generation",
    "limelight", "ego", "outfitters", "breakout",
]


def _parse_intent_regex(text: str) -> Dict:
    """
    Fallback: extract structured search params via regex/keyword matching.
    Returns: {brand, query, price_min, price_max, gender, category}
    """
    text_lower = text.lower()
    price_min, price_max = None, None

    # Price: "under/below/max/upto 5000"
    m = re.search(r'(?:under|below|less\s*than|max|upto|up\s*to|tak)\s*(\d+)', text_lower)
    if m:
        price_max = int(m.group(1))

    # Price: "above/over/more than/min 1000"
    m = re.search(r'(?:above|over|more\s*than|min|se\s*zyada)\s*(\d+)', text_lower)
    if m:
        price_min = int(m.group(1))

    # Price range: "3000 to 8000" or "3000 - 8000"
    m = re.search(r'(\d+)\s*(?:to|-)\s*(\d+)', text_lower)
    if m:
        price_min, price_max = int(m.group(1)), int(m.group(2))

    # Gender
    gender = None
    if any(kw in text_lower for kw in ["men", "male", "gents", "mard", "boy", "ladka"]):
        gender = "men"
    elif any(kw in text_lower for kw in ["women", "female", "ladies", "aurat", "girl", "ladki"]):
        gender = "women"

    # Category
    category = None
    if any(kw in text_lower for kw in ["shirt", "kurta", "kameez", "dupatta", "lawn", "suit",
                                        "kurti", "shalwar", "trouser", "jeans"]):
        category = "clothing"
    elif any(kw in text_lower for kw in ["shoe", "sneaker", "sandal", "khussa", "chappal",
                                          "loafer", "heel"]):
        category = "footwear"
    elif any(kw in text_lower for kw in ["perfume", "attar", "cologne", "fragrance"]):
        category = "fragrance"

    # Brand detection
    brand = None
    for b in _BRANDS:
        if b in text_lower:
            brand = b.title()
            break

    return {
        "brand":     brand,
        "query":     text,
        "price_min": price_min,
        "price_max": price_max,
        "gender":    gender,
        "category":  category,
    }


def parse_intent_with_llm(text: str) -> Dict:
    """
    Primary intent parser — calls the LLM to extract structured params.
    Falls back to _parse_intent_regex on any error.
    """
    prompt = (
        "Extract structured search parameters from this user message.\n"
        "Return ONLY valid JSON (no markdown, no extra text):\n"
        '{"query": string, "price_min": int|null, "price_max": int|null, '
        '"gender": "men"|"women"|null, "brand": string|null}\n\n'
        f"Message: {text}"
    )
    try:
        resp = call_llm([{"role": "user", "content": prompt}], max_tokens=150)
        resp = re.sub(r'```json\s*|\s*```', '', resp).strip()
        data = json.loads(resp)
        data.setdefault("query",     text)
        data.setdefault("price_min", None)
        data.setdefault("price_max", None)
        data.setdefault("gender",    None)
        data.setdefault("brand",     None)
        # Carry over category from regex for footwear/fragrance detection
        regex_result = _parse_intent_regex(text)
        data.setdefault("category", regex_result.get("category"))
        return data
    except Exception:
        return _parse_intent_regex(text)


def parse_intent(text: str) -> Dict:
    """Public entry-point — LLM-first with regex fallback."""
    return parse_intent_with_llm(text)
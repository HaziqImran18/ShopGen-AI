"""
Vision Service — Powered by Google Gemini 2.0 Flash
─────────────────────────────────────────────────────
User sends a clothing photo → Gemini identifies it → Firebase search

Why Gemini 2.0 Flash:
  - Free tier (no credit card needed for dev)
  - Best-in-class vision quality
  - Faster than most alternatives
  - Handles Pakistani clothing accurately

Setup:
  1. Go to https://aistudio.google.com/apikey
  2. Click "Create API key"
  3. Add to .env: GEMINI_API_KEY=AIza...
  4. pip install google-generativeai
"""

import os
import base64
import requests
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-flash")


def analyze_clothing_image(image_url: str) -> dict:
    """
    Downloads image from Twilio, sends to Gemini 2.0 Flash vision model,
    extracts structured clothing attributes for Firebase product search.

    Returns dict: {category, gender, color, occasion, description}
    """
    try:
        # Download image from Twilio (requires auth)
        twilio_sid   = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")

        response = requests.get(
            image_url,
            auth=(twilio_sid, twilio_token),
            timeout=30
        )
        response.raise_for_status()

        image_bytes = response.content
        content_type = response.headers.get("Content-Type", "image/jpeg")
        print(f"[VISION] Downloaded image: {len(image_bytes)} bytes ({content_type})")

        # Send to Gemini with inline image data
        result = gemini_model.generate_content([
            {
                "inline_data": {
                    "mime_type": content_type,
                    "data": base64.b64encode(image_bytes).decode("utf-8")
                }
            },
            """Analyze this clothing item and return ONLY a valid JSON object with these exact fields:
{
  "category": one of ["shalwar kameez", "kurta", "lawn suit", "dress", "shirt", "trousers", "dupatta", "saree", "jacket", "other"],
  "gender": one of ["women", "men", "unisex"],
  "color": the main color as a single word in lowercase (e.g. "black", "white", "red", "blue", "green", "pink", "yellow", "grey", "brown", "maroon", "navy", "beige"),
  "occasion": one of ["casual", "formal", "wedding", "eid", "office", null],
  "description": a brief 1-sentence description of the garment
}
Return ONLY the JSON. No markdown, no explanation, no code blocks."""
        ])

        raw = result.text.strip()
        print(f"[VISION] Gemini response: {raw}")

        # Strip markdown code fences if Gemini adds them anyway
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)
        print(f"[VISION] Extracted: {parsed}")
        return parsed

    except json.JSONDecodeError as e:
        print(f"[VISION ERROR] JSON parse failed: {e} | raw: {raw if 'raw' in dir() else 'N/A'}")
        return {"category": None, "gender": None, "color": None, "occasion": None, "description": "clothing item"}

    except Exception as e:
        print(f"[VISION ERROR] {e}")
        return {"category": None, "gender": None, "color": None, "occasion": None, "description": "clothing item"}


def build_search_params_from_vision(vision_result: dict) -> dict:
    """Converts Gemini output into Firebase search params."""
    return {
        "category": vision_result.get("category"),
        "gender":   vision_result.get("gender") if vision_result.get("gender") != "unisex" else None,
        "color":    vision_result.get("color"),
        "occasion": vision_result.get("occasion"),
        "max_price": None,
        "min_price": None,
        "brand":     None,
    }
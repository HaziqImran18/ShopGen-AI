import hashlib
import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def debug_log(msg: str):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[TRACK {timestamp}] {msg}")


# ─── In-memory cache for fast lookups (read-through) ───────────────────────────
_tracking_cache: dict = {}
_TRACKING_TTL = 604800  # 7 days


def _get_firestore_db():
    """Lazy import to avoid circular dependencies"""
    try:
        from services.firebase_service import _get_db
        return _get_db()
    except:
        return None


def generate_tracking_link(
    user_id: str,
    product_id: str,
    position: int,
    original_url: str,
    search_context: dict = None,
) -> str:
    """Generate a short tracking URL stored in Firestore (with memory cache)."""
    context = search_context or {}
    unique_str = f"{user_id}{product_id}{position}{original_url}{time.time()}"
    short_id = hashlib.md5(unique_str.encode()).hexdigest()[:16]
    
    payload = {
        "user_id":      user_id,
        "product_id":   product_id,
        "position":     position,
        "original_url": original_url,
        "query":        context.get("query", ""),
        "gender":       context.get("gender", ""),
        "price_max":    context.get("price_max"),
        "category":     context.get("category", ""),
        "brand":        context.get("brand", ""),
        "price":        context.get("price", 0),
        "created_at":   time.time(),
        "expires_at":   time.time() + _TRACKING_TTL,
    }
    
    # Store in memory cache
    _tracking_cache[short_id] = payload
    
    # Persist to Firestore
    db = _get_firestore_db()
    if db is not None:
        try:
            db.collection("short_links").document(short_id).set(payload)
            debug_log(f"Saved tracking link {short_id} to Firestore")
        except Exception as e:
            debug_log(f"Failed to save to Firestore: {e}")
    
    return f"{BASE_URL}/track/{short_id}"


def decode_tracking_id(short_id: str) -> dict:
    """Decode a short tracking ID from cache or Firestore."""
    # Check memory cache first
    if short_id in _tracking_cache:
        payload = _tracking_cache[short_id]
        if time.time() < payload.get("expires_at", 0):
            return payload
        else:
            del _tracking_cache[short_id]  # Clean expired from cache
    
    # Fall back to Firestore
    db = _get_firestore_db()
    if db is not None:
        try:
            doc = db.collection("short_links").document(short_id).get()
            if doc.exists:
                payload = doc.to_dict()
                if time.time() < payload.get("expires_at", 0):
                    # Restore to cache for future fast lookups
                    _tracking_cache[short_id] = payload
                    return payload
                else:
                    debug_log(f"Expired tracking ID: {short_id}")
            else:
                debug_log(f"Tracking ID not found: {short_id}")
        except Exception as e:
            debug_log(f"Firestore lookup failed: {e}")
    
    raise KeyError(f"Tracking ID '{short_id}' not found or expired")


def log_click_event(data: dict, **kwargs) -> None:
    """Log a product click event to Firestore and update behavior profile."""
    debug_log(f"Click: product={str(data.get('product_id', '?'))[:8]} pos={data.get('position', '?')}")
    try:
        from services.firebase_service import _get_db, get_user_data, save_user_data
        from services.rl_service import log_interaction

        firestore_db = _get_db()

        # ── 1. Write click event to Firestore ─────────────────────────────────
        if firestore_db is not None:
            firestore_db.collection("click_events").add({
                "user_id":      data.get("user_id", ""),
                "product_id":   data.get("product_id", ""),
                "position":     data.get("position", 0),
                "search_query": data.get("query", ""),
                "timestamp":    datetime.utcnow().isoformat(),
            })
            debug_log(f"click_event saved for product {str(data.get('product_id', ''))[:8]}")

        # ── 2. Update behavior_profile ─────────────────────────────────────────
        user_id = data.get("user_id", "")
        if user_id:
            user_data = get_user_data(user_id)
            profile   = user_data.get("behavior_profile", {})
            product   = {
                "product_id": data.get("product_id", ""),
                "category":   data.get("category"),
                "brand":      data.get("brand"),
                "price":      data.get("price"),
            }
            new_profile = log_interaction(profile, "click", product)
            save_user_data(user_id, {"behavior_profile": new_profile})
            debug_log(f"behavior_profile updated for {user_id}")

    except Exception as e:
        debug_log(f"Click log error: {e}")
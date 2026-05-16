# ================================================================
# 📁 rl_service.py
# 📝 Purpose: UCB-based product ranking, fashion context building,
#             outfit suggestions, and interaction logging for RL.
# ================================================================

import math
import time
from datetime import datetime
from typing import Dict, List, Optional

# ─── Constants ────────────────────────────────────────────────────────────────
DECAY_HALF_LIFE_DAYS = 30
UCB_EXPLORATION_C    = 1.5

# Short-lived decay cache (avoids recomputing every call)
_decay_cache = {"profile": None, "result": None, "ts": 0.0}
_DECAY_TTL   = 60  # 1 minute


# ================================================================
# 🏗️ PROFILE HELPERS
# ================================================================

def _empty_profile() -> Dict:
    return {
        "categories":         {},
        "brands":             {},
        "subcategories":      {},
        "impressions":        {},
        "total_interactions": 0,
        "last_active":        None,
        "style_preference":   None,
        "avg_price":          0,
        "price_interactions": 0,
    }


def init_profile_from_onboarding(style: str) -> Dict:
    """Seed the behavior profile from the user's chosen style."""
    profile = _empty_profile()
    profile["style_preference"] = style.lower()
    seeds = {
        "casual":     {"shirt": 3, "trouser": 2, "sneakers": 2},
        "ethnic":     {"dupatta": 3, "kurta": 2},
        "formal":     {"shirt": 3, "trouser": 3},
        "streetwear": {"shirt": 3, "jeans": 2, "sneakers": 3},
    }
    profile["subcategories"] = seeds.get(style.lower(), {})
    return profile


# ================================================================
# ⏳ TIME DECAY (cached)
# ================================================================

def _apply_time_decay(profile: Dict) -> Dict:
    global _decay_cache
    now = time.time()
    if _decay_cache["profile"] is profile and (now - _decay_cache["ts"]) < _DECAY_TTL:
        return _decay_cache["result"]

    last_str = profile.get("last_active")
    if not last_str:
        return profile
    try:
        last_dt = datetime.strptime(last_str, "%Y-%m-%d")
    except ValueError:
        return profile

    days = (datetime.utcnow() - last_dt).days
    if days <= 0:
        return profile

    decay = 0.5 ** (days / DECAY_HALF_LIFE_DAYS)
    decayed = dict(profile)
    for key in ("categories", "brands", "subcategories"):
        if key in decayed:
            decayed[key] = {k: v * decay for k, v in decayed[key].items()}

    _decay_cache = {"profile": profile, "result": decayed, "ts": now}
    return decayed


# ================================================================
# 🏆 UCB PRODUCT RANKING
# ================================================================

def rank_products_for_user(
    products: List[Dict],
    behavior_profile: Dict,
    search_context: Dict = None,
) -> List[Dict]:
    """Rank products using UCB exploration + user preference signals."""
    if not behavior_profile or behavior_profile.get("total_interactions", 0) < 2:
        return products

    profile     = _apply_time_decay(behavior_profile)
    categories  = profile.get("categories", {})
    brands      = profile.get("brands", {})
    impressions = profile.get("impressions", {})
    avg_price   = profile.get("avg_price", 0)
    total       = max(profile.get("total_interactions", 1), 1)

    max_cat   = max(categories.values(), default=1)
    max_brand = max(brands.values(), default=1)

    scored = []
    for p in products:
        score = 0.0

        # Category affinity
        cat = p.get("category", "")
        if cat and cat in categories:
            score += 3 * (categories[cat] / max_cat)

        # Brand affinity
        br = p.get("brand", "")
        if br and br in brands:
            score += 2 * (brands[br] / max_brand)

        # Price proximity
        price = p.get("price", 0)
        if avg_price > 0 and price > 0:
            if abs(price - avg_price) / avg_price <= 0.2:
                score += 1.0

        # UCB exploration bonus (avoids always showing same products)
        pid = p.get("product_id", "")
        n_i = impressions.get(pid, 0)
        score += UCB_EXPLORATION_C * math.sqrt(math.log(total + 1) / (n_i + 1))

        if score > 0:
            scored.append((p, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in scored]


# ================================================================
# 👗 FASHION ADVICE CONTEXT
# ================================================================

def build_fashion_advice_context(behavior_profile: Dict, user_message: str) -> str:
    """Build a short context string for the fashion advice LLM prompt."""
    if not behavior_profile:
        return ""
    profile    = _apply_time_decay(behavior_profile)
    categories = profile.get("categories", {})
    style      = profile.get("style_preference", "not set")
    avg_price  = profile.get("avg_price", 0)
    top_cats   = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:2]
    return (
        f"User style: {style}\n"
        f"Favourite categories: {', '.join(c[0] for c in top_cats) or 'unknown'}\n"
        f"Avg spend: PKR {avg_price:,.0f}\n"
        f"Question: {user_message}"
    )


# ================================================================
# 🌟 PERSONALISED INTRO (for rl_recommendations)
# ================================================================

def get_personalized_intro(behavior_profile: Dict) -> Optional[str]:
    """Return a personalised greeting line based on user history."""
    if not behavior_profile or behavior_profile.get("total_interactions", 0) < 3:
        return None
    profile = _apply_time_decay(behavior_profile)
    subcats = profile.get("subcategories", {})
    if subcats:
        top = max(subcats, key=subcats.get)
        return f"🔥 Based on your love for *{top}*, here are your top matches:"
    style = profile.get("style_preference", "")
    if style:
        return f"✨ Curated for your *{style}* style:"
    return None


# ================================================================
# 👔 OUTFIT SUGGESTIONS (LLM-powered)
# ================================================================

def generate_outfit_suggestions(product: Dict, user_profile: Dict) -> str:
    """
    Call the LLM to suggest 2 complementary items for a given product.
    Returns a short 2-3 line response.
    """
    from services.llm_router import call_llm
    prompt = (
        f"Product: {product.get('name')} "
        f"(Brand: {product.get('brand')}, Price: PKR {product.get('price')})\n"
        f"User style: {user_profile.get('style_preference', 'not specified')}\n"
        "Suggest 2 complementary items (e.g. shoes, bag, dupatta) that pair well "
        "with this product for a Pakistani fashion context. "
        "Keep it short — 2 to 3 lines only."
    )
    try:
        result = call_llm([{"role": "user", "content": prompt}], max_tokens=150)
        return result or "✨ Pair this with matching shoes and a simple clutch bag!"
    except Exception:
        return "✨ Pair this with matching shoes and a simple clutch bag!"


# ================================================================
# 📊 INTERACTION LOGGING (for RL personalisation)
# ================================================================

def log_interaction(behavior_profile: Dict, event_type: str, product: Dict) -> Dict:
    """
    Update behavior_profile weights based on an interaction event.
    event_type: "click" (weight 4), "add_to_cart" (weight 3), "view" (weight 1)
    Returns the updated profile dict (does NOT save to Firestore — caller's job).
    """
    profile = dict(behavior_profile) if behavior_profile else _empty_profile()

    # Ensure all required keys exist (handles partial profiles loaded from Firebase)
    for key in _empty_profile():
        profile.setdefault(key, _empty_profile()[key])

    weight = {"click": 4, "add_to_cart": 3, "view": 1}.get(event_type, 1)

    # Category weight
    cat = product.get("category", "")
    if cat:
        profile["categories"][cat] = profile["categories"].get(cat, 0) + weight

    # Brand weight
    brand = product.get("brand", "")
    if brand:
        profile["brands"][brand] = profile["brands"].get(brand, 0) + weight

    # Impression count (unique product views)
    pid = product.get("product_id", "")
    if pid:
        profile["impressions"][pid] = profile["impressions"].get(pid, 0) + 1

    # Rolling average price
    price = product.get("price", 0)
    if price and price > 0:
        cnt = profile.get("price_interactions", 0) + 1
        avg = profile.get("avg_price", 0)
        profile["avg_price"]          = ((avg * (cnt - 1)) + price) / cnt
        profile["price_interactions"] = cnt

    profile["total_interactions"] = profile.get("total_interactions", 0) + 1
    profile["last_active"]        = datetime.utcnow().strftime("%Y-%m-%d")

    return profile
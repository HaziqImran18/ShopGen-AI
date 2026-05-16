# ================================================================
# 📁 live_search.py
# 📝 Purpose: Live product search via SerpAPI Google Shopping
# ================================================================

import os
import hashlib
import re
from typing import List, Dict, Optional, Tuple
from serpapi import GoogleSearch


def debug_log(msg: str):
    print(f"[LIVE SEARCH] {msg}")


# ================================================================
# 💰 PRICE PARSER
# ================================================================

def extract_price_value(price_str: str) -> int:
    digits = re.sub(r"[^0-9]", "", str(price_str))
    return int(digits) if digits else 0


# ================================================================
# 🏷️ CATEGORY GUESSER
# ================================================================

def guess_category_from_query(query: str) -> str:
    q = query.lower()
    if any(w in q for w in ["shirt", "kurti", "kurta", "kameez", "dupatta",
                              "suit", "lawn", "shalwar", "trouser", "jeans"]):
        return "clothing"
    if any(w in q for w in ["shoe", "sneaker", "sandal", "khussa", "chappal",
                              "loafer", "heel"]):
        return "footwear"
    if any(w in q for w in ["perfume", "attar", "cologne", "fragrance"]):
        return "fragrance"
    if any(w in q for w in ["watch", "bracelet", "necklace", "earring", "ring"]):
        return "accessories"
    return "general"


# ================================================================
# 🎯 FILTER ENGINE (price, gender, brand only)
# ================================================================

def apply_filters(
    products: List[Dict],
    gender: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    brand: Optional[str] = None,
) -> Tuple[List[Dict], Dict]:
    """Apply price, gender, and brand filters. Returns (filtered, stats)."""

    filtered = []
    stats = {
        "total_initial": len(products),
        "final_count":   0,
        "mismatched_filters": [],
    }

    gender_keywords = []
    if gender == "men":
        gender_keywords = ["men", "male", "men's", "mens", "man", "gentleman", "gents"]
    elif gender == "women":
        gender_keywords = ["women", "female", "women's", "womens", "woman", "lady", "girl"]

    for p in products:
        price = p.get("price", 0)

        # Price filter
        if price_min and price > 0 and price < price_min:
            continue
        if price_max and price > 0 and price > price_max:
            continue

        # Gender filter
        if gender_keywords:
            name = p.get("name", "").lower()
            pgender = p.get("gender", "").lower()
            if not any(kw in name or kw in pgender for kw in gender_keywords):
                continue

        # Brand filter
        if brand and brand.lower() not in p.get("brand", "").lower():
            continue

        filtered.append(p)

    stats["final_count"] = len(filtered)

    # Track which filter caused failures
    prices = [p.get("price", 0) for p in products if p.get("price", 0) > 0]
    if (price_min or price_max) and not filtered:
        stats["mismatched_filters"].append("price")
        stats["price_min_avail"] = min(prices) if prices else None
        stats["price_max_avail"] = max(prices) if prices else None
    if gender and not filtered:
        stats["mismatched_filters"].append(f"gender_{gender}")
    if brand and not filtered:
        stats["mismatched_filters"].append(f"brand_{brand}")

    return filtered, stats


# ================================================================
# 💬 FALLBACK MESSAGES (WhatsApp-friendly, short)
# ================================================================

def _short_fallback(query: str, stats: Dict, total_found: int,
                    gender=None, price_min=None, price_max=None, brand=None) -> str:
    mismatches = stats.get("mismatched_filters", [])

    if total_found == 0:
        tips = []
        if gender:   tips.append(f"remove gender filter '{gender}'")
        if price_max: tips.append(f"increase budget (max PKR {price_max:,})")
        if brand:    tips.append(f"try without brand filter")
        hint = " • ".join(tips[:2]) if tips else "try different keywords"
        return (
            f"😔 *No results for \"{query}\"*\n\n"
            f"💡 Try: {hint}\n"
            f"Or ask me to search without filters."
        )

    # Products found but filters eliminated all
    if "price" in mismatches:
        lo = stats.get("price_min_avail")
        hi = stats.get("price_max_avail")
        price_hint = f"PKR {lo:,}–{hi:,}" if lo and hi else "different range"
        return (
            f"📋 *Price mismatch for \"{query}\"*\n\n"
            f"Found {total_found} products but none in your price range.\n"
            f"✅ Available: {price_hint}\n"
            f"💡 Try adjusting your budget."
        )

    for m in mismatches:
        if m.startswith("gender_"):
            g = m.replace("gender_", "")
            return (
                f"📋 *No {g}'s items for \"{query}\"*\n\n"
                f"💡 Try removing the gender filter or search without it."
            )
        if m.startswith("brand_"):
            b = m.replace("brand_", "")
            return (
                f"📋 *Brand '{b}' not in results for \"{query}\"*\n\n"
                f"💡 Try without brand filter or check spelling."
            )

    return f"😔 No products matched your filters for \"{query}\". Try broader search terms."


# ================================================================
# 🔍 MAIN SEARCH FUNCTION
# ================================================================

def live_search_products(
    query: str,
    brand: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    gender: Optional[str] = None,
    num_results: int = 10,
) -> Tuple[List[Dict], Optional[str]]:
    """
    Search Pakistani products via SerpAPI Google Shopping.
    Returns (products, fallback_message). fallback_message is None on success.
    """

    # ⚠️ API-KEY
    api_key = "5b4618237eb4d62d445276e1175925bec26ad794006bec8d248566e60e88ae96"

    if not api_key:
        return [], "⚠️ Search service unavailable. Please try again."

    # Build query string
    search_terms = [query]
    if brand:   search_terms.append(brand)
    if gender:  search_terms.append(gender)
    q = " ".join(search_terms)

    params = {
        "engine":  "google_shopping",
        "q":       q,
        "api_key": api_key,
        "tbm":     "shop",
        "gl":      "us",
        "hl":      "en",
        "num":     num_results * 2,
        "device":  "desktop",
    }
    if price_min: params["price_min"] = price_min
    if price_max: params["price_max"] = price_max

    try:
        results = GoogleSearch(params).get_dict()
        shopping_results = results.get("shopping_results", [])

        if not shopping_results:
            debug_log(f"No SerpAPI results for '{q}'")
            return [], _short_fallback(query, {"total_initial": 0, "final_count": 0,
                                               "mismatched_filters": []},
                                       0, gender=gender, price_min=price_min,
                                       price_max=price_max, brand=brand)

        # Parse products
        products = []
        for item in shopping_results:
            url = item.get("product_link") or item.get("link")
            if not url:
                continue

            product_id = item.get("product_id") or hashlib.md5(url.encode()).hexdigest()

            price = item.get("extracted_price", 0)
            if not price:
                price = extract_price_value(item.get("price", "0"))

            # Infer gender from title
            title_lower = item.get("title", "").lower()
            pgender = item.get("gender", "")
            if not pgender:
                if any(w in title_lower for w in ["men", "male", "man", "gent"]):
                    pgender = "men"
                elif any(w in title_lower for w in ["women", "female", "woman", "lady", "girl"]):
                    pgender = "women"

            products.append({
                "product_id": product_id,
                "name":       item.get("title", "Unknown")[:100],
                "price":      price,
                "url":        url,
                "brand":      item.get("source", brand or "Unknown"),
                "image":      item.get("thumbnail", ""),
                "currency":   "PKR",
                "source":     "serpapi",
                "position":   len(products) + 1,
                "gender":     pgender,
                "category":   guess_category_from_query(query),
            })

            if len(products) >= num_results * 2:
                break

        debug_log(f"Raw results: {len(products)} for '{q}'")

        filtered, stats = apply_filters(
            products,
            gender=gender,
            price_min=price_min,
            price_max=price_max,
            brand=brand,
        )

        if not filtered:
            fallback = _short_fallback(query, stats, len(products),
                                       gender=gender, price_min=price_min,
                                       price_max=price_max, brand=brand)
            return [], fallback

        debug_log(f"After filters: {len(filtered)} products")
        return filtered[:num_results], None

    except Exception as e:
        debug_log(f"SerpAPI error: {e}")
        return [], "⚠️ Search service temporarily unavailable. Please try again."

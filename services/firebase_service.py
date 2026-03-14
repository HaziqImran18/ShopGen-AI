"""
Firebase Service
────────────────
All Firestore read/write operations.
User isolation is enforced by using user_id as the document key.
No user can ever access another user's data.

Firestore structure:
  users/
    {user_id}/          ← WhatsApp number is the key
      cart: []
      order_history: []
      conversation_history: []
      pending_otp: str | null
      pending_order: dict | null
      last_seen: str

  products/
    {product_id}/
      name, brand, category, gender, price, url, image_url, scraped_at
"""

import os
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

# ─── Initialize Firebase ───────────────────────────────────────────────────────
# Set FIREBASE_CREDENTIALS_PATH in .env to the path of your serviceAccount.json

_db = None

def _get_db():
    global _db
    if _db is None:
        if not firebase_admin._apps:
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccount.json")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        _db = firestore.client()
    return _db


# ─── User Data ─────────────────────────────────────────────────────────────────

def get_user_data(user_id: str) -> Dict:
    """
    Fetch a user's full state from Firestore.
    Returns empty defaults if user doesn't exist yet (first message).
    """
    db = _get_db()
    doc = db.collection("users").document(user_id).get()

    if doc.exists:
        return doc.to_dict()

    # First-time user — return clean defaults
    return {
        "cart": [],
        "order_history": [],
        "conversation_history": [],
        "pending_otp": None,
        "pending_order": None,
    }


def save_user_data(user_id: str, data: Dict) -> None:
    """
    Save/update a user's state in Firestore.
    Uses merge=True so partial updates don't overwrite other fields.
    """
    db = _get_db()
    db.collection("users").document(user_id).set(data, merge=True)


# ─── Products ──────────────────────────────────────────────────────────────────

def get_products_collection(params: Dict) -> List[Dict]:
    """
    Query products from Firestore based on search parameters.
    Applies available filters then sorts by price.
    
    Note: Firestore requires composite indexes for multi-field queries.
    We filter in Python after a broad query to avoid index requirements during dev.
    """
    db = _get_db()
    query = db.collection("products")

    # Apply Firestore-level filters where possible
    if params.get("gender"):
        query = query.where("gender", "==", params["gender"])
    if params.get("brand"):
        query = query.where("brand", "==", params["brand"])

    # Fetch and apply remaining filters in Python
    docs = query.limit(100).stream()
    results = []

    for doc in docs:
        p = doc.to_dict()
        p["product_id"] = doc.id

        # Category filter (substring match)
        if params.get("category"):
            if params["category"].lower() not in p.get("category", "").lower():
                continue

        # Price filter
        if params.get("max_price") and p.get("price", 0) > params["max_price"]:
            continue
        if params.get("min_price") and p.get("price", 0) < params["min_price"]:
            continue

        # Color filter — soft match, adds score but doesn't exclude
        # Many products don't mention color in name, so we don't hard-filter
        color_match = False
        if params.get("color"):
            searchable = (p.get("name", "") + " " + p.get("description", "")).lower()
            color_match = params["color"].lower() in searchable
        p["_color_match"] = color_match

        # Occasion filter — soft match
        occasion_match = False
        if params.get("occasion"):
            searchable = (p.get("name", "") + " " + p.get("tags", "")).lower()
            occasion_match = params["occasion"].lower() in searchable
        p["_occasion_match"] = occasion_match

        results.append(p)

    # Sort: color/occasion matches first, then by price ascending
    results.sort(key=lambda x: (
        not x.get("_color_match", False),      # color matches come first
        not x.get("_occasion_match", False),   # then occasion matches
        x.get("price", 0)                      # then cheapest first
    ))

    # Clean up internal scoring fields before returning
    for p in results:
        p.pop("_color_match", None)
        p.pop("_occasion_match", None)

    return results


def get_product_by_id(product_id: str) -> Optional[Dict]:
    """Fetch a single product by its Firestore document ID."""
    db = _get_db()
    doc = db.collection("products").document(product_id).get()
    if doc.exists:
        p = doc.to_dict()
        p["product_id"] = doc.id
        return p
    return None


def save_products_batch(products: List[Dict]) -> int:
    """
    Bulk save scraped products to Firestore.
    Uses product_id as document key to avoid duplicates on re-scrape.
    Returns count of products saved.
    """
    db = _get_db()
    batch = db.batch()
    count = 0

    for product in products:
        product_id = product.get("product_id")
        if not product_id:
            continue
        ref = db.collection("products").document(product_id)
        batch.set(ref, product, merge=True)
        count += 1

        # Firestore batch limit is 500
        if count % 499 == 0:
            batch.commit()
            batch = db.batch()

    batch.commit()
    return count
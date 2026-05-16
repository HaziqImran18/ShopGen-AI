# ================================================================
# 📁 firebase_service.py
# 📝 Purpose: Firebase user profile CRUD only (NO product logic)
# ✅ Added: _get_db() helper for modules that write to Firestore directly.
# ================================================================

import firebase_admin
from firebase_admin import credentials, firestore
import os
import time
from dotenv import load_dotenv

load_dotenv()

db = None
_firebase_available = False


def debug_log(msg: str):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[FIREBASE {timestamp}] {msg}")


def _try_init_firebase():
    global db, _firebase_available
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    if not cred_path or not os.path.exists(cred_path):
        debug_log(f"Credentials not found at '{cred_path}'. User data will not persist.")
        return
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        _firebase_available = True
        debug_log("Firebase connected.")
    except Exception as e:
        debug_log(f"Firebase init failed: {e}. User data will not persist.")


_try_init_firebase()


def _get_db():
    """
    Return the Firestore client, or None if Firebase is not initialised.
    Callers should check for None and skip writes gracefully.
    """
    return db if _firebase_available else None


_USER_DEFAULT = {
    "conversation_history": [],
    "user_profile":         {},
    "behavior_profile":     {},
    "last_shown_products":  [],
    "selected_products":    [],  # ADD THIS LINE
    "onboarding_step":      None,
    "last_seen_date":       None,
    "last_intent":          None,
}

def get_user_data(user_id: str) -> dict:
    debug_log(f"get_user_data: {user_id}")
    start = time.time()
    if not _firebase_available:
        return dict(_USER_DEFAULT)
    try:
        doc = db.collection("users").document(user_id).get()
        result = doc.to_dict() if doc.exists else dict(_USER_DEFAULT)
        debug_log(f"get_user_data done in {(time.time()-start)*1000:.0f}ms")
        return result
    except Exception as e:
        debug_log(f"get_user_data failed: {e}")
        return dict(_USER_DEFAULT)


def save_user_data(user_id: str, data: dict):
    debug_log(f"save_user_data: {user_id}")
    start = time.time()
    if not _firebase_available:
        return
    try:
        db.collection("users").document(user_id).set(data, merge=True)
        debug_log(f"save_user_data done in {(time.time()-start)*1000:.0f}ms")
    except Exception as e:
        debug_log(f"save_user_data failed: {e}")


# 🚀 End of file
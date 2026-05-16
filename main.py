# ================================================================
# 📁 main.py
# 📝 Purpose: FastAPI server — WhatsApp webhook, tracking, TTS
# ================================================================

import os, time, asyncio, requests, hashlib
from collections import OrderedDict
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from agent.graph import agent_graph
from services.voice_service import transcribe_audio, text_to_speech
from services.tracking_service import decode_tracking_id, log_click_event

load_dotenv()

WHAPI_TOKEN = os.getenv("WHAPI_TOKEN")
WHAPI_URL   = os.getenv("WHAPI_URL", "https://gate.whapi.cloud")

USER_RATE: dict[str, float] = {}

# ─── Connection pooling ───────────────────────────────────────────────────────
_session = None

def get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        adapter = HTTPAdapter(
            max_retries=Retry(total=0),
            pool_connections=10,
            pool_maxsize=20,
        )
        _session.mount("https://", adapter)
        _session.mount("http://",  adapter)
        print("[SESSION] Connection pool created")
    return _session


# ─── Debug counters ───────────────────────────────────────────────────────────
_STATS = {"webhook_calls": 0, "duplicate_webhooks": 0,
          "send_calls": 0, "send_timeouts": 0, "total_send_ms": 0}

def debug_log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


# ─── TTL dedup set ────────────────────────────────────────────────────────────
class _TTLSet:
    def __init__(self, ttl: int = 30):
        self._store: OrderedDict = OrderedDict()
        self._ttl = ttl

    def __contains__(self, key: str) -> bool:
        self._evict(); return key in self._store

    def add(self, key: str):
        self._evict(); self._store[key] = time.monotonic()

    def _evict(self):
        cutoff = time.monotonic() - self._ttl
        while self._store:
            k, ts = next(iter(self._store.items()))
            if ts < cutoff: self._store.popitem(last=False)
            else: break


processed_messages = _TTLSet(ttl=30)

# ─── Duplicate response prevention ───────────────────────────────────────────
_response_cache: dict[str, tuple[str, float]] = {}

def _is_duplicate_response(user_id: str, text: str) -> bool:
    h   = hashlib.md5(text.encode()).hexdigest()
    now = time.time()
    if user_id in _response_cache:
        last_h, last_t = _response_cache[user_id]
        if last_h == h and (now - last_t) < 60:
            debug_log(f"🛑 DUPLICATE blocked for {user_id}")
            return True
    _response_cache[user_id] = (h, now)
    # Cleanup old entries
    for uid in list(_response_cache):
        if now - _response_cache[uid][1] > 300:
            del _response_cache[uid]
    return False


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("static/audio", exist_ok=True)
    print("✅ ShopGen V2 ready (live search mode)!")
    yield


app = FastAPI(title="ShopGen", version="4.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["POST", "GET"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")


# ─── Messaging helpers ────────────────────────────────────────────────────────
def send_text(to: str, body: str):
    _STATS["send_calls"] += 1
    start = time.time()
    to    = to.replace("whatsapp:", "").strip()
    debug_log(f"📤 send_text to={to} size={len(body)}")
    chunks  = [body[i:i+4000] for i in range(0, len(body), 4000)]
    session = get_session()
    for i, chunk in enumerate(chunks):
        try:
            resp = session.post(
                f"{WHAPI_URL}/messages/text",
                headers={"Authorization": f"Bearer {WHAPI_TOKEN}"},
                json={"to": to, "body": chunk},
                timeout=30,
            )
            debug_log(f"  chunk {i+1}/{len(chunks)} status={resp.status_code}")
        except requests.Timeout:
            _STATS["send_timeouts"] += 1
            debug_log(f"  ⏰ timeout chunk {i+1} — Whapi will retry")
        except Exception as e:
            debug_log(f"  ❌ {e}")
    _STATS["total_send_ms"] += (time.time() - start) * 1000


def send_audio(to: str, audio_url: str):
    to = to.replace("whatsapp:", "").strip()
    try:
        get_session().post(
            f"{WHAPI_URL}/messages/audio",
            headers={"Authorization": f"Bearer {WHAPI_TOKEN}"},
            json={"to": to, "media": audio_url},
            timeout=40,
        )
    except Exception as e:
        debug_log(f"🎵 audio error: {e}")


# ─── Background task ──────────────────────────────────────────────────────────
async def process_message(from_number: str, initial_state: dict, is_voice: bool):
    start = time.time()
    try:
        result       = await asyncio.to_thread(agent_graph.invoke, initial_state)
        response     = result.get("response_text") or "⚠️ Something went wrong. Please try again."
        debug_log(f"✅ graph done {(time.time()-start)*1000:.0f}ms response={len(response)}chars")

        if not _is_duplicate_response(from_number, response):
            send_text(from_number, response)

        if is_voice and len(response) < 400:
            audio_url = text_to_speech(response)
            if audio_url:
                send_audio(from_number, audio_url)
    except Exception as e:
        debug_log(f"❌ process_message error: {e}")
        send_text(from_number, "⚠️ Something went wrong. Please try again.")
    debug_log(f"🏁 total {(time.time()-start)*1000:.0f}ms")


# ─── Webhook ──────────────────────────────────────────────────────────────────
@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    _STATS["webhook_calls"] += 1
    debug_log(f"📞 WEBHOOK #{_STATS['webhook_calls']}")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"status": "invalid_json"}, status_code=400)

    messages = body.get("messages", [])
    if not messages:
        return JSONResponse({"status": "no_messages"})

    msg         = messages[0]
    msg_age     = time.time() - int(msg.get("timestamp", 0))
    if msg_age > 60:
        debug_log(f"⏰ too old ({msg_age:.0f}s)")
        return JSONResponse({"status": "old_ignored"})

    msg_id      = msg.get("id")
    from_number = msg.get("from", "")
    msg_type    = msg.get("type", "")

    if msg_id in processed_messages:
        _STATS["duplicate_webhooks"] += 1
        return JSONResponse({"status": "duplicate"})

    if msg.get("from_me"):
        return JSONResponse({"status": "outgoing"})

    now = time.time()
    if now - USER_RATE.get(from_number, 0) < 1:
        return JSONResponse({"status": "rate_limited"})
    USER_RATE[from_number] = now

    user_message = ""
    is_voice     = False

    if msg_type == "text":
        user_message = msg.get("text", {}).get("body", "").strip()

    elif msg_type in ("audio", "voice"):
        is_voice   = True
        voice_data = msg.get("voice") or msg.get("audio") or {}
        media_url  = (voice_data.get("link") or
                      f"{WHAPI_URL}/messages/media/{voice_data.get('id', '')}")
        user_message, _ = transcribe_audio(media_url, whapi_token=WHAPI_TOKEN)
        if not user_message:
            send_text(from_number, "Sorry, couldn't understand your voice. Please try again.")
            return JSONResponse({"status": "voice_failed"})

    elif msg_type == "image":
        send_text(from_number, "Image search not supported yet. Please type your request.")
        return JSONResponse({"status": "image_not_supported"})

    else:
        return JSONResponse({"status": "unsupported"})

    if not user_message:
        return JSONResponse({"status": "empty"})

    processed_messages.add(msg_id)

    # Immediate acknowledgment (WhatsApp 15s rule)
    try:
        get_session().post(
            f"{WHAPI_URL}/messages/text",
            headers={"Authorization": f"Bearer {WHAPI_TOKEN}"},
            json={"to": from_number,
                  "body": "⏳ Okay, processing your request..."},
            timeout=5,
        )
    except Exception as e:
        debug_log(f"⚠️ ACK failed: {e}")

    initial_state = {
        "user_id":              from_number,
        "user_message":         user_message,
        "conversation_history": [],
        "user_profile":         None,
        "onboarding_step":      None,
        "last_seen_date":       None,
        "last_shown_products":  [],
        "behavior_profile":     {},
        "intent":               None,
        "search_params":        None,
        "products":             None,
        "response_text":        None,
        "response_audio_url":   None,
    }

    asyncio.create_task(process_message(from_number, initial_state, is_voice))
    return JSONResponse({"status": "accepted"})


# ─── Tracking redirect ────────────────────────────────────────────────────────
@app.get("/track/{short_id}")
async def track_click(short_id: str):
    try:
        data = decode_tracking_id(short_id)
        log_click_event(data)
        return RedirectResponse(url=data["original_url"], status_code=302)
    except Exception:
        return RedirectResponse(url="https://google.com", status_code=302)


# ─── Demo order webhook ───────────────────────────────────────────────────────
@app.post("/webhook/order")
async def receive_demo_order(request: Request):
    try:
        order      = await request.json()
        user_phone = order.get("phone", "").replace("whatsapp:", "").strip()
        confirm    = (
            f"✅ *Demo Order Received*\n\n"
            f"Order ID: `{order['order_id']}`\n"
            f"Product: {order.get('product_name', 'N/A')}\n"
            f"Size: {order.get('size', 'N/A')}\n"
            f"Delivery: {order.get('address', 'N/A')}, {order.get('city', 'N/A')}\n\n"
            f"This is a *simulated order* for thesis demo.\n"
            f"No real payment or shipment. Thank you! 🎓"
        )
        if user_phone and len(user_phone) >= 10:
            send_text(user_phone, confirm)
        return JSONResponse({"status": "ok", "order_id": order["order_id"]})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ─── Health & debug ───────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "running", "version": "4.1.0", "mode": "live_search"}


@app.get("/health")
async def health():
    return {"status": "healthy", "mode": "live_search"}


@app.get("/debug/stats")
async def debug_stats():
    return {
        "webhook_calls":    _STATS["webhook_calls"],
        "duplicate_webhooks": _STATS["duplicate_webhooks"],
        "send_calls":       _STATS["send_calls"],
        "send_timeouts":    _STATS["send_timeouts"],
        "avg_send_ms":      _STATS["total_send_ms"] / max(_STATS["send_calls"], 1),
    }

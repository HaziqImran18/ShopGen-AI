"""
Main FastAPI Application — ShopGen WhatsApp Shopping Assistant
───────────────────────────────────────────────────────────────
Handles:
  - Text messages
  - Voice messages (OGG audio → Whisper transcription)
  - Image messages (→ vision search)
  - Always responds with BOTH text AND audio
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from twilio.rest import Client
from dotenv import load_dotenv

from agent.graph import agent_graph
from services.voice_service import transcribe_audio, text_to_speech

load_dotenv()

# ─── Twilio ────────────────────────────────────────────────────────────────────

twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
MAX_MSG_LEN = 1500


# ─── Startup ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("static/audio", exist_ok=True)
    print("✅ ShopGen started!")
    yield


app = FastAPI(
    title="ShopGen — AI Shopping Assistant",
    description="WhatsApp AI shopping assistant for Pakistani fashion brands",
    version="2.0.0",
    lifespan=lifespan,
)

os.makedirs("static/audio", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ─── Utilities ─────────────────────────────────────────────────────────────────

def split_message(text: str, chunk_size: int = MAX_MSG_LEN):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def send_text(to: str, body: str):
    """Send text message via Twilio."""
    for part in split_message(body):
        twilio_client.messages.create(from_=TWILIO_NUMBER, to=to, body=part)


def send_audio(to: str, audio_url: str):
    """Send audio message via Twilio."""
    try:
        twilio_client.messages.create(
            from_=TWILIO_NUMBER,
            to=to,
            media_url=[audio_url],
        )
    except Exception as e:
        print(f"[AUDIO SEND ERROR] {e}")


# ─── Main Webhook ──────────────────────────────────────────────────────────────

@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    """
    Handles all incoming WhatsApp messages:
    - Text  → straight to agent
    - Voice → transcribe first → agent
    - Image → agent with image_url → vision search
    Always responds with text + audio.
    """
    form = await request.form()

    from_number   = form.get("From", "")
    message_body  = form.get("Body", "").strip()
    num_media     = int(form.get("NumMedia", 0))
    media_url     = form.get("MediaUrl0", "")
    media_type    = form.get("MediaContentType0", "")

    print(f"\n{'='*40}")
    print(f"FROM: {from_number}")
    print(f"MESSAGE: {message_body}")
    print(f"MEDIA: {num_media} ({media_type})")

    user_message = message_body
    image_url    = None
    is_voice     = False

    # ── Voice message ─────────────────────────────────────────────────────────
    if num_media > 0 and "audio" in media_type:
        is_voice = True
        transcribed = transcribe_audio(media_url)
        if transcribed:
            user_message = transcribed
            print(f"TRANSCRIBED: {user_message}")
        else:
            send_text(from_number, "Sorry, I couldn't understand your voice message. Please try again or type your message.")
            return JSONResponse({"status": "transcription_failed"})

    # ── Image message ─────────────────────────────────────────────────────────
    elif num_media > 0 and "image" in media_type:
        image_url = media_url
        user_message = "image search"  # trigger phrase for intent
        print(f"IMAGE URL: {image_url}")

    if not user_message:
        return JSONResponse({"status": "no_message"})

    # ── Run LangGraph Agent ───────────────────────────────────────────────────
    try:
        initial_state = {
            "user_id":              from_number,
            "user_message":         user_message,
            "is_voice":             is_voice,
            "image_url":            image_url,
            "cart":                 [],
            "order_history":        [],
            "conversation_history": [],
            "pending_otp":          None,
            "pending_order":        None,
            "user_profile":         None,
            "onboarding_step":      None,
            "last_seen_date":       None,
            "intent":               None,
            "search_params":        None,
            "products":             None,
            "response_text":        None,
            "response_audio_url":   None,
        }

        result = agent_graph.invoke(initial_state)
        response_text = result.get("response_text") or "Sorry, something went wrong. Please try again."
        print(f"RESPONSE: {response_text[:120]}...")

        # ── Always send text ──────────────────────────────────────────────────
        send_text(from_number, response_text)

        # ── Always send audio too ─────────────────────────────────────────────
        audio_url = text_to_speech(response_text)
        if audio_url:
            send_audio(from_number, audio_url)

        return JSONResponse({"status": "ok"})

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        send_text(from_number, "Sorry, something went wrong. Please try again in a moment.")
        return JSONResponse({"status": "error", "detail": str(e)})


# ─── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "running", "service": "ShopGen", "version": "2.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
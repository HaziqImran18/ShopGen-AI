# ================================================================
# 📁 voice_service.py
# 📝 Purpose: Audio transcription (Whisper) and TTS (OpenAI/gTTS)
# ================================================================

import os
import re
import uuid
import tempfile
import requests
from gtts import gTTS
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
AUDIO_DIR = os.getenv("AUDIO_DIR", "static/audio")
BASE_URL  = os.getenv("BASE_URL", "http://localhost:8000")

# Whisper prompt tuned for Pakistani accent / Roman Urdu
_WHISPER_PROMPT = (
    "Pakistani user. Urdu, English, or mixed Hinglish. Common words: "
    "chahiye, milega, dikhao, karo, bhai, yaar, acha, theek, nahi, haan, "
    "price, order, delivery, shop, kahan, kya, available, stock."
)


# ================================================================
# 🔢 NUMBER-WORD NORMALISATION
# ================================================================

_NUM_MAP = [
    (r'ten thousand', '10000'), (r'nine thousand', '9000'),
    (r'eight thousand', '8000'), (r'seven thousand', '7000'),
    (r'six thousand', '6000'), (r'five thousand', '5000'),
    (r'four thousand', '4000'), (r'three thousand', '3000'),
    (r'two thousand', '2000'), (r'one thousand', '1000'),
    (r'five hundred', '500'), (r'four hundred', '400'),
    (r'three hundred', '300'), (r'two hundred', '200'),
    (r'one hundred', '100'), (r'ninety', '90'), (r'eighty', '80'),
    (r'seventy', '70'), (r'sixty', '60'), (r'fifty', '50'),
    (r'forty', '40'), (r'thirty', '30'),
]

def number_words_to_digits(text: str) -> str:
    for word, digit in _NUM_MAP:
        text = re.sub(r'\b' + word + r'\b', digit, text, flags=re.IGNORECASE)
    return text


# ================================================================
# 🎙️ TRANSCRIPTION
# ================================================================

def transcribe_audio(audio_url: str, whapi_token: str = None) -> tuple[str, str]:
    """
    Download audio from Whapi and transcribe via OpenAI Whisper.
    Returns (transcribed_text, intent_hint="unknown").
    intent_hint kept for API compatibility but smart_router handles intent.
    """
    tmp_path = None
    try:
        headers = {}
        if whapi_token and "whapi.cloud" in audio_url:
            headers["Authorization"] = f"Bearer {whapi_token}"

        resp = requests.get(audio_url, headers=headers, timeout=30)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "audio/ogg")
        ext = ".ogg"
        if "mpeg" in content_type or "mp3" in content_type:
            ext = ".mp3"
        elif "mp4" in content_type or "m4a" in content_type:
            ext = ".m4a"

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(resp.content)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                prompt=_WHISPER_PROMPT,
                response_format="text",
            )

        text = transcript.strip() if isinstance(transcript, str) else transcript.text.strip()
        text = number_words_to_digits(text)

        print(f"[VOICE] Transcribed: {text!r}")
        return text, "unknown"   # intent resolved by smart_router

    except Exception as e:
        print(f"[VOICE ERROR] {e}")
        return "", "unknown"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ================================================================
# 🔊 TEXT-TO-SPEECH
# ================================================================

_URL_RE   = re.compile(r"https?://\S+")
_EMOJI_RE = re.compile(
    r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
    r"\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
    r"\u2702-\u27B0\u24C2-\U0001F251]+",
    flags=re.UNICODE,
)


def strip_for_speech(text: str) -> str:
    text = _URL_RE.sub("link", text)
    text = _EMOJI_RE.sub("", text)
    text = (text.replace("*", "").replace("_", "").replace("`", "")
                .replace("#", "").replace("━", "").replace("•", "")
                .replace("|", "").replace("—", ",").replace("–", ","))
    return re.sub(r"\n{2,}", "\n", text).strip()


def _urdu_ratio(text: str) -> float:
    urdu = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    return urdu / max(len(text), 1)


def text_to_speech(text: str) -> str:
    """Convert response text to MP3. Returns public URL."""
    try:
        os.makedirs(AUDIO_DIR, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)
        clean = strip_for_speech(text)

        try:
            resp = openai_client.audio.speech.create(
                model="tts-1", voice="alloy", input=clean[:4096]
            )
            resp.stream_to_file(filepath)
        except Exception as e:
            print(f"[TTS] OpenAI TTS failed, falling back to gTTS: {e}")
            lang = "ur" if _urdu_ratio(clean) > 0.30 else "en"
            gTTS(text=clean, lang=lang, slow=False).save(filepath)

        return f"{BASE_URL}/static/audio/{filename}"
    except Exception as e:
        print(f"[TTS ERROR] {e}")
        return ""

"""
Voice Service
──────────────
Handles both directions of voice in your FYP:
  - Input:  Twilio sends OGG audio URL → we download it → Whisper transcribes to text
  - Output: Text response → gTTS converts to MP3 → we host it → send URL back via Twilio

This is a key differentiator for your FYP — multimodal (text + voice) support.
"""

import os
import uuid
import tempfile
import requests
from gtts import gTTS
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Directory to serve audio files from (configure in main.py with StaticFiles)
AUDIO_DIR = os.getenv("AUDIO_DIR", "static/audio")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")  # Your ngrok/Railway URL


def transcribe_audio(audio_url: str) -> str:
    """
    Downloads audio from Twilio's URL and transcribes it using Groq's Whisper.
    Twilio sends voice messages as OGG format. Whisper handles OGG natively.
    Returns transcribed text, or empty string on failure.
    """
    tmp_path = None
    try:
        # Download audio file from Twilio
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")

        response = requests.get(
            audio_url,
            auth=(twilio_sid, twilio_token),
            timeout=30
        )
        response.raise_for_status()

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        # Transcribe with Whisper via Groq
        # Must pass file as tuple (filename, fileobj, mimetype) for Groq to accept it
        with open(tmp_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=("audio.ogg", audio_file, "audio/ogg"),
                response_format="text",
                language="en",
            )

        # response_format="text" returns a plain string directly
        text = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
        print(f"[VOICE INPUT] Transcribed: {text}")
        return text

    except Exception as e:
        print(f"[VOICE ERROR] Transcription failed: {e}")
        return ""

    finally:
        # Always clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def text_to_speech(text: str) -> str:
    """
    Converts text response to audio using gTTS (Google Text-to-Speech).
    Saves MP3 to static directory and returns its public URL.
    Returns the public URL of the audio file, or empty string on failure.
    """
    try:
        os.makedirs(AUDIO_DIR, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        # Strip markdown formatting for cleaner speech
        clean_text = (
            text.replace("*", "")
                .replace("_", "")
                .replace("`", "")
                .replace("#", "")
                .replace("🛒", "cart")
                .replace("✅", "")
                .replace("❌", "")
                .replace("📦", "")
                .replace("💰", "")
                .replace("🔐", "")
        )

        tts = gTTS(text=clean_text, lang="en", slow=False)
        tts.save(filepath)

        audio_url = f"{BASE_URL}/static/audio/{filename}"
        print(f"[VOICE OUTPUT] Audio saved: {audio_url}")
        return audio_url

    except Exception as e:
        print(f"[TTS ERROR] {e}")
        return ""
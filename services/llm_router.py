import os
import time
import threading
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ─── Rate limiting (to avoid hitting OpenAI’s free tier limits) ───────────────
_last_call = 0.0
_MIN_GAP = 1.5  # seconds between calls (adjust as needed)

# Semaphore to limit concurrent calls (max 2 at a time)
_LLM_SEMAPHORE = threading.Semaphore(2)
HARD_TIMEOUT = 8  # seconds

def _format_messages(messages: list) -> str:
    """Convert messages list to a simple string prompt (for compatibility)"""
    return "\n".join(m["content"] for m in messages if m.get("content"))

def _run_with_timeout(fn, timeout: int = HARD_TIMEOUT):
    result = [None]
    exc = [None]

    def target():
        try:
            result[0] = fn()
        except Exception as e:
            exc[0] = e

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)

    if t.is_alive():
        return None, "hard timeout"

    if exc[0]:
        return None, str(exc[0])

    return result[0], None

def call_llm(messages: list, max_tokens: int = 200, preferred: str = "openai") -> str:
    """
    Call OpenAI’s gpt-4o-mini (fast, cheap, reliable).
    Returns a string. If it fails, returns a friendly error message.
    """
    if not openai_client:
        return "⚠️ OpenAI API key not configured. Please add OPENAI_API_KEY to your .env file."

    # Rate limiting: ensure we don't exceed free tier limits
    global _last_call
    now = time.time()
    if now - _last_call < _MIN_GAP:
        wait = _MIN_GAP - (now - _last_call)
        time.sleep(wait)
    _last_call = time.time()

    with _LLM_SEMAPHORE:
        def _call():
            try:
                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",  # cheapest and fast model
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                content = response.choices[0].message.content
                return content.strip() if content else ""
            except Exception as e:
                raise e

        result, error = _run_with_timeout(_call)

        if result:
            return result
        else:
            print(f"[OPENAI ERROR] {error}")
            return "🤖 Sorry, I'm having trouble processing your request right now. Please try again in a moment."

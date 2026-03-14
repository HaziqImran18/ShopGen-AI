"""
LangGraph Nodes — ShopGen Shopping Assistant

Full flow:
  load_user_state → check_onboarding → classify_intent → route → action → generate_response → save_user_state
"""

import json
import random
import string
import os
from datetime import datetime, timedelta
from typing import Dict

from groq import Groq
from twilio.rest import Client as TwilioClient
from dotenv import load_dotenv

from agent.state import AgentState
from services.firebase_service import (
    get_user_data,
    save_user_data,
    get_products_collection,
    get_product_by_id,
)
from services.user_service import (
    is_profile_complete,
    get_next_onboarding_step,
    get_onboarding_question,
    apply_onboarding_answer,
    format_profile_complete_message,
)
from services.cards_service import (
    get_daily_greeting,
    get_welcome_card,
    get_search_results_card,
    get_cart_card,
)

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = "llama3-70b-8192"
MAX_HISTORY = 10


# ── Utility ────────────────────────────────────────────────────────────────────

def _llm(system: str, user: str, json_mode: bool = False) -> str:
    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=0.3,
        max_tokens=512,
        **kwargs,
    )
    return response.choices[0].message.content.strip()


# ── NODE 1 — Load user state ───────────────────────────────────────────────────

def load_user_state(state: AgentState) -> AgentState:
    user_data = get_user_data(state["user_id"])
    state["cart"]                  = user_data.get("cart", [])
    state["order_history"]         = user_data.get("order_history", [])
    state["conversation_history"]  = user_data.get("conversation_history", [])[-MAX_HISTORY:]
    state["pending_otp"]           = user_data.get("pending_otp")
    state["pending_order"]         = user_data.get("pending_order")
    state["user_profile"]          = user_data.get("user_profile", {})
    state["onboarding_step"]       = user_data.get("onboarding_step")
    state["last_seen_date"]        = user_data.get("last_seen_date")
    state["intent"]                = None
    state["search_params"]         = None
    state["products"]              = None
    state["response_text"]         = None
    state["response_audio_url"]    = None
    state["image_url"]             = state.get("image_url")
    return state


# ── NODE 2 — Check onboarding ──────────────────────────────────────────────────

def check_onboarding(state: AgentState) -> AgentState:
    profile = state.get("user_profile") or {}

    if is_profile_complete(profile):
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if state.get("last_seen_date") != today:
            state["intent"] = "daily_greeting"
        return state

    current_step = state.get("onboarding_step") or get_next_onboarding_step(profile)

    if current_step and state["user_message"]:
        profile = apply_onboarding_answer(profile, current_step, state["user_message"])
        state["user_profile"] = profile
        next_step = get_next_onboarding_step(profile)

        if next_step is None:
            state["onboarding_step"] = None
            state["response_text"]   = format_profile_complete_message(profile)
            state["intent"]          = "onboarding_complete"
        else:
            state["onboarding_step"] = next_step
            state["response_text"]   = get_onboarding_question(next_step)
            state["intent"]          = "onboarding"
    else:
        first_step = get_next_onboarding_step(profile)
        state["onboarding_step"] = first_step
        state["response_text"]   = get_onboarding_question(first_step)
        state["intent"]          = "onboarding"

    return state


# ── NODE 3 — Classify intent ───────────────────────────────────────────────────

def classify_intent(state: AgentState) -> AgentState:
    if state.get("image_url"):
        state["intent"] = "vision_search"
        return state

    if state.get("intent"):
        return state

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in state["conversation_history"][-4:]
    )

    system = (
        "You are an intent classifier for a Pakistani fashion shopping WhatsApp assistant. "
        "Classify the user message into EXACTLY one of these intents:\n"
        "- search: find/browse products\n"
        "- add_to_cart: add item to cart\n"
        "- view_cart: see cart contents\n"
        "- clear_cart: empty the cart\n"
        "- place_order: checkout/confirm order\n"
        "- verify_otp: user is sending an OTP code (digits only or short numeric string)\n"
        "- order_status: check past orders\n"
        "- my_profile: view saved profile\n"
        "- menu: asking for help or options\n"
        "- general: anything else\n\n"
        "Return ONLY JSON: {\"intent\": \"<intent>\", \"confidence\": <0.0-1.0>}"
    )

    user = "Context:\n" + history_text + "\n\nMessage: \"" + state["user_message"] + "\""

    try:
        result = json.loads(_llm(system, user, json_mode=True))
        state["intent"] = result.get("intent", "general")
    except Exception:
        state["intent"] = "general"

    print(f"[INTENT] {state['intent']} for: {state['user_message']}")
    return state


# ── NODE 4a — Vision search ────────────────────────────────────────────────────

def vision_search(state: AgentState) -> AgentState:
    from services.vision_service import analyze_clothing_image, build_search_params_from_vision

    image_url = state.get("image_url")
    if not image_url:
        state["response_text"] = "I didn't receive an image. Please try sending the photo again."
        return state

    vision_result  = analyze_clothing_image(image_url)
    description    = vision_result.get("description", "clothing item")
    search_params  = build_search_params_from_vision(vision_result)
    state["search_params"] = search_params

    products = get_products_collection(search_params)
    state["products"] = products[:6]

    print(f"[VISION SEARCH] {len(state['products'])} products for: {description}")

    product_card = get_search_results_card(state["products"])
    state["response_text"] = "📸 I see: *" + description + "*\n\nSimilar items:\n\n" + product_card
    return state


# ── NODE 4b — Search products ──────────────────────────────────────────────────

def search_products(state: AgentState) -> AgentState:
    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in state["conversation_history"][-4:]
    )

    system = (
        "Extract product search parameters from a Pakistani fashion store query. "
        "Return JSON with these fields (null if not mentioned):\n"
        "{\n"
        "  \"category\": one of [\"shalwar kameez\",\"kurta\",\"lawn suit\",\"dress\",\"shirt\",\"trousers\",\"dupatta\",\"saree\",null],\n"
        "  \"gender\": one of [\"men\",\"women\",\"kids\",null],\n"
        "  \"max_price\": integer PKR or null,\n"
        "  \"min_price\": integer PKR or null,\n"
        "  \"color\": string or null,\n"
        "  \"brand\": one of [\"Khaadi\",\"Sapphire\",\"Alkaram\",null],\n"
        "  \"occasion\": one of [\"casual\",\"formal\",\"eid\",\"wedding\",\"office\",null]\n"
        "}"
    )

    user = "Context:\n" + history_text + "\n\nMessage: \"" + state["user_message"] + "\""

    try:
        params = json.loads(_llm(system, user, json_mode=True))
        state["search_params"] = params
    except Exception:
        state["search_params"] = {}

    print(f"[SEARCH PARAMS] {state['search_params']}")

    products = get_products_collection(state["search_params"])
    state["products"]       = products[:6]
    state["response_text"]  = get_search_results_card(state["products"])
    return state


# ── NODE 4c — Manage cart ──────────────────────────────────────────────────────

def manage_cart(state: AgentState) -> AgentState:
    intent = state["intent"]
    cart   = state["cart"]

    if intent == "view_cart":
        state["response_text"] = get_cart_card(cart)
        return state

    if intent == "clear_cart":
        state["cart"]          = []
        state["response_text"] = "Cart cleared! What are you looking for?"
        return state

    if intent == "add_to_cart":
        last_msg = next(
            (m["content"] for m in reversed(state["conversation_history"]) if m["role"] == "assistant"),
            ""
        )
        system = (
            "User wants to add a product to cart. Extract from the message:\n"
            "{\"item_number\": integer (if user said 'add 1' or 'add 2'), \"qty\": integer default 1}\n"
            "Return ONLY JSON."
        )
        user = "Products shown:\n" + last_msg + "\n\nUser says: \"" + state["user_message"] + "\""

        try:
            result      = json.loads(_llm(system, user, json_mode=True))
            item_number = result.get("item_number")
            qty         = result.get("qty", 1) or 1

            product_id = None
            if item_number:
                import re
                ids = re.findall(r'[A-Z]{2,5}-[A-F0-9]{8}', last_msg)
                if ids and item_number <= len(ids):
                    product_id = ids[item_number - 1]

            if product_id:
                product = get_product_by_id(product_id)
                if product:
                    existing = next((i for i in cart if i["product_id"] == product_id), None)
                    if existing:
                        existing["qty"] += qty
                    else:
                        cart.append({
                            "product_id": product_id,
                            "name":       product["name"],
                            "brand":      product["brand"],
                            "price":      product["price"],
                            "qty":        qty,
                        })
                    state["cart"]         = cart
                    state["response_text"] = (
                        "Added *" + product["name"] + "* to your cart!\n"
                        "PKR " + f"{product['price']:,}" + " x " + str(qty) + "\n\n"
                        "Type *view cart* or *place order* to checkout."
                    )
                else:
                    state["response_text"] = "Product not found. Try again with the correct number."
            else:
                state["response_text"] = "Please specify which item — e.g. *add 1* or *add 2*"
        except Exception as e:
            print(f"[CART ERROR] {e}")
            state["response_text"] = "Couldn't add the item. Try typing *add 1* or *add 2*."

    return state


# ── NODE 4d — Initiate order (send OTP separately) ────────────────────────────

def initiate_order(state: AgentState) -> AgentState:
    """
    OTP Flow:
      1. Show order summary + delivery address
      2. Generate OTP
      3. Send OTP as a SEPARATE Twilio message (like a real OTP SMS)
      4. Tell user to enter the code they just received
    """
    cart         = state["cart"]
    user_profile = state.get("user_profile") or {}

    if not cart:
        state["response_text"] = "Your cart is empty! Add some products first."
        return state

    otp   = "".join(random.choices(string.digits, k=6))
    total = sum(item["price"] * item["qty"] for item in cart)

    pending_order = {
        "items":      cart,
        "total":      total,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
    }

    state["pending_otp"]   = otp
    state["pending_order"] = pending_order

    # Build items summary
    items_lines = []
    for item in cart:
        items_lines.append(
            "  " + item["name"] + " x" + str(item["qty"]) +
            " — PKR " + f"{item['price'] * item['qty']:,}"
        )
    items_text = "\n".join(items_lines)

    # Message 1: Order summary (NO OTP here)
    state["response_text"] = (
        "📦 *Order Summary*\n"
        "━━━━━━━━━━━━━━━━━━━━\n" +
        items_text + "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💰 *Total: PKR " + f"{total:,}" + "*\n\n"
        "🚚 *Delivering to:*\n"
        "  👤 " + user_profile.get("name", "N/A") + "\n"
        "  📍 " + user_profile.get("address", "N/A") + "\n"
        "  🏙️ " + user_profile.get("city", "N/A") + "\n\n"
        "🔐 Sending your OTP now..."
    )

    # Message 2: OTP as a SEPARATE Twilio message
    try:
        twilio = TwilioClient(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )
        twilio.messages.create(
            from_=os.getenv("TWILIO_NUMBER"),
            to=state["user_id"],
            body=(
                "ShopGen OTP\n\n"
                "Your order confirmation code is:\n\n"
                "*" + otp + "*\n\n"
                "Valid for 5 minutes.\n"
                "Reply with this code to confirm your order."
            )
        )
        print(f"[OTP] Sent {otp} to {state['user_id']}")
    except Exception as e:
        print(f"[OTP SEND ERROR] {e}")
        # Fallback: put OTP in the response if Twilio fails
        state["response_text"] += "\n\n_Your OTP: *" + otp + "*_"

    return state


# ── NODE 4e — Verify OTP ───────────────────────────────────────────────────────

def verify_otp(state: AgentState) -> AgentState:
    user_code    = state["user_message"].strip()
    stored_otp   = state.get("pending_otp")
    pending_order = state.get("pending_order")
    user_profile  = state.get("user_profile") or {}

    if not stored_otp or not pending_order:
        state["response_text"] = (
            "No pending order found.\n"
            "Add items to cart and type *place order* to start."
        )
        return state

    expires_at = datetime.fromisoformat(pending_order["expires_at"])
    if datetime.utcnow() > expires_at:
        state["pending_otp"]   = None
        state["pending_order"] = None
        state["response_text"] = "OTP expired. Type *place order* to get a new one."
        return state

    if user_code == stored_otp:
        order_id = "ORD-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")

        order = {
            **pending_order,
            "order_id": order_id,
            "status":   "confirmed",
            "user_id":  state["user_id"],
            "delivery": {
                "name":    user_profile.get("name", "N/A"),
                "address": user_profile.get("address", "N/A"),
                "city":    user_profile.get("city", "N/A"),
            }
        }

        orders = state.get("order_history", [])
        orders.append(order)

        state["order_history"] = orders
        state["cart"]          = []
        state["pending_otp"]   = None
        state["pending_order"] = None

        items_lines = []
        for i in pending_order.get("items", []):
            items_lines.append(
                "  " + i["name"] + " x" + str(i["qty"]) +
                " — PKR " + f"{i['price'] * i['qty']:,}"
            )
        items_text = "\n".join(items_lines)

        state["response_text"] = (
            "Order Confirmed!\n\n"
            "Order ID: *" + order_id + "*\n\n"
            "Items:\n" + items_text + "\n\n"
            "Total: PKR " + f"{pending_order.get('total', 0):,}" + "\n\n"
            "Delivering to:\n"
            "  " + user_profile.get("name", "N/A") + "\n"
            "  " + user_profile.get("address", "N/A") + ", " + user_profile.get("city", "N/A") + "\n\n"
            "Expected delivery: 3-5 business days.\n"
            "Thank you for shopping with ShopGen!"
        )
    else:
        state["response_text"] = (
            "Incorrect OTP. Please check and try again.\n"
            "Type *place order* to resend a new OTP."
        )

    return state


# ── NODE 5 — Generate response ─────────────────────────────────────────────────

def generate_response(state: AgentState) -> AgentState:
    if state.get("response_text"):
        return state

    intent = state["intent"]

    if intent == "daily_greeting":
        name = (state.get("user_profile") or {}).get("name", "there")
        state["response_text"] = get_daily_greeting(name)
        return state

    if intent == "menu":
        state["response_text"] = get_welcome_card()
        return state

    if intent == "my_profile":
        profile = state.get("user_profile") or {}
        state["response_text"] = (
            "Your Profile:\n\n"
            "  Name: " + profile.get("name", "N/A") + "\n"
            "  City: " + profile.get("city", "N/A") + "\n"
            "  Address: " + profile.get("address", "N/A")
        )
        return state

    if intent == "order_status":
        orders = state.get("order_history", [])
        if not orders:
            state["response_text"] = "No orders yet. Browse products and place your first order!"
        else:
            last = orders[-1]
            items_lines = []
            for i in last.get("items", []):
                items_lines.append("  " + i["name"] + " x" + str(i["qty"]))
            state["response_text"] = (
                "Latest Order:\n\n"
                "Order ID: " + last.get("order_id", "N/A") + "\n"
                "Status: " + last.get("status", "N/A").upper() + "\n"
                "Total: PKR " + f"{last.get('total', 0):,}" + "\n\n"
                "Items:\n" + "\n".join(items_lines) + "\n"
                "Placed: " + last.get("created_at", "")[:10]
            )
        return state

    # General chat
    history_msgs = [
        {"role": m["role"], "content": m["content"]}
        for m in state["conversation_history"][-6:]
    ]
    history_msgs.append({"role": "user", "content": state["user_message"]})

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are ShopGen, a friendly WhatsApp shopping assistant for Pakistani fashion brands "
                    "(Khaadi, Sapphire, Alkaram). Keep replies short, max 5 lines, no markdown tables."
                ),
            },
            *history_msgs,
        ],
        temperature=0.7,
        max_tokens=300,
    )
    state["response_text"] = response.choices[0].message.content.strip()
    return state


# ── NODE 6 — Save user state ───────────────────────────────────────────────────

def save_user_state(state: AgentState) -> AgentState:
    history = state.get("conversation_history", [])
    history.append({"role": "user",      "content": state["user_message"]})
    if state.get("response_text"):
        history.append({"role": "assistant", "content": state["response_text"]})
    history = history[-MAX_HISTORY:]

    save_user_data(state["user_id"], {
        "cart":                 state.get("cart", []),
        "order_history":        state.get("order_history", []),
        "conversation_history": history,
        "pending_otp":          state.get("pending_otp"),
        "pending_order":        state.get("pending_order"),
        "user_profile":         state.get("user_profile", {}),
        "onboarding_step":      state.get("onboarding_step"),
        "last_seen_date":       datetime.utcnow().strftime("%Y-%m-%d"),
    })
    return state
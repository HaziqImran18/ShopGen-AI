# ================================================================
# 📁 nodes.py
# 📝 Purpose: All LangGraph node functions for ShopGen V2
# ================================================================

import os, time, json, re
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlencode
from services.llm_router import call_llm
from services.tracking_service import generate_tracking_link
from services.live_search import live_search_products
from services.intent_parser import parse_intent
from services.firebase_service import get_user_data, save_user_data
from services.rl_service import (
    rank_products_for_user,
    build_fashion_advice_context,
    get_personalized_intro,
    init_profile_from_onboarding,
    generate_outfit_suggestions,
)
from agent.state import AgentState
from dotenv import load_dotenv

load_dotenv()

MAX_HISTORY = 10


def debug_log(msg: str):
    print(f"[NODE {time.strftime('%H:%M:%S')}] {msg}")


# ================================================================
# 🧭 ONBOARDING CONFIG
# ================================================================

ONBOARDING_STEPS = ["name", "city", "style"]
ONBOARDING_QUESTIONS = {
    "name":  "👋 Welcome to *ShopGen* — your AI fashion discovery assistant!\n\nWhat's your name?",
    "city":  "Great! 🏙️ Which city are you in?\n_(e.g. Lahore, Karachi, Islamabad)_",
    "style": "Last one! 👗 What's your fashion style?\n\n1. Casual\n2. Ethnic\n3. Formal\n4. Streetwear",
}
STYLE_MAP = {"1": "casual", "2": "ethnic", "3": "formal", "4": "streetwear"}


def _is_profile_complete(profile: Dict) -> bool:
    return all(profile.get(f) for f in ONBOARDING_STEPS)


def _next_onboarding_step(profile: Dict):
    for step in ONBOARDING_STEPS:
        if not profile.get(step):
            return step
    return None


def _profile_complete_message(profile: Dict) -> str:
    return (
        "✅ *Profile saved!*\n\n"
        f"  👤 Name:  {profile.get('name',  '')}\n"
        f"  🏙️ City:  {profile.get('city',  '')}\n"
        f"  👗 Style: {profile.get('style', '').capitalize()}\n\n"
        "You're all set! What can I help you with?\n"
        "• Search — _'women kurtis under 3000'_\n"
        "• Voice search — send a voice note\n"
        "• Fashion advice — _'what to wear for Eid?'_\n"
        "• Recommendations — _'suggest something'_"
    )


# ================================================================
# 🎨 FORMATTERS
# ================================================================

def _generate_demo_order_link(product: dict, user_id: str, user_profile: dict) -> str:
    import random
    streets = ["Main Boulevard", "Johar Town", "DHA Phase 5", "Gulberg III", "F-10 Markaz"]
    cities  = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Multan"]
    params  = {
        "product_id":   product.get("product_id", ""),
        "product_name": product.get("name", ""),
        "brand":        product.get("brand", ""),
        "price":        str(product.get("price", 0)),
        "name":         user_profile.get("name", "Demo User"),
        "phone":        user_id.replace("whatsapp:", ""),
        "city":         user_profile.get("city", random.choice(cities)),
        "address":      f"{random.choice(streets)}, {random.choice(cities)}",
        "size":         random.choice(["S", "M", "L", "XL"]),
    }
    return f"https://haziqimran18.github.io/shopgen-store/auto_order.html?{urlencode(params)}"


def _format_products(products: list, state: dict,
                     intro: str = None, search_context: dict = None) -> str:
    if not products:
        return "😔 No products found."

    lines    = [(intro or "🛍️ Here are your matches:") + "\n"]
    user_id  = state["user_id"]
    profile  = state.get("user_profile", {})

    for i, p in enumerate(products[:4]):
        if not p.get("product_id") or not p.get("url"):
            continue
        per_product_ctx = {
            **(search_context or {}),
            "category": p.get("category", ""),
            "brand":    p.get("brand", ""),
            "price":    p.get("price", 0),
        }
        real_url  = generate_tracking_link(user_id, p["product_id"], i + 1,
                                           p["url"], per_product_ctx)
        order_url = _generate_demo_order_link(p, user_id, profile)
        name      = p.get("name", "Unknown")
        if len(name) > 45:
            name = name[:42] + "..."
        lines.append(
            f"{i+1}. *{name}*\n"
            f"   {p.get('brand', 'N/A')} | USD {p.get('price', 0):,}\n"
            f"   🔗 [View Product]({real_url})\n"
            f"   🤖 [Auto Order]({order_url})\n"
        )

    return "\n".join(lines)


def _daily_greeting(name: str) -> str:
    h = datetime.now().hour
    g, e = (("Good morning", "🌅") if h < 12 else
            ("Good afternoon", "☀️") if h < 17 else
            ("Good evening", "🌙"))
    return (
        f"{e} *{g}, {name}!*\n\n"
        "Welcome back to ShopGen.\n"
        "What can I help you with today?\n"
        "• Search products\n• Fashion advice\n• _'menu'_ for all options"
    )


def _menu_card() -> str:
    return (
        "🛍️ *ShopGen — AI Fashion Discovery*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔍 *Search* — 'women lawn suits under 5000'\n"
        "🎤 *Voice* — send a voice note\n"
        "👗 *Fashion advice* — 'what to wear for Eid?'\n"
        "⭐ *Recommendations* — 'recommend me something'\n"
        "👤 *Profile* — 'my profile'\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Brands: *Khaadi • Sapphire • Alkaram • Bonanza • Ndure*"
    )


# ================================================================
# 🧠 SMART ROUTER (classify_intent)
# ================================================================

def resolve_follow_up(user_msg: str, last_products: list) -> Optional[int]:
    if not last_products:
        return None
    patterns = [
        r'(?:second|product|number|item|#|pehla|doosra|teesra)\s*(\d+)',
        r'(\d+)(?:st|nd|rd|th)?\s*(?:wala|product|item|number)',
        r'(\d+)\s*(?:k|ke|ki)',
    ]
    for pat in patterns:
        m = re.search(pat, user_msg.lower())
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(last_products):
                return idx
    return None


def smart_router(state: AgentState) -> AgentState:
    """LLM-based router: decides action (search/recommend/fashion_advice/answer/clarify)."""
    debug_log("🧠 smart_router START")
    start = time.time()

    user_msg      = state["user_message"]
    history       = state.get("conversation_history", [])[-4:]
    last_products = state.get("last_shown_products", [])
    selected      = state.get("selected_products", [])
    style         = state.get("user_profile", {}).get("style", "unknown")

    # Fast path: simple greetings
    user_lower = user_msg.lower().strip()
    if user_lower in ["hello", "hi", "hey", "salam", "assalam", "aoa"]:
        state["router_decision"] = {"action": "answer", "search_query": None,
                                     "price_min": None, "price_max": None, "gender": None}
        debug_log("🧠 greeting → answer")
        return state

    # Build context for LLM
    history_str = "\n".join(f"{m['role']}: {m['content'][:100]}" for m in history)
    products_str = ("\n".join(f"{i+1}. {p.get('name','')} - USD {p.get('price',0):,}"
                              for i, p in enumerate(last_products[:5])) if last_products else "None")
    selected_str = "\n".join(f"- {p.get('name')}" for p in selected) if selected else "None"

    prompt = f"""You are ShopGen's intent classifier. Analyse the user's message and choose ONE action:

- "search" – user wants to find specific products (e.g., "show men shoes", "trouser dikhao")
- "recommend" – user wants personalised suggestions (e.g., "kuch suggest karo")
- "fashion_advice" – user asks for styling tips, what to wear with something, or outfit ideas
- "answer" – general chat, greetings, help, menu, profile, or anything not covered above
- "clarify" – ONLY if the message is extremely vague and no context exists

Return STRICT JSON:
{{"action": "...", "search_query": "...", "price_min": null, "price_max": null, "gender": null, "use_selected_products": false}}

Examples:
- "hello" → {{"action": "answer", ...}}
- "second wala overcoat k sath koi shoes suggest kro" → {{"action": "fashion_advice", "use_selected_products": true}}
- "show me pants" → {{"action": "search", "search_query": "pants"}}
- "what should I wear for Eid" → {{"action": "fashion_advice"}}

Selected products (user has already picked these):
{selected_str}

Last shown products:
{products_str}

Conversation history (last 4 turns):
{history_str}

User style: {style}
Current message: {user_msg}

IMPORTANT:
- If the user asks for styling advice or product suggestions (e.g., "suggest shoes", "in k sath kya pehnu") and there are selected products, set action="fashion_advice" and use_selected_products=true.
- Do NOT use "clarify" unless message is completely gibberish.
"""
    try:
        response = call_llm([{"role": "user", "content": prompt}], max_tokens=120)
        response = re.sub(r'```json\s*|\s*```', '', response).strip()
        decision = json.loads(response)
        decision.setdefault("search_query", user_msg if decision.get("action") == "search" else None)
        decision.setdefault("price_min", None)
        decision.setdefault("price_max", None)
        decision.setdefault("gender", None)
        decision.setdefault("use_selected_products", False)
        # Force search if "dikhao" present
        if "dikhao" in user_msg.lower() and decision.get("action") != "search":
            decision["action"] = "search"
            decision["search_query"] = decision.get("search_query") or user_msg
        state["router_decision"] = decision
        debug_log(f"🧠 LLM decision: {decision}")
    except Exception as e:
        debug_log(f"❌ LLM failed: {e} → default answer")
        state["router_decision"] = {"action": "answer", "search_query": None,
                                    "price_min": None, "price_max": None, "gender": None,
                                    "use_selected_products": False}
    debug_log(f"🧠 smart_router END {(time.time()-start)*1000:.0f}ms")
    return state


def classify_intent(state: AgentState) -> AgentState:
    """Alias — calls smart_router."""
    return smart_router(state)


def detect_selections(user_msg: str, last_products: list) -> list:
    """
    Use LLM to extract which product numbers the user wants to "select"
    (e.g., "second wala", "third wali", "yeh le rha hoon").
    Returns list of 0‑based indices.
    """
    if not last_products:
        return []
    product_list = "\n".join(f"{i+1}. {p.get('name', '')[:60]}" for i, p in enumerate(last_products))
    prompt = f"""User message: "{user_msg}"
Last shown products:
{product_list}
Which product numbers does the user want to SELECT or TAKE? Examples: "second wala" → [2], "yeh aur yeh le rha hoon" → [1,3]. Return ONLY JSON list of integers, e.g., [2] or []. No extra text."""
    try:
        from services.llm_router import call_llm
        resp = call_llm([{"role": "user", "content": prompt}], max_tokens=50)
        import re, json
        resp = re.sub(r'```json\s*|\s*```', '', resp).strip()
        indices = json.loads(resp)
        # convert to 0‑based and validate
        return [i-1 for i in indices if isinstance(i, int) and 1 <= i <= len(last_products)]
    except:
        return []


# ================================================================
# 📂 NODE 1: Load user state
# ================================================================

def load_user_state(state: AgentState) -> AgentState:
    debug_log(f"📂 load_user_state: {state['user_id']}")
    start = time.time()
    data = get_user_data(state["user_id"])
    state.update({
        "last_intent":          data.get("last_intent"),
        "conversation_history": data.get("conversation_history", [])[-MAX_HISTORY:],
        "user_profile":         data.get("user_profile", {}),
        "onboarding_step":      data.get("onboarding_step"),
        "last_seen_date":       data.get("last_seen_date"),
        "last_shown_products":  data.get("last_shown_products", []),
        "selected_products":    data.get("selected_products", []),  # ADD THIS LINE
        "behavior_profile":     data.get("behavior_profile", {}),
        "intent":               None,
        "search_params":        None,
        "products":             None,
        "response_text":        None,
        "response_audio_url":   None,
        "router_decision":      None,
    })
    debug_log(f"📂 done {(time.time()-start)*1000:.0f}ms")
    return state


# ================================================================
# 🔍 NODE 2: Onboarding check
# ================================================================

def check_onboarding(state: AgentState) -> AgentState:
    debug_log(f"🔍 check_onboarding: {state['user_id']}")
    start   = time.time()
    intent  = state.get("intent")
    msg     = state.get("user_message", "").lower().strip()
    profile = state.get("user_profile") or {}

    # ── BLOCK ALL ACTIONS IF PROFILE IS INCOMPLETE ────────────────────────────
    if not _is_profile_complete(profile):
        debug_log("🔍 Profile incomplete - forcing onboarding")
        
        # Determine next step
        current = state.get("onboarding_step")
        if not current:
            first = _next_onboarding_step(profile)
            state.update({
                "onboarding_step": first,
                "response_text":   "👋 Welcome to ShopGen!\n\n" + ONBOARDING_QUESTIONS[first],
                "intent":          "onboarding",
            })
            return state
        
        # Process onboarding step
        answer = state["user_message"].strip()
        
        if current == "name":
            if len(answer) < 2 or answer.lower() in ["hi", "hello", "hey", "salam", "aoa"]:
                state["response_text"] = "Please enter a valid name 😊"
                state["intent"] = "onboarding"
                return state
            profile[current] = answer
            
        elif current == "city":
            profile[current] = answer
            
        elif current == "style":
            mapped = STYLE_MAP.get(answer, answer.lower())
            if mapped not in ["casual", "ethnic", "formal", "streetwear"]:
                state["response_text"] = "Please reply 1, 2, 3, or 4 to choose your style."
                state["intent"] = "onboarding"
                return state
            profile[current] = mapped
            state["behavior_profile"] = init_profile_from_onboarding(mapped)
        
        state["user_profile"] = profile
        next_step = _next_onboarding_step(profile)
        
        if next_step is None:
            state.update({
                "onboarding_step": None,
                "response_text":   _profile_complete_message(profile),
                "intent":          "onboarding_complete"
            })
        else:
            state.update({
                "onboarding_step": next_step,
                "response_text":   ONBOARDING_QUESTIONS[next_step],
                "intent":          "onboarding"
            })
        
        debug_log(f"🔍 onboarding step done {(time.time()-start)*1000:.0f}ms")
        return state

    # ── Profile is complete - proceed normally ─────────────────────────────────
    today = datetime.utcnow().strftime("%Y-%m-%d")
    _SAFE = {"search", "fashion_advice", "recommend", "menu", "my_profile", "answer"}
    if state.get("last_seen_date") != today and intent not in _SAFE:
        state["intent"] = "daily_greeting"
    
    debug_log(f"🔍 complete {(time.time()-start)*1000:.0f}ms")
    return state


# ================================================================
# 📢 NO-RESULTS FALLBACK MESSAGES
# ================================================================

def generate_no_results_message(query: str, gender=None,
                                 price_min=None, price_max=None,
                                 category=None) -> str:
    tips = []
    if gender:             tips.append(f"remove gender filter ('{gender}')")
    if price_min or price_max:
        tips.append(f"adjust price range (USD {price_min or 0}–{price_max or '∞'})")
    if category:           tips.append("try different keywords")
    hint = " • ".join(tips[:2]) if tips else "try broader keywords"
    return (
        f"😔 *No results for \"{query}\"*\n\n"
        f"💡 Try: {hint}\n"
        f"Or ask me to search without filters."
    )


def generate_gender_mismatch_message(target_gender: str, query: str) -> str:
    return (
        f"😔 *No {target_gender}'s items for \"{query}\"*\n\n"
        f"💡 Try: remove gender filter or search without it."
    )


def generate_price_mismatch_message(price_min, price_max,
                                     available_min, available_max, query: str) -> str:
    rng = f"USD {price_min:,}–{price_max:,}" if price_min and price_max else \
          f"under USD {price_max:,}" if price_max else f"above USD {price_min:,}"
    avail = (f"USD {available_min:,}–{available_max:,}"
             if available_min and available_max else "see all")
    return (
        f"📋 *Price issue for \"{query}\"*\n\n"
        f"❌ Searched: {rng}\n"
        f"✅ Available: {avail}\n"
        f"💡 Adjust your budget or remove price filter."
    )


# ================================================================
# 🔎 NODE 4a: Search products
# ================================================================

def search_products(state: AgentState) -> AgentState:
    debug_log("🔎 search_products START")
    start = time.time()

    decision = state.get("router_decision", {})
    user_msg  = state["user_message"]

    # Get query and basic params from router or intent parser
    if decision.get("action") == "search" and decision.get("search_query"):
        intent = parse_intent(user_msg)
        query  = decision["search_query"]
        # Router overrides take priority
        price_min = decision.get("price_min") if decision.get("price_min") is not None \
                    else intent.get("price_min")
        price_max = decision.get("price_max") if decision.get("price_max") is not None \
                    else intent.get("price_max")
        gender    = decision.get("gender") or intent.get("gender")
        brand     = intent.get("brand")
    else:
        intent    = parse_intent(user_msg)
        query     = intent.get("query") or user_msg
        price_min = intent.get("price_min")
        price_max = intent.get("price_max")
        gender    = intent.get("gender")
        brand     = intent.get("brand")

    state["search_params"] = intent
    debug_log(f"query={query!r} price={price_min}-{price_max} gender={gender} brand={brand}")

    # Detect category from query (used for category filter only, NOT passed to live_search)
    query_lower = query.lower()
    explicit_category = None
    if any(w in query_lower for w in ["shoe", "sneaker", "sandal", "khussa",
                                       "chappal", "loafer", "heel"]):
        explicit_category = "footwear"
    elif any(w in query_lower for w in ["perfume", "attar", "cologne", "fragrance"]):
        explicit_category = "fragrance"

    # ── Live search (handles price + gender filtering internally) ─────────────
    products, fallback_msg = live_search_products(
        query=query, brand=brand,
        price_min=price_min, price_max=price_max,
        gender=gender, num_results=15,
    )

    if not products:
        state["response_text"]    = fallback_msg or generate_no_results_message(
            query, gender, price_min, price_max, explicit_category)
        state["products"]         = []
        state["last_shown_products"] = []
        return state

    # ── Category filter (not in live_search, only for footwear/fragrance) ────
    if explicit_category and explicit_category != "clothing":
        filtered = [p for p in products if p.get("category") == explicit_category]
        if not filtered:
            state["response_text"] = (
                f"📋 *No {explicit_category} items for \"{query}\"*\n\n"
                f"💡 Try different keywords or remove category filter."
            )
            state["products"]         = []
            state["last_shown_products"] = []
            return state
        products = filtered

    # ── RL ranking (if user has interaction history) ──────────────────────────
    behavior = state.get("behavior_profile", {})
    if behavior and behavior.get("total_interactions", 0) > 2:
        try:
            products = rank_products_for_user(products, behavior, search_context=intent)
        except Exception as e:
            debug_log(f"⚠️ RL ranking failed: {e}")

    final     = products[:6]
    state["products"]            = final
    state["last_shown_products"] = final
    state["response_text"]       = _format_products(
        final, state, f"🛍️ *Found {len(final)} products for you:*\n\n", intent
    )

    debug_log(f"🔎 done {(time.time()-start)*1000:.0f}ms ({len(final)} products)")
    return state


# ================================================================
# 👗 NODE 4b: Fashion advice
# ================================================================
def fashion_advice(state: AgentState) -> AgentState:
    debug_log("👗 fashion_advice START")
    start = time.time()
    decision = state.get("router_decision", {})
    selected = state.get("selected_products", [])
    behavior = state.get("behavior_profile") or {}

    if decision.get("use_selected_products") and selected:
        # Build context with all selected products
        items_desc = "\n".join(f"- {p.get('name')} (Brand: {p.get('brand')}, Price: USD {p.get('price')})" for p in selected)
        context = f"User has selected these items:\n{items_desc}\n\nUser question: {state['user_message']}"
    else:
        context = build_fashion_advice_context(behavior, state["user_message"])

    system = (
        "You are ShopGen, a friendly WhatsApp fashion advisor. "
        "Reply in Roman Urdu/English mix. Max 6-7 lines. "
        "Give practical advice for Pakistani clothes & occasions (Eid, weddings, office, casual). "
        "If the user has selected specific items, give advice tailored to those items. "
        "End with a tip or question.\n\n"
        f"Context:\n{context}"
    )
    try:
        response = call_llm(
            [{"role": "system", "content": system},
             {"role": "user",   "content": state["user_message"]}],
            max_tokens=250, preferred="openai",
        )
        state["response_text"] = response or "Aap apni pasand share karein, main madad karunga! 👗"
    except Exception as e:
        debug_log(f"❌ Fashion advice error: {e}")
        state["response_text"] = "Kya aap outfit ke baare mein bata sakte hain? Main help karunga. 👗"
    debug_log(f"👗 done {(time.time()-start)*1000:.0f}ms")
    return state

# ================================================================
# ⭐ NODE 4c: RL recommendations
# ================================================================

def rl_recommendations(state: AgentState) -> AgentState:
    debug_log("⭐ rl_recommendations START")
    start    = time.time()
    behavior = state.get("behavior_profile") or {}
    decision = state.get("router_decision", {})

    follow_up_idx = decision.get("follow_up_product_index")
    query, brand  = "", ""

    if follow_up_idx is not None:
        last = state.get("last_shown_products", [])
        if 0 <= follow_up_idx < len(last):
            ref   = last[follow_up_idx]
            query = ref.get("category", "")
            brand = ref.get("brand", "")

    if not query:
        cats    = behavior.get("categories", {})
        top_cat = max(cats, key=cats.get) if cats else None
        style   = behavior.get("style_preference", "")
        query   = top_cat or style or "fashion"

    price_max = int(behavior.get("avg_price", 0) * 1.3) if behavior.get("avg_price") else None

    products, _ = live_search_products(
        query=query, brand=brand or None,
        price_max=price_max, num_results=8,
    )

    if not products:
        state["response_text"] = "😔 No recommendations yet. Search for a few products first!"
        return state

    products    = rank_products_for_user(products, behavior)
    final       = products[:6]
    state["products"]            = final
    state["last_shown_products"] = final

    if follow_up_idx is not None:
        intro = f"✨ *More like this* — based on product #{follow_up_idx+1}:"
    elif query != "fashion":
        intro = f"⭐ *Recommended for you* — based on your interest in *{query}*:"
    else:
        intro = "⭐ *Recommended for you:*"

    state["response_text"] = _format_products(final, state, intro)
    debug_log(f"⭐ done {(time.time()-start)*1000:.0f}ms")
    return state


# ================================================================
# ❓ NODE 4d: Clarification handler
# ================================================================

def handle_clarification(state: AgentState) -> AgentState:
    debug_log("❓ handle_clarification START")
    user_msg = state["user_message"].lower()

    last_response = ""
    for m in reversed(state.get("conversation_history", [])):
        if m.get("role") == "assistant":
            last_response = m.get("content", "")
            break

    show_phrases = ["dikhao", "show me", "dikha skte", "kya tum mujhe dikha",
                    "dikha do", "show karo"]
    if any(p in user_msg for p in show_phrases) and last_response:
        suggestions = re.findall(r'\d+\.\s*\*?([^*\n]+?)\*?(?:\n|$)', last_response)
        if suggestions:
            if len(suggestions) == 1:
                state["router_decision"] = {
                    "action":       "search",
                    "search_query": suggestions[0].strip(),
                    "price_min":    None,
                    "price_max":    None,
                    "gender":       None,
                }
                state["intent"]        = "search"
                state["response_text"] = None   # triggers search
                debug_log(f"❓ → search for: {suggestions[0].strip()}")
                return state
            else:
                options = ", ".join(suggestions[:3])
                state["response_text"] = (
                    f"In my last message I mentioned: {options}\n"
                    f"Which one should I search for?"
                )
                return state

    state["response_text"] = (
        "Could you be more specific? "
        "_(e.g. 'shoes under 5000', 'formal shirt for Eid')_"
    )
    return state


# ================================================================
# 💬 NODE 5: Generate response
# ================================================================
def generate_response(state: AgentState) -> AgentState:
    debug_log(f"💬 generate_response intent={state.get('intent')}")
    start = time.time()

    if state.get("response_text"):
        debug_log(f"💬 already set, skipping {(time.time()-start)*1000:.0f}ms")
        return state

    decision       = state.get("router_decision", {})
    action         = decision.get("action", "answer")
    follow_up_idx  = decision.get("follow_up_product_index")
    last_products  = state.get("last_shown_products", [])

    # ── 1. Handle selections (user picking products) ──────────────────────────
    if last_products:
        selected_indices = detect_selections(state["user_message"], last_products)
        if selected_indices:
            # get current selected list
            current_selected = list(state.get("selected_products", []))
            # add newly selected products (avoid duplicates by product_id)
            existing_ids = {p.get("product_id") for p in current_selected}
            for idx in selected_indices:
                if 0 <= idx < len(last_products):
                    prod = last_products[idx]
                    if prod.get("product_id") not in existing_ids:
                        current_selected.append(prod)
                        existing_ids.add(prod.get("product_id"))
            state["selected_products"] = current_selected
            # Confirm selection to user
            names = [last_products[i].get("name", f"product {i+1}")[:40] for i in selected_indices]
            state["response_text"] = f"✅ Added: {', '.join(names)}. Now you have {len(current_selected)} item(s) selected. Want fashion advice or more items?"
            return state

    # ── 2. Daily greeting ────────────────────────────────────────────────────
    intent = state.get("intent")
    if intent == "daily_greeting":
        name = state.get("user_profile", {}).get("name", "")
        state["response_text"] = _daily_greeting(name)
        return state

    # ── 3. Menu / Profile ────────────────────────────────────────────────────
    user_lower = state["user_message"].lower()
    if user_lower in ["menu", "menue", "help", "madad", "options"]:
        state["response_text"] = _menu_card()
        return state
    if "my profile" in user_lower or "mera profile" in user_lower:
        profile = state.get("user_profile", {})
        state["response_text"] = (
            f"👤 *Your Profile*\n\n"
            f"Name:  {profile.get('name', 'N/A')}\n"
            f"City:  {profile.get('city', 'N/A')}\n"
            f"Style: {profile.get('style', 'N/A').capitalize()}"
        )
        return state

    # ── 4. Follow‑up on a specific product (legacy) ─────────────────────────
    if follow_up_idx is not None and 0 <= follow_up_idx < len(last_products):
        product = last_products[follow_up_idx]
        if any(w in user_lower for w in ["outfit", "sath", "pair", "match", "wear with"]):
            user_profile = state.get("user_profile", {})
            behavior     = state.get("behavior_profile", {})
            combined_profile = {**user_profile, **behavior}
            suggestion = generate_outfit_suggestions(product, combined_profile)
            state["response_text"] = f"👗 *Outfit ideas for {product.get('name', 'this product')}:*\n\n" + suggestion
        elif any(w in user_lower for w in ["price", "kitna", "qeemat"]):
            state["response_text"] = f"💰 *{product['name']}* — USD {product.get('price', 0):,}\nWant to see similar items?"
        else:
            state["response_text"] = f"You asked about *{product['name']}*.\nWant: price info, similar products, or outfit ideas?"
        return state

    # ── 5. General LLM answer (with selected products context) ───────────────
    history = state.get("conversation_history", [])[-6:]
    products_ctx = ""
    if last_products:
        products_ctx = "Recently shown:\n" + "\n".join(
            f"{i+1}. {p['name']} — USD {p['price']}" for i, p in enumerate(last_products[:3])
        )
    selected_ctx = ""
    selected = state.get("selected_products", [])
    if selected:
        selected_ctx = "Your selected items:\n" + "\n".join(
            f"- {p.get('name')} ({p.get('brand')})" for p in selected
        )
    system = (
        "You are ShopGen, a WhatsApp shopping assistant. "
        "Reply in Roman Urdu/English. Max 6-7 lines. "
        "Do NOT search for products (another module handles that). "
        "Answer general questions, give fashion tips, clarify doubts.\n\n"
        + products_ctx + "\n" + selected_ctx
    )
    messages = [{"role": "system", "content": system}]
    for m in history:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": state["user_message"]})

    response = call_llm(messages, max_tokens=200, preferred="openai")
    state["response_text"] = (response or
        "Main yahan hoon aapki madad ke liye! Kuch dhundhna hai? 🛍️")

    debug_log(f"💬 done {(time.time()-start)*1000:.0f}ms")
    return state

# ================================================================
# 💾 NODE 6: Save user state
# ================================================================

def save_user_state(state: AgentState) -> AgentState:
    debug_log(f"💾 save_user_state: {state['user_id']}")
    start   = time.time()
    history = list(state.get("conversation_history", []))
    history.append({"role": "user",      "content": state["user_message"]})
    if state.get("response_text"):
        history.append({"role": "assistant", "content": state["response_text"]})

    # Add selected_products to the saved data (around line 485)
    save_user_data(state["user_id"], {
        "conversation_history": history[-MAX_HISTORY:],
        "user_profile":         state.get("user_profile", {}),
        "onboarding_step":      state.get("onboarding_step"),
        "last_seen_date":       datetime.utcnow().strftime("%Y-%m-%d"),
        "last_shown_products":  state.get("last_shown_products", []),
        "selected_products":    state.get("selected_products", []),  # ADD THIS LINE
        "behavior_profile":     state.get("behavior_profile", {}),
        "last_intent":          state.get("last_intent"),
    })
    debug_log(f"💾 done {(time.time()-start)*1000:.0f}ms")
    return state
"""
Cards Service
──────────────
Sends WhatsApp interactive messages (buttons/menus) via Twilio.

Two types of cards:
1. Welcome card  — sent on first message of the day with quick action buttons
2. Menu card     — sent when user types "menu" or "help"

Twilio WhatsApp supports interactive messages via Content Templates.
For sandbox, we use text-based menu cards with numbered options
since template approval isn't needed.
"""

from datetime import datetime
from typing import Optional


def get_daily_greeting(user_name: str) -> str:
    """
    Returns a personalized daily greeting card based on time of day.
    Sent once per day on the user's first message.
    """
    hour = datetime.now().hour

    if hour < 12:
        greeting = "Good morning"
        emoji = "🌅"
    elif hour < 17:
        greeting = "Good afternoon"
        emoji = "☀️"
    else:
        greeting = "Good evening"
        emoji = "🌙"

    return (
        f"{emoji} *{greeting}, {user_name}!*\n\n"
        f"Welcome back to ShopGen. Here's what's available today:\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔍 *1. Search Products*\n"
        f"   Type what you're looking for\n"
        f"   _e.g. 'women kurtis under 3000'_\n\n"
        f"📸 *2. Image Search*\n"
        f"   Send a photo to find similar items\n\n"
        f"🛒 *3. View My Cart*\n"
        f"   Type: _view cart_\n\n"
        f"📦 *4. My Orders*\n"
        f"   Type: _order status_\n\n"
        f"👤 *5. My Profile*\n"
        f"   Type: _my profile_\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"What can I help you with today?"
    )


def get_welcome_card() -> str:
    """
    Sent to brand new users after completing onboarding.
    Also sent when user types 'menu' or 'help'.
    """
    return (
        f"🛍️ *ShopGen — AI Shopping Assistant*\n"
        f"Pakistan's top fashion brands, on WhatsApp.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*How to shop:*\n\n"
        f"🔍 *Search by text*\n"
        f"   _'Show me women lawn suits under 5000'_\n"
        f"   _'Men shalwar kameez for Eid'_\n\n"
        f"📸 *Search by image*\n"
        f"   Send any clothing photo\n"
        f"   We'll find similar items\n\n"
        f"🎤 *Search by voice*\n"
        f"   Send a voice note\n"
        f"   We'll understand and search\n\n"
        f"🛒 *Cart & Ordering*\n"
        f"   _'add 1'_ → add to cart\n"
        f"   _'view cart'_ → see your items\n"
        f"   _'place order'_ → checkout with OTP\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Brands: *Khaadi • Sapphire • Alkaram*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"What are you looking for today? 👇"
    )


def get_search_results_card(products: list) -> str:
    """
    Formats product search results as a clean card.
    """
    if not products:
        return (
            "😔 *No products found*\n\n"
            "Try:\n"
            "• Different keywords\n"
            "• Remove price filter\n"
            "• Send a product photo instead\n\n"
            "_Example: 'women kurtis' or 'men shalwar kameez'_"
        )

    lines = ["🛍️ *Here are your matches:*\n"]
    valid = 0
    for p in products:
        price = p.get("price", 0)
        if price < 200:
            continue
        valid += 1
        lines.append(
            f"*{valid}.* {p['name']}\n"
            f"   🏷️ {p['brand']} | PKR {price:,}\n"
            f"   🔗 {p.get('url', 'N/A')}\n"
        )
        if valid >= 6:
            break

    if valid == 0:
        return get_search_results_card([])

    lines.append("─────────────────")
    lines.append("Reply *add 1*, *add 2* etc. to add to cart\nOr *view cart* to checkout")
    return "\n".join(lines)


def get_cart_card(cart: list) -> str:
    """Formats cart as a clean card."""
    if not cart:
        return (
            "🛒 *Your cart is empty*\n\n"
            "Search for products to get started!\n"
            "_Try: 'show me women kurtis under 3000'_"
        )

    total = sum(item["price"] * item["qty"] for item in cart)
    lines = ["🛒 *Your Cart:*\n"]
    for item in cart:
        lines.append(
            f"• {item['name']}\n"
            f"  {item['brand']} | {item['qty']}x PKR {item['price']:,}"
        )
    lines.append(f"\n━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"💰 *Total: PKR {total:,}*")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"\nType *place order* to checkout")
    lines.append(f"Type *clear cart* to start over")
    return "\n".join(lines)


def get_order_confirmation_card(order: dict, user_profile: dict) -> str:
    """Formats order summary before OTP is sent."""
    items_text = "\n".join(
        f"  • {item['name']} x{item['qty']} — PKR {item['price'] * item['qty']:,}"
        for item in order.get("items", [])
    )
    return (
        f"📦 *Order Summary*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{items_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *Total: PKR {order.get('total', 0):,}*\n\n"
        f"🚚 *Delivering to:*\n"
        f"  👤 {user_profile.get('name', 'N/A')}\n"
        f"  📍 {user_profile.get('address', 'N/A')}\n"
        f"  🏙️ {user_profile.get('city', 'N/A')}\n\n"
        f"🔐 *Your OTP: {order.get('otp', '------')}*\n\n"
        f"Reply with this code to confirm your order.\n"
        f"_Expires in 5 minutes_"
    )
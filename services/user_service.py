"""
User Profile Service
─────────────────────
Handles the onboarding flow that collects user info on first interaction.
Info is stored in Firebase and used for order delivery details.

Flow:
  First message → "Welcome! What's your name?"
  User replies  → Save name → "What's your delivery city?"
  User replies  → Save city → "Full delivery address?"
  User replies  → Save address → "Profile complete! Here's your menu."
"""

from typing import Optional, Dict


ONBOARDING_STEPS = ["name", "city", "address"]

ONBOARDING_QUESTIONS = {
    "name":    "👋 Welcome to ShopGen! I'm your AI shopping assistant for top Pakistani fashion brands.\n\nFirst, what's your name?",
    "city":    "Great! Which city are you in? (e.g. Lahore, Karachi, Islamabad)",
    "address": "Perfect! What's your full delivery address? (Street, Area)",
}

ONBOARDING_COMPLETE = """✅ *Profile saved!* Here's what I have:
{summary}

You're all set! Here's what I can do:
• 🔍 *Search products* — "show me women kurtis under 3000"
• 📸 *Image search* — send a clothing photo
• 🛒 *View cart* — "view cart"
• 📦 *Place order* — "place order"
• 📋 *Order status* — "order status"

What are you looking for today?"""


def is_profile_complete(user_profile: Optional[Dict]) -> bool:
    """Check if user has completed onboarding."""
    if not user_profile:
        return False
    return all(user_profile.get(field) for field in ONBOARDING_STEPS)


def get_next_onboarding_step(user_profile: Optional[Dict]) -> Optional[str]:
    """Returns the next field to collect, or None if complete."""
    if not user_profile:
        return "name"
    for step in ONBOARDING_STEPS:
        if not user_profile.get(step):
            return step
    return None


def get_onboarding_question(step: str) -> str:
    """Returns the question to ask for a given onboarding step."""
    return ONBOARDING_QUESTIONS.get(step, "Tell me a bit about yourself.")


def apply_onboarding_answer(user_profile: Dict, step: str, answer: str) -> Dict:
    """
    Saves the user's answer for the current onboarding step.
    Returns updated profile.
    """
    profile = dict(user_profile) if user_profile else {}
    profile[step] = answer.strip()
    return profile


def format_profile_complete_message(user_profile: Dict) -> str:
    """Returns the completion message with user's info summary."""
    summary = (
        f"  👤 Name: {user_profile.get('name', 'N/A')}\n"
        f"  🏙️ City: {user_profile.get('city', 'N/A')}\n"
        f"  📍 Address: {user_profile.get('address', 'N/A')}"
    )
    return ONBOARDING_COMPLETE.format(summary=summary)


def format_order_with_profile(order: Dict, user_profile: Dict) -> str:
    """
    Formats a confirmed order with delivery details.
    Used in OTP confirmation message.
    """
    items_text = "\n".join(
        f"  • {item['name']} x{item['qty']} — PKR {item['price'] * item['qty']:,}"
        for item in order.get("items", [])
    )
    return (
        f"✅ *Order Confirmed!*\n\n"
        f"📦 *Order ID:* {order.get('order_id', 'N/A')}\n\n"
        f"🛍️ *Items:*\n{items_text}\n\n"
        f"💰 *Total: PKR {order.get('total', 0):,}*\n\n"
        f"🚚 *Delivery Details:*\n"
        f"  👤 {user_profile.get('name', 'N/A')}\n"
        f"  📍 {user_profile.get('address', 'N/A')}, {user_profile.get('city', 'N/A')}\n\n"
        f"Your order will arrive in 3-5 business days. Thank you for shopping! 🎉"
    )
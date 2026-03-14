from typing import TypedDict, List, Optional, Dict, Any


class AgentState(TypedDict):
    """
    Central state passed between all LangGraph nodes.
    Every user gets their own isolated instance of this state,
    loaded from and saved to Firebase per user_id.
    """
    # User identification
    user_id: str                          # WhatsApp number e.g. "whatsapp:+923001234567"

    # Current message
    user_message: str                     # Raw incoming message text
    is_voice: bool                        # Was this a voice message?
    image_url: Optional[str]             # URL of image if user sent a photo

    # Intent classification result
    intent: Optional[str]                 # "search" | "add_to_cart" | "view_cart" |
                                          # "place_order" | "verify_otp" | "order_status" |
                                          # "onboarding" | "vision_search" | "general"

    # Extracted search parameters (filled by extract_params node)
    search_params: Optional[Dict[str, Any]]

    # Products found in this turn
    products: Optional[List[Dict]]

    # User profile (name, address, phone for order delivery)
    user_profile: Optional[Dict[str, str]]   # {"name": "...", "phone": "...", "address": "...", "city": "..."}
    onboarding_step: Optional[str]           # which field we are currently collecting

    # Persistent user data (loaded from Firebase at start of each turn)
    cart: List[Dict]
    order_history: List[Dict]
    conversation_history: List[Dict]

    # OTP flow
    pending_otp: Optional[str]
    pending_order: Optional[Dict]

    # Final response
    response_text: Optional[str]
    response_audio_url: Optional[str]
    last_seen_date: Optional[str]        # Track daily greeting
# ================================================================
# 📁 state.py
# ================================================================

from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime


class AgentState(TypedDict, total=False):
    """Shared state passed between all graph nodes."""

    # ── Required ─────────────────────────────────────────────────
    user_id:      str
    user_message: str

    # ── User data (loaded from Firebase) ─────────────────────────
    conversation_history: List[Dict[str, str]]
    user_profile:         Dict[str, Any]
    behavior_profile:     Dict[str, Any]
    last_shown_products:  List[Dict[str, Any]]
    onboarding_step:      Optional[str]
    last_seen_date:       Optional[str]
    last_intent:          Optional[str]

    # ── Routing & search ─────────────────────────────────────────
    intent:          Optional[str]
    router_decision: Optional[Dict[str, Any]]   # action, search_query, price_*, gender, use_selected_products
    search_params:   Optional[Dict[str, Any]]

    # ── Selected products (user's chosen items) ──────────────────
    selected_products: Optional[List[Dict[str, Any]]]   # products user explicitly selected

    # ── Products & response ──────────────────────────────────────
    products:           Optional[List[Dict[str, Any]]]
    response_text:      Optional[str]
    response_audio_url: Optional[str]

    # ── Misc ─────────────────────────────────────────────────────
    last_updated: Optional[str]


def create_initial_state(user_id: str, user_message: str) -> AgentState:
    """Create a fresh AgentState with safe defaults."""
    return {
        "user_id":              user_id,
        "user_message":         user_message,
        "conversation_history": [],
        "user_profile":         {},
        "behavior_profile":     {},
        "last_shown_products":  [],
        "onboarding_step":      None,
        "last_seen_date":       None,
        "last_intent":          None,
        "intent":               None,
        "router_decision":      None,
        "search_params":        None,
        "selected_products":    None,          # new
        "products":             None,
        "response_text":        None,
        "response_audio_url":   None,
        "last_updated":         datetime.utcnow().isoformat(),
    }
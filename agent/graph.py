"""
LangGraph Agent Graph — ShopGen

Full flow:
  load_user_state → check_onboarding → classify_intent → route → action → generate_response → save_user_state

                         ┌─────────────────┐
                         │ load_user_state │
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │check_onboarding │ ← collects name/city/address
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │classify_intent  │ ← LLM classifies intent
                         └────────┬────────┘
                                  │
               ┌──────────────────▼──────────────────────┐
               │             route_intent                 │
               └──┬──────┬──────┬──────┬──────┬──────────┘
                  │      │      │      │      │
            vision  search  cart  order  otp  generate_response
                  │      │      │      │      │
                  └──────┴──────┴──────┴──────┘
                                  │
                         ┌────────▼──────────┐
                         │ generate_response │
                         └────────┬──────────┘
                                  │
                         ┌────────▼──────────┐
                         │  save_user_state  │
                         └───────────────────┘
"""

from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes import (
    load_user_state,
    check_onboarding,
    classify_intent,
    vision_search,
    search_products,
    manage_cart,
    initiate_order,
    verify_otp,
    generate_response,
    save_user_state,
)


def route_intent(state: AgentState) -> str:
    """Routes to the correct node based on classified intent."""
    intent = state.get("intent", "general")

    routing = {
        "vision_search":     "vision_search",
        "search":            "search_products",
        "add_to_cart":       "manage_cart",
        "view_cart":         "manage_cart",
        "clear_cart":        "manage_cart",
        "place_order":       "initiate_order",
        "verify_otp":        "verify_otp",
        # these go directly to generate_response
        "order_status":      "generate_response",
        "menu":              "generate_response",
        "my_profile":        "generate_response",
        "daily_greeting":    "generate_response",
        "onboarding":        "generate_response",
        "onboarding_complete": "generate_response",
        "general":           "generate_response",
    }
    return routing.get(intent, "generate_response")


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("load_user_state",   load_user_state)
    graph.add_node("check_onboarding",  check_onboarding)
    graph.add_node("classify_intent",   classify_intent)
    graph.add_node("vision_search",     vision_search)
    graph.add_node("search_products",   search_products)
    graph.add_node("manage_cart",       manage_cart)
    graph.add_node("initiate_order",    initiate_order)
    graph.add_node("verify_otp",        verify_otp)
    graph.add_node("generate_response", generate_response)
    graph.add_node("save_user_state",   save_user_state)

    # Flow
    graph.set_entry_point("load_user_state")
    graph.add_edge("load_user_state",  "check_onboarding")
    graph.add_edge("check_onboarding", "classify_intent")

    # Conditional routing
    graph.add_conditional_edges(
        "classify_intent",
        route_intent,
        {
            "vision_search":     "vision_search",
            "search_products":   "search_products",
            "manage_cart":       "manage_cart",
            "initiate_order":    "initiate_order",
            "verify_otp":        "verify_otp",
            "generate_response": "generate_response",
        },
    )

    # All action nodes → generate_response
    graph.add_edge("vision_search",   "generate_response")
    graph.add_edge("search_products", "generate_response")
    graph.add_edge("manage_cart",     "generate_response")
    graph.add_edge("initiate_order",  "generate_response")
    graph.add_edge("verify_otp",      "generate_response")

    # generate_response → save → END
    graph.add_edge("generate_response", "save_user_state")
    graph.add_edge("save_user_state",   END)

    return graph.compile()


# Compile once at startup
agent_graph = build_graph()
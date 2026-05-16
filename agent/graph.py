# ================================================================
# 📁 graph.py
# 📝 Purpose: LangGraph workflow definition for ShopGen V2
# ================================================================

from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes import (
    load_user_state,
    check_onboarding,
    classify_intent,
    handle_clarification,
    search_products,
    fashion_advice,
    rl_recommendations,
    generate_response,
    save_user_state,
)


# ================================================================
# 🧭 ROUTING FUNCTIONS
# ================================================================

def route_after_onboarding(state: AgentState) -> str:
    """
    Conditional edge after check_onboarding.
    Routes based on router_decision.action set by smart_router.
    """
    decision = state.get("router_decision", {})
    action   = decision.get("action", "answer")

    mapping = {
        "search":         "search_products",
        "fashion_advice": "fashion_advice",
        "recommend":      "rl_recommendations",
        "clarify":        "handle_clarification",
        "answer":         "generate_response",
    }

    dest = mapping.get(action, "generate_response")
    print(f"[ROUTE] action={action} → {dest}")
    return dest


def route_after_clarification(state: AgentState) -> str:
    """
    Conditional edge after handle_clarification.

    KEY FIX: Resolves the "kya tum mujhe dikha skte ho" loop.
    When clarification detects the user wants to see a suggested
    item, it sets router_decision.action = "search" and clears
    response_text → this edge sends them to search_products.
    """
    decision      = state.get("router_decision", {})
    response_text = state.get("response_text")

    if decision.get("action") == "search" and response_text is None:
        print(f"[ROUTE] clarification → search: '{decision.get('search_query')}'")
        return "search_products"

    print("[ROUTE] clarification → save_user_state")
    return "save_user_state"


# ================================================================
# 🏗️ GRAPH CONSTRUCTION
# ================================================================

def build_graph() -> StateGraph:

    print("[GRAPH] Building ShopGen V2 graph...")
    graph = StateGraph(AgentState)

    # ── Nodes ────────────────────────────────────────────────────────────────
    graph.add_node("load_user_state",      load_user_state)
    graph.add_node("classify_intent",      classify_intent)
    graph.add_node("check_onboarding",     check_onboarding)
    graph.add_node("search_products",      search_products)
    graph.add_node("fashion_advice",       fashion_advice)
    graph.add_node("rl_recommendations",   rl_recommendations)
    graph.add_node("generate_response",    generate_response)
    graph.add_node("save_user_state",      save_user_state)
    graph.add_node("handle_clarification", handle_clarification)

    # ── Linear entry ─────────────────────────────────────────────────────────
    graph.set_entry_point("load_user_state")
    graph.add_edge("load_user_state", "classify_intent")
    graph.add_edge("classify_intent", "check_onboarding")

    # ── Branch after onboarding ───────────────────────────────────────────────
    graph.add_conditional_edges(
        "check_onboarding",
        route_after_onboarding,
        {
            "search_products":    "search_products",
            "fashion_advice":     "fashion_advice",
            "rl_recommendations": "rl_recommendations",
            "handle_clarification": "handle_clarification",
            "generate_response":  "generate_response",
        },
    )

    # ── Clarification can re-route to search (loop fix) ───────────────────────
    graph.add_conditional_edges(
        "handle_clarification",
        route_after_clarification,
        {
            "search_products": "search_products",
            "save_user_state": "save_user_state",
        },
    )

    # ── All action nodes → generate_response → save → END ────────────────────
    for node in ("search_products", "fashion_advice", "rl_recommendations"):
        graph.add_edge(node, "generate_response")

    graph.add_edge("generate_response", "save_user_state")
    graph.add_edge("save_user_state",   END)

    print("[GRAPH] Built successfully.")
    return graph.compile()


# ================================================================
# 🚀 COMPILED GRAPH EXPORT
# ================================================================

agent_graph = build_graph()

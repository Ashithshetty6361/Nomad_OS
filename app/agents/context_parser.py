"""
Context Parsing Agent: Extracts structured parameters, travel constraints, and intent.
"""
from app.agents.base import BaseAgent
from app.models.state import OrchestrationState, ContextState
from app.services.llm_service import llm_service


class ContextParsingAgent(BaseAgent):
    """
    Parses unstructured user input into structured travel preferences and constraints.
    Routes to AWS Bedrock Fast Model Tier (Claude 3 Haiku / Nova Micro) for minimal latency and cost.
    """
    def __init__(self):
        super().__init__(name="ContextParsingAgent", task_type="context_parsing")

    async def run(self, state: OrchestrationState) -> OrchestrationState:
        system_prompt = (
            "You are an expert Travel Context Analyzer. Your job is to extract exact travel parameters from user prompts.\n"
            "If the user does not specify a destination but shares their mood, companions, or purpose (e.g., 'concert with friends', 'quiet family retreat'), intelligently suggest the ideal destination city that fits that vibe.\n"
            "Return ONLY a JSON object with keys:\n"
            "- destination (string, e.g. 'Tokyo', 'Austin', 'Paris', 'Kyoto', 'Bali')\n"
            "- origin_city (string, default 'Current Location')\n"
            "- duration_days (integer, default 3 if unspecified)\n"
            "- budget_usd (float, default 2000.0 if unspecified)\n"
            "- travelers_count (integer, default 1)\n"
            "- companions (string: 'Solo', 'Couple', 'Friends', or 'Family with Kids')\n"
            "- travel_style (string, e.g., 'Live Concert & Nightlife', 'Family Relaxation', 'Foodie & Culture', 'Adventure')\n"
            "- trip_mood (string, e.g., 'Energetic & Social', 'Calm & Rejuvenating', 'Curious & Historic')\n"
            "- lodging_style (string: 'Boutique', 'Luxury Resort', 'Budget Friendly', or 'Central')\n"
            "- interests (list of strings)\n"
            "- constraints (list of strings)\n"
            "- confidence_score (float between 0.0 and 1.0)"
        )

        user_prompt = f"User Request: {state.raw_query}"

        result_json, telemetry = await llm_service.invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            task_type=self.task_type
        )

        context = ContextState(
            destination=result_json.get("destination", "Tokyo"),
            origin_city=result_json.get("origin_city", "Current Location"),
            duration_days=int(result_json.get("duration_days", 3)),
            budget_usd=float(result_json.get("budget_usd", 2000.0)),
            travelers_count=int(result_json.get("travelers_count", 1)),
            companions=result_json.get("companions", "Solo"),
            travel_style=result_json.get("travel_style", "Cultural Exploration"),
            trip_mood=result_json.get("trip_mood"),
            lodging_style=result_json.get("lodging_style", "Central"),
            interests=result_json.get("interests", []),
            constraints=result_json.get("constraints", []),
            confidence_score=float(result_json.get("confidence_score", 0.95)),
            model_used=telemetry["model_id"]
        )

        state.context = context
        state.models_routed[self.name] = telemetry["model_id"]
        state.tokens_consumed[self.name] = telemetry["prompt_tokens"] + telemetry["completion_tokens"]
        state.total_cost_usd += telemetry["cost_usd"]

        return state

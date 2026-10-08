"""
Discovery Agent: Generates curated point-of-interest, food spots, and neighborhood recommendations.
"""
from app.agents.base import BaseAgent
from app.models.state import OrchestrationState, DiscoveryState, ActivityItem
from app.services.llm_service import llm_service


class DiscoveryAgent(BaseAgent):
    """
    Identifies high-signal activities, distinct neighborhoods, and regional culinary highlights.
    """
    def __init__(self):
        super().__init__(name="DiscoveryAgent", task_type="discovery_filtering")

    async def run(self, state: OrchestrationState) -> OrchestrationState:
        if not state.context:
            raise ValueError("ContextState is missing prior to DiscoveryAgent execution.")

        ctx = state.context
        system_prompt = (
            "You are a master Local Destination Curator. Given the destination, style, and interests, generate curated recommendations.\n"
            "Return ONLY a JSON object with keys:\n"
            "- recommended_activities: list of objects with [name, category, estimated_duration_hours, estimated_cost_usd, location_area, description]\n"
            "- top_neighborhoods: list of strings (4 distinct areas)\n"
            "- local_culinary_highlights: list of strings"
        )

        user_prompt = (
            f"Destination: {ctx.destination}\n"
            f"Duration: {ctx.duration_days} days\n"
            f"Travel Style: {ctx.travel_style}\n"
            f"Interests: {', '.join(ctx.interests) if ctx.interests else 'General exploration'}\n"
            f"Budget: ${ctx.budget_usd}"
        )

        result_json, telemetry = await llm_service.invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            task_type=self.task_type
        )

        activities = [
            ActivityItem(
                name=act.get("name", "Local Landmark Tour"),
                category=act.get("category", "Culture"),
                estimated_duration_hours=float(act.get("estimated_duration_hours", 2.0)),
                estimated_cost_usd=float(act.get("estimated_cost_usd", 30.0)),
                location_area=act.get("location_area", "Central District"),
                description=act.get("description", "Immersive local activity.")
            )
            for act in result_json.get("recommended_activities", [])
        ]

        state.discovery = DiscoveryState(
            recommended_activities=activities,
            top_neighborhoods=result_json.get("top_neighborhoods", []),
            local_culinary_highlights=result_json.get("local_culinary_highlights", []),
            model_used=telemetry["model_id"]
        )

        state.models_routed[self.name] = telemetry["model_id"]
        state.tokens_consumed[self.name] = telemetry["prompt_tokens"] + telemetry["completion_tokens"]
        state.total_cost_usd += telemetry["cost_usd"]

        return state

"""
RAG-based Enrichment Agent: Queries ChromaDB vector store for localized guides, hidden gems, and etiquette.
"""
from app.agents.base import BaseAgent
from app.models.state import OrchestrationState, EnrichmentState
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service


class RAGEnrichmentAgent(BaseAgent):
    """
    Augments discovery data with verified local knowledge retrieved from the vector database.
    """
    def __init__(self):
        super().__init__(name="RAGEnrichmentAgent", task_type="enrichment_extraction")

    async def run(self, state: OrchestrationState) -> OrchestrationState:
        if not state.context:
            raise ValueError("ContextState is missing prior to RAGEnrichmentAgent execution.")

        ctx = state.context
        # 1. Retrieve relevant knowledge documents from ChromaDB
        search_query = f"{ctx.travel_style} {' '.join(ctx.interests)}"
        retrieved_docs = rag_service.retrieve_destination_context(
            destination=ctx.destination,
            query=search_query,
            top_k=3
        )

        # 2. Synthesize retrieved knowledge into actionable guidance
        rag_context_text = "\n\n".join([f"[{d.category}] {d.title}: {d.content}" for d in retrieved_docs])
        
        system_prompt = (
            "You are a Destination Intelligence & Etiquette Specialist.\n"
            "Using the retrieved knowledge base, synthesize essential local insider tips and etiquette.\n"
            "Return ONLY a JSON object with keys:\n"
            "- local_pro_tips: list of strings (practical tips, timing, booking tricks)\n"
            "- cultural_etiquette: list of strings (local customs, tipping, attire rules)\n"
            "- transport_advice: string (optimal transit cards/methods)"
        )

        user_prompt = (
            f"Destination: {ctx.destination}\n"
            f"Retrieved Knowledge Context:\n{rag_context_text}"
        )

        result_json, telemetry = await llm_service.invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            task_type=self.task_type
        )

        state.enrichment = EnrichmentState(
            retrieved_guides=retrieved_docs,
            local_pro_tips=result_json.get("local_pro_tips", []),
            cultural_etiquette=result_json.get("cultural_etiquette", []),
            transport_advice=result_json.get("transport_advice", "Use local transit card."),
            model_used=telemetry["model_id"]
        )

        state.models_routed[self.name] = telemetry["model_id"]
        state.tokens_consumed[self.name] = telemetry["prompt_tokens"] + telemetry["completion_tokens"]
        state.total_cost_usd += telemetry["cost_usd"]

        return state

"""
Deterministic Multi-Agent Planner and State Orchestrator.
"""
import uuid
import time
from typing import Tuple, List
from app.models.requests import PlanRequest
from app.models.state import OrchestrationState
from app.models.responses import PlanResponse, AgentStepLog, TelemetrySummary
from app.agents.context_parser import ContextParsingAgent
from app.agents.discovery_agent import DiscoveryAgent
from app.agents.rag_enrichment_agent import RAGEnrichmentAgent
from app.agents.booking_agent import BookingReasoningAgent
from app.core.logging import logger, correlation_id_ctx
from app.core.metrics import Timer
from app.core.exceptions import InvalidPlanStateError, AgentExecutionError


class PlannerService:
    """
    Deterministic Planner isolating workflow business logic, state transitions,
    and runtime telemetry aggregation from individual agent implementations.
    """
    def __init__(self):
        self.context_agent = ContextParsingAgent()
        self.discovery_agent = DiscoveryAgent()
        self.rag_agent = RAGEnrichmentAgent()
        self.booking_agent = BookingReasoningAgent()

    async def execute_plan_pipeline(self, request: PlanRequest) -> PlanResponse:
        """
        Executes the multi-agent pipeline sequentially with strict contract verification.
        """
        trace_id = f"trace-{uuid.uuid4().hex[:8]}"
        correlation_id_ctx.set(trace_id)
        
        logger.info(f"Starting multi-agent orchestration for query: '{request.query}'", extra={"trace_id": trace_id})
        
        state = OrchestrationState(
            trace_id=trace_id,
            raw_query=request.query
        )

        agent_logs: List[AgentStepLog] = []
        
        with Timer() as total_timer:
            # 1. Context Parsing Agent
            state.current_step = "CONTEXT_PARSING"
            state = await self.context_agent.execute(state)
            if not state.context:
                raise InvalidPlanStateError("ContextParsing", "Failed to produce valid ContextState.")
            
            agent_logs.append(AgentStepLog(
                step_name="1. Context Extraction",
                agent_name=self.context_agent.name,
                model_id=state.models_routed.get(self.context_agent.name, "Fast Tier"),
                latency_ms=state.step_latencies.get(self.context_agent.name, 0.0),
                summary=f"Extracted destination: {state.context.destination}, {state.context.duration_days} days, budget: ${state.context.budget_usd}",
                key_outputs={"travel_style": state.context.travel_style, "interests": state.context.interests}
            ))

            # 2. Discovery Agent
            state.current_step = "DISCOVERY"
            state = await self.discovery_agent.execute(state)
            if not state.discovery:
                raise InvalidPlanStateError("Discovery", "Failed to produce valid DiscoveryState.")
                
            agent_logs.append(AgentStepLog(
                step_name="2. Destination Discovery",
                agent_name=self.discovery_agent.name,
                model_id=state.models_routed.get(self.discovery_agent.name, "Fast Tier"),
                latency_ms=state.step_latencies.get(self.discovery_agent.name, 0.0),
                summary=f"Discovered {len(state.discovery.recommended_activities)} curated activities and {len(state.discovery.top_neighborhoods)} key neighborhoods.",
                key_outputs={"top_neighborhoods": state.discovery.top_neighborhoods, "culinary": state.discovery.local_culinary_highlights}
            ))

            # 3. RAG Enrichment Agent
            state.current_step = "RAG_ENRICHMENT"
            state = await self.rag_agent.execute(state)
            if not state.enrichment:
                raise InvalidPlanStateError("RAGEnrichment", "Failed to produce valid EnrichmentState.")

            agent_logs.append(AgentStepLog(
                step_name="3. RAG Knowledge Enrichment",
                agent_name=self.rag_agent.name,
                model_id=state.models_routed.get(self.rag_agent.name, "Vector RAG + Fast"),
                latency_ms=state.step_latencies.get(self.rag_agent.name, 0.0),
                summary=f"Retrieved {len(state.enrichment.retrieved_guides)} vector documents from ChromaDB with verified local insights.",
                key_outputs={"pro_tips": state.enrichment.local_pro_tips, "transit": state.enrichment.transport_advice}
            ))

            # 4. Booking & Reasoning Agent
            state.current_step = "BOOKING_REASONING"
            state = await self.booking_agent.execute(state)
            if not state.booking:
                raise InvalidPlanStateError("BookingReasoning", "Failed to produce valid BookingState.")

            agent_logs.append(AgentStepLog(
                step_name="4. Booking & Schedule Synthesis",
                agent_name=self.booking_agent.name,
                model_id=state.models_routed.get(self.booking_agent.name, "Reasoning Tier"),
                latency_ms=state.step_latencies.get(self.booking_agent.name, 0.0),
                summary=f"Constructed {len(state.booking.daily_itinerary)}-day schedule with optimized budget allocation: ${state.booking.total_estimated_cost_usd}.",
                key_outputs={"budget_breakdown": state.booking.budget_breakdown, "variance": state.booking.budget_variance_status}
            ))

            state.current_step = "COMPLETED"

        # Calculate cost savings from cost-aware dynamic routing vs pure Claude 3.5 Sonnet
        total_tokens = sum(state.tokens_consumed.values())
        # Cost if all tokens were run on Sonnet ($0.003 / $0.015 per 1k)
        baseline_sonnet_cost = (total_tokens / 1000.0) * 0.009
        cost_savings = max(0.0, round(baseline_sonnet_cost - state.total_cost_usd, 6))

        telemetry = TelemetrySummary(
            trace_id=trace_id,
            total_latency_ms=total_timer.latency_ms,
            step_latencies=state.step_latencies,
            total_tokens=total_tokens,
            estimated_cost_usd=round(state.total_cost_usd, 6),
            models_used=state.models_routed,
            cost_savings_usd=cost_savings
        )

        logger.info(
            f"Pipeline completed in {total_timer.latency_ms}ms with total cost ${state.total_cost_usd:.6f}",
            extra={"cost_usd": state.total_cost_usd, "latency_ms": total_timer.latency_ms}
        )

        return PlanResponse(
            status="SUCCESS",
            destination=state.context.destination,
            duration_days=state.context.duration_days,
            travel_style=state.context.travel_style,
            total_budget_usd=state.context.budget_usd,
            estimated_cost_usd=state.booking.total_estimated_cost_usd,
            budget_breakdown=state.booking.budget_breakdown,
            trade_off_reasoning=state.booking.trade_off_reasoning,
            daily_itinerary=state.booking.daily_itinerary,
            enrichment_insights={
                "local_pro_tips": state.enrichment.local_pro_tips,
                "cultural_etiquette": state.enrichment.cultural_etiquette,
                "transport_advice": state.enrichment.transport_advice,
                "vector_documents": [
                    {"title": doc.title, "category": doc.category, "score": doc.relevance_score, "source": doc.source}
                    for doc in state.enrichment.retrieved_guides
                ]
            },
            # Door-to-Door, Lodging, Dining & Packing
            origin_city=state.context.origin_city,
            companions=state.context.companions,
            trip_mood=state.context.trip_mood,
            origin_transit=state.booking.origin_transit,
            lodging_options=state.booking.lodging_options,
            dining_highlights=state.booking.dining_highlights,
            packing_checklist=state.booking.packing_checklist,
            agent_steps=agent_logs,
            telemetry=telemetry
        )



planner_service = PlannerService()

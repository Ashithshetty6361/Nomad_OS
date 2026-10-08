"""
Observability and model router metadata endpoint.
"""
from fastapi import APIRouter
from app.config import settings
from app.services.rag_service import rag_service

router = APIRouter()


@router.get("/observability/models", summary="List Available AI Models & Cost Tiers")
async def get_models_metadata():
    """
    Returns configured model routing tiers and pricing parameters for observability.
    Supports Local Offline LLMs (Ollama), AWS Bedrock, and Google Gemini.
    """
    return {
        "active_provider": "Local_Ollama" if settings.USE_LOCAL_LLM else "AWS_Bedrock",
        "local_llm": {
            "enabled": settings.USE_LOCAL_LLM,
            "base_url": settings.OLLAMA_BASE_URL,
            "fast_model": settings.OLLAMA_FAST_MODEL,
            "reasoning_model": settings.OLLAMA_REASONING_MODEL,
            "embedding_model": settings.OLLAMA_EMBEDDING_MODEL,
            "cost_per_query": "$0.00 (Offline Real AI)"
        },
        "fast_tier": {
            "model_id": settings.OLLAMA_FAST_MODEL if settings.USE_LOCAL_LLM else settings.BEDROCK_FAST_MODEL_ID,
            "tasks": ["context_parsing", "discovery_filtering", "enrichment_extraction"],
            "input_cost_per_1k": 0.0 if settings.USE_LOCAL_LLM else settings.HAIKU_INPUT_COST_PER_1K,
            "output_cost_per_1k": 0.0 if settings.USE_LOCAL_LLM else settings.HAIKU_OUTPUT_COST_PER_1K
        },
        "reasoning_tier": {
            "model_id": settings.OLLAMA_REASONING_MODEL if settings.USE_LOCAL_LLM else settings.BEDROCK_REASONING_MODEL_ID,
            "tasks": ["booking_reasoning", "itinerary_optimization"],
            "input_cost_per_1k": 0.0 if settings.USE_LOCAL_LLM else settings.SONNET_INPUT_COST_PER_1K,
            "output_cost_per_1k": 0.0 if settings.USE_LOCAL_LLM else settings.SONNET_OUTPUT_COST_PER_1K
        },
        "embedding_tier": {
            "model_id": settings.OLLAMA_EMBEDDING_MODEL if settings.USE_LOCAL_LLM else settings.BEDROCK_EMBEDDING_MODEL_ID,
            "tasks": ["rag_vector_search"]
        },
        "vector_store": {
            "provider": "ChromaDB",
            "indexed_guides_count": rag_service.collection.count() if rag_service.collection else 0
        },
        "provider_status": "Local Offline LLM (Ollama: Phi-3 & Llama-3.1) + ChromaDB" if settings.USE_LOCAL_LLM else "AWS Bedrock (boto3) / Deterministic Provider"
    }


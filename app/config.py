import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "NomadOS Multi-Agent Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Logging
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # AWS Bedrock Credentials & Models
    AWS_REGION: str = "us-east-1"
    AWS_PROFILE: Optional[str] = "nomados"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # Bedrock Model IDs for Cost-Aware Model Routing
    # Fast / Lightweight model for parsing & discovery routing (e.g., Claude 3 Haiku or Nova Micro)
    BEDROCK_FAST_MODEL_ID: str = "anthropic.claude-3-haiku-20240307-v1:0"
    # Heavy / Reasoning model for complex itinerary synthesis & constraint optimization (Claude 3.5 Sonnet)
    BEDROCK_REASONING_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    # Embedding model for RAG vector search
    BEDROCK_EMBEDDING_MODEL_ID: str = "amazon.titan-embed-text-v2:0"
    
    # Cost per 1k tokens (AWS Bedrock pricing for cost estimation)
    HAIKU_INPUT_COST_PER_1K: float = 0.00025
    HAIKU_OUTPUT_COST_PER_1K: float = 0.00125
    SONNET_INPUT_COST_PER_1K: float = 0.003
    SONNET_OUTPUT_COST_PER_1K: float = 0.015
    
    # Flag to enable local mock LLM fallback if AWS credentials aren't present
    USE_MOCK_LLM: bool = True
    
    # ChromaDB Vector Store
    CHROMA_PERSIST_DIR: str = os.environ.get("CHROMA_PERSIST_DIR", "/tmp/chroma_db" if os.environ.get("VERCEL") else "./chroma_db")
    
    # Uber Rides API Credentials & Config
    UBER_CLIENT_ID: Optional[str] = None
    UBER_CLIENT_SECRET: Optional[str] = None
    UBER_SERVER_TOKEN: Optional[str] = None
    UBER_API_BASE_URL: str = "https://api.uber.com/v1.2"
    UBER_SANDBOX_BASE_URL: str = "https://sandbox-api.uber.com/v1.2"
    UBER_SANDBOX_MODE: bool = True
    UBER_MOCK_FALLBACK: bool = True
    
    # Rate Limiting (Protects Bedrock & Uber quotas from abuse)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PLAN_PER_MINUTE: int = 10
    RATE_LIMIT_UBER_PER_MINUTE: int = 30
    
    # Zero-Cost Free-Tier AI Provider (Google AI Studio Gemini)
    # Allows 100% free live real AI execution (15 RPM / 1,500 RPD free forever)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_ID: str = "gemini-1.5-flash"
    
    # Local Offline LLM Provider (Ollama: Phi-3, Llama 3.1, Nomic Embed Text)
    USE_LOCAL_LLM: bool = True
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_FAST_MODEL: str = "phi3:mini"
    OLLAMA_REASONING_MODEL: str = "llama3.1:8b-instruct-q4_K_M"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text:latest"
    OLLAMA_REQUEST_TIMEOUT: float = 25.0
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

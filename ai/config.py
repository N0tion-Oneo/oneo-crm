"""
AI system configuration and settings
"""
from typing import Dict, Any, Optional
from pydantic import BaseSettings
from enum import Enum
import os


class AIProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class VectorProvider(str, Enum):
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    CHROMA = "chroma"
    FAISS = "faiss"


class AIConfig(BaseSettings):
    """AI system configuration"""
    
    # API Keys
    openai_api_key: str = "demo-key"
    anthropic_api_key: str = "demo-key"
    pinecone_api_key: Optional[str] = None
    weaviate_url: Optional[str] = None
    
    # Model configurations
    default_completion_model: str = "gpt-4o-mini"
    default_embedding_model: str = "text-embedding-3-small"
    max_tokens: int = 2000
    temperature: float = 0.7
    
    # Vector database settings
    vector_provider: VectorProvider = VectorProvider.CHROMA
    vector_dimension: int = 1536
    similarity_threshold: float = 0.8
    
    # Processing limits
    max_concurrent_requests: int = 10
    rate_limit_requests_per_minute: int = 1000
    cost_tracking_enabled: bool = True
    
    # Caching
    cache_embeddings: bool = True
    cache_completions: bool = True
    cache_ttl: int = 3600  # 1 hour
    
    class Config:
        env_prefix = "AI_"
        case_sensitive = False


# Global AI configuration
ai_config = AIConfig()
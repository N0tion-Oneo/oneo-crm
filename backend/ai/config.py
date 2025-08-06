"""
AI system configuration and settings
"""
from typing import Dict, Any, Optional
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


class AIConfig:
    """AI system configuration"""
    
    def __init__(self):
        # API Keys
        self.openai_api_key = os.getenv('AI_OPENAI_API_KEY', 'demo-key')
        self.anthropic_api_key = os.getenv('AI_ANTHROPIC_API_KEY', 'demo-key')
        self.pinecone_api_key = os.getenv('AI_PINECONE_API_KEY')
        self.weaviate_url = os.getenv('AI_WEAVIATE_URL')
        
        # Model configurations
        self.default_completion_model = os.getenv('AI_DEFAULT_COMPLETION_MODEL', 'gpt-4.1-mini')
        self.default_embedding_model = os.getenv('AI_DEFAULT_EMBEDDING_MODEL', 'text-embedding-3-small')
        self.max_tokens = int(os.getenv('AI_MAX_TOKENS', '2000'))
        self.temperature = float(os.getenv('AI_TEMPERATURE', '0.7'))
        
        # Vector database settings
        self.vector_provider = VectorProvider(os.getenv('AI_VECTOR_PROVIDER', VectorProvider.CHROMA))
        self.vector_dimension = int(os.getenv('AI_VECTOR_DIMENSION', '1536'))
        self.similarity_threshold = float(os.getenv('AI_SIMILARITY_THRESHOLD', '0.8'))
        
        # Processing limits
        self.max_concurrent_requests = int(os.getenv('AI_MAX_CONCURRENT_REQUESTS', '10'))
        self.rate_limit_requests_per_minute = int(os.getenv('AI_RATE_LIMIT_REQUESTS_PER_MINUTE', '1000'))
        self.cost_tracking_enabled = os.getenv('AI_COST_TRACKING_ENABLED', 'True').lower() == 'true'
        
        # Caching
        self.cache_embeddings = os.getenv('AI_CACHE_EMBEDDINGS', 'True').lower() == 'true'
        self.cache_completions = os.getenv('AI_CACHE_COMPLETIONS', 'True').lower() == 'true'
        self.cache_ttl = int(os.getenv('AI_CACHE_TTL', '3600'))  # 1 hour


# Global AI configuration
ai_config = AIConfig()
"""
AI-Assistant-SelfTutoring - Configuration
Version 2.0.0
"""
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def detect_ollama_model_variant(base_model: str, ollama_host: str = 'http://localhost:11434') -> str:
    """
    Detect the actual model variant available in Ollama.

    Args:
        base_model: Base model name (e.g., 'llama3.2', 'mxbai-embed-large')
        ollama_host: Ollama API host

    Returns:
        Full model name with tag if found (e.g., 'llama3.2:1b'), or base_model if not found
    """
    try:
        response = requests.get(f"{ollama_host}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            # Look for exact match first
            for model in models:
                model_name = model.get('name', '')
                if model_name == base_model:
                    return base_model

            # Look for variant (base model with tag)
            for model in models:
                model_name = model.get('name', '')
                # Check if model name starts with base_model followed by ':'
                if model_name.startswith(base_model + ':'):
                    print(f"ℹ️  Auto-detected model variant: {model_name} (configured: {base_model})")
                    return model_name
                # Also check without tag separator (e.g., llama3.2 vs llama3.2:1b)
                if model_name.split(':')[0] == base_model:
                    print(f"ℹ️  Auto-detected model variant: {model_name} (configured: {base_model})")
                    return model_name
    except Exception as e:
        print(f"⚠️  Could not detect Ollama model variant: {e}")

    return base_model

# =============================================================================
# APPLICATION INFO
# =============================================================================

APP_NAME = "AI-Assistant-SelfTutoring"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "Self-tutoring AI assistant with document grounding, knowledge graphs, and deep research"

# =============================================================================
# FEATURE FLAGS (can be overridden at runtime via API)
# =============================================================================

ENABLE_KNOWLEDGE_GRAPH = os.getenv('ENABLE_KNOWLEDGE_GRAPH', 'false').lower() == 'true'
ENABLE_LLM_ENTITY_EXTRACTION = os.getenv('ENABLE_LLM_ENTITY_EXTRACTION', 'false').lower() == 'true'
ENABLE_GUARDRAILS = os.getenv('ENABLE_GUARDRAILS', 'true').lower() == 'true'

# =============================================================================
# RUNTIME CONFIG (mutable at runtime)
# =============================================================================

class RuntimeConfig:
    """Runtime configuration that can be changed via API"""
    
    def __init__(self):
        self.knowledge_graph_enabled = ENABLE_KNOWLEDGE_GRAPH
        self.entity_extraction_enabled = ENABLE_LLM_ENTITY_EXTRACTION
        self.neo4j_connected = False
        self.entity_extractor_ready = False
        self.guardrails_enabled = ENABLE_GUARDRAILS
        
        # Search parameters (adjustable at runtime)
        self.search_params = {
            'top_k': int(os.getenv('TOP_K_RESULTS', '6')),
            'min_relevance': float(os.getenv('MIN_RELEVANCE_SCORE', '0.3')),
            'use_reranking': os.getenv('USE_RERANKING', 'false').lower() == 'true',
            'search_mode': os.getenv('SEARCH_MODE', 'hybrid'),  # vector, graph, hybrid
            'context_window': int(os.getenv('CONTEXT_WINDOW', '6000')),
        }
        
        # Guardrails settings
        self.guardrails_config = {
            'block_injection': True,
            'block_jailbreak': True,
            'pii_redaction': True,
            'content_filtering': True,
            'log_blocked': True,
            'strict_mode': False,  # If True, more aggressive blocking
        }
    
    def to_dict(self):
        return {
            'knowledge_graph_enabled': self.knowledge_graph_enabled,
            'entity_extraction_enabled': self.entity_extraction_enabled,
            'neo4j_connected': self.neo4j_connected,
            'entity_extractor_ready': self.entity_extractor_ready,
            'guardrails_enabled': self.guardrails_enabled,
            'search_params': self.search_params,
            'guardrails_config': self.guardrails_config,
        }
    
    def update_search_params(self, params: dict):
        """Update search parameters"""
        for key, value in params.items():
            if key in self.search_params:
                self.search_params[key] = value
    
    def update_guardrails_config(self, config: dict):
        """Update guardrails configuration"""
        for key, value in config.items():
            if key in self.guardrails_config:
                self.guardrails_config[key] = value

# Global runtime config instance
runtime_config = RuntimeConfig()

# =============================================================================
# FOLDER PATHS
# =============================================================================

UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './data_store')
CHROMA_DB = os.getenv('CHROMA_DB', './chroma_graphrag_db')
ENTITY_CACHE = os.getenv('ENTITY_CACHE', './entity_resolution_cache.json')
INDEXED_FILES_TRACKER = os.getenv('INDEXED_FILES_TRACKER', './indexed_files.json')
GUARDRAILS_CONFIG_PATH = os.getenv('GUARDRAILS_CONFIG_PATH', './guardrails/config.yml')

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =============================================================================
# NEO4J CONFIGURATION (only used if ENABLE_KNOWLEDGE_GRAPH = True)
# =============================================================================

NEO4J_CONFIG = {
    'uri': os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
    'user': os.getenv('NEO4J_USER', 'neo4j'),
    'password': os.getenv('NEO4J_PASSWORD', 'password')
}

# =============================================================================
# LLM CONFIGURATION
# =============================================================================

# Ollama Host (for Docker: http://host.docker.internal:11434 or http://ollama:11434)
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')

# Get base model names from environment
_LLM_MODEL_BASE = os.getenv('LLM_MODEL', 'llama3.2')
_EMBEDDING_MODEL_BASE = os.getenv('EMBEDDING_MODEL', 'mxbai-embed-large')

# Auto-detect actual model variants available in Ollama
# This handles cases where user has llama3.2:1b instead of llama3.2
LLM_MODEL = detect_ollama_model_variant(_LLM_MODEL_BASE, OLLAMA_HOST)
EMBEDDING_MODEL = detect_ollama_model_variant(_EMBEDDING_MODEL_BASE, OLLAMA_HOST)

LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.3'))

# LLM Request Timeout
LLM_REQUEST_TIMEOUT = int(os.getenv('LLM_REQUEST_TIMEOUT', '120'))

# =============================================================================
# FILE UPLOAD SETTINGS
# =============================================================================

# Maximum upload size (50MB)
MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(50 * 1024 * 1024)))

# Supported file extensions
SUPPORTED_EXTENSIONS = {'pdf', 'docx', 'txt', 'csv', 'json', 'md', 'html', 'xml'}

# =============================================================================
# CHUNKING SETTINGS
# =============================================================================

# Smaller chunks to fit within embedding model context (mxbai-embed-large ~512 tokens)
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '500'))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '100'))

# =============================================================================
# SEARCH SETTINGS (defaults, can be changed at runtime)
# =============================================================================

TOP_K_RESULTS = int(os.getenv('TOP_K_RESULTS', '6'))
MIN_RELEVANCE_SCORE = float(os.getenv('MIN_RELEVANCE_SCORE', '0.3'))

# =============================================================================
# GUARDRAILS SETTINGS
# =============================================================================

GUARDRAILS_ENABLED = os.getenv('ENABLE_GUARDRAILS', 'true').lower() == 'true'
GUARDRAILS_STRICT_MODE = os.getenv('GUARDRAILS_STRICT_MODE', 'false').lower() == 'true'

# Disable telemetry
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

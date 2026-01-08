"""
Hybrid Search and LLM Prompts
Combines vector search (ChromaDB) with graph search (Neo4j)
"""
from langchain_core.prompts import ChatPromptTemplate


def hybrid_search(query, vector_store, neo4j_graph=None, top_k=8):
    """
    Combine ChromaDB vector search with Neo4j entity search (if enabled).
    Searches ALL documents in data_store (persisted across sessions).
    
    Args:
        query: Search query string
        vector_store: ChromaDB vector store
        neo4j_graph: Neo4j graph instance (can be None if KG disabled)
        top_k: Number of results to return
    
    Returns: (vector_results, graph_results)
    """
    from config import runtime_config
    
    vector_results = []
    graph_results = []

    # 1) Vector search via ChromaDB (ALWAYS)
    try:
        docs = vector_store.similarity_search_with_relevance_scores(query, k=top_k)
        for d, score in docs:
            source = d.metadata.get('source', 'unknown') if hasattr(d, 'metadata') else 'unknown'
            vector_results.append({
                'text': d.page_content,
                'source': source,
                'source_path': d.metadata.get('source_path', source),
                'relevance_score': score,
                'chunk_index': d.metadata.get('chunk_index', 0)
            })
        
        # Sort by relevance score (highest first)
        vector_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
    except Exception as e:
        print(f"Vector search error: {e}")
        # Fallback to basic search
        try:
            docs = vector_store.similarity_search(query, k=top_k)
            for d in docs:
                source = d.metadata.get('source', 'unknown') if hasattr(d, 'metadata') else 'unknown'
                vector_results.append({
                    'text': d.page_content,
                    'source': source,
                    'source_path': d.metadata.get('source_path', source),
                    'relevance_score': 0.5
                })
        except Exception as e2:
            print(f"Fallback search error: {e2}")

    # 2) Neo4j entity search (OPTIONAL - only if enabled AND connected)
    if runtime_config.knowledge_graph_enabled and neo4j_graph is not None:
        try:
            graph_results = neo4j_graph.search_entities(query, limit=top_k)
        except Exception as e:
            print(f"Graph search error: {e}")

    return vector_results, graph_results


def build_context(vector_hits, graph_hits, max_context_chars=6000):
    """Build context string from search results with size limits"""
    context_parts = []
    total_chars = 0
    
    if vector_hits:
        context_parts.append("=== DOCUMENT EXCERPTS FROM YOUR DATA_STORE ===\n")
        total_chars += 50
        
        # Group by source for better organization
        sources_seen = {}
        for i, v in enumerate(vector_hits[:5], 1):  # Limit to 5 hits
            src = v.get('source') or 'unknown'
            text = v.get('text', '').strip()
            score = v.get('relevance_score', 0)
            
            if text:
                # Truncate individual chunks to prevent overflow
                max_chunk = min(800, (max_context_chars - total_chars) // 2)
                if len(text) > max_chunk:
                    text = text[:max_chunk] + "..."
                
                chunk_text = f"[Document {i}: {src}] (relevance: {score:.2f})\n{text}\n"
                
                # Check if we're exceeding max context
                if total_chars + len(chunk_text) > max_context_chars:
                    break
                    
                context_parts.append(chunk_text)
                total_chars += len(chunk_text)
                sources_seen[src] = True
        
        if sources_seen:
            context_parts.append(f"\nSources: {', '.join(sources_seen.keys())}")
    
    if graph_hits and total_chars < max_context_chars - 500:
        context_parts.append('\n\n=== RELATED ENTITIES FROM KNOWLEDGE GRAPH ===')
        for g in graph_hits[:5]:  # Limit to 5 entities
            entity_info = f"• {g.get('name')} ({g.get('type')})"
            context_parts.append(entity_info)
    
    if context_parts:
        return "\n".join(context_parts)
    
    return ''


def has_meaningful_context(vector_hits, min_score=0.3):
    """Check if we have meaningful context to answer from"""
    if not vector_hits:
        return False
    
    # Check if at least one result has decent relevance
    for hit in vector_hits:
        score = hit.get('relevance_score', 0)
        if score >= min_score:
            return True
        # If no score available, assume it might be relevant
        if score == 0 and hit.get('text'):
            return True
    
    return False


# ============================================================================
# LLM PROMPTS
# ============================================================================

# Primary prompt - Uses document context from data_store
DOCUMENT_GROUNDED_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful AI assistant. Answer the user's question using the provided context from their document repository.

GUIDELINES:
1. IMPORTANT: The context below has ALREADY been filtered as relevant to the question. Use it to answer!
2. Use the information from the Context to answer the question
3. If the context contains ANY related information, even partially, USE IT to provide a helpful answer
4. Cite which document(s) the information comes from
5. Be helpful - try to answer based on what IS in the context, even if it's not a perfect match
6. ONLY respond with [NO_CONTEXT] if the context is COMPLETELY EMPTY or talks about a totally different topic
7. If you can partially answer from the context, do so and mention what additional information might be helpful

Context from data_store documents (these documents were selected as relevant to your question):
{context}

---
User Question: {input}

Provide a helpful answer based on the context above. The documents shown are relevant - use them to answer:"""),
    ("human", "{input}")
])

# Secondary prompt - Used ONLY when user explicitly approves general knowledge
GENERAL_KNOWLEDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful AI assistant. The user's documents don't contain the specific answer, but they have approved using your general knowledge.

Provide helpful, accurate information based on your training. Be clear this is general knowledge, not from their specific documents.

User Question: {input}

Provide a helpful answer based on your knowledge:"""),
    ("human", "{input}")
])


# ============================================================================
# RESPONSE MESSAGES
# ============================================================================

NO_CONTEXT_MESSAGE = (
    "🔍 I couldn't find any relevant information in your data_store documents "
    "for this question.\n\nWould you like me to answer based on my general knowledge instead?"
)

INSUFFICIENT_CONTEXT_MESSAGE = (
    "🔍 I found some documents in your data_store, but they don't seem to contain "
    "the specific information needed to fully answer your question.\n\n"
    "Would you like me to answer based on my general knowledge instead?"
)

GENERAL_KNOWLEDGE_PREFIX = "⚠️ **Based on General Knowledge (not from your documents):**\n\nI'm here to help answer your questions. My responses are based on general knowledge and not specifically tailored to your organization's documents. Feel free to ask about any topic, and I'll provide the best information I can.\n\n"

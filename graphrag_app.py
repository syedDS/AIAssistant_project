"""
AI-Assistant-SelfTutoring - Main Application
=============================================
A self-tutoring AI assistant with document grounding, knowledge graphs, and deep research.

Features:
- Vector embeddings for semantic search (ChromaDB) - ALWAYS ON
- Knowledge graph for entity relationships (Neo4j) - OPTIONAL
- Persistent data_store (all documents searchable across sessions)
- Deep research with web search
- Configurable security guardrails

Run: python graphrag_app.py
"""
import os
import secrets
import requests
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma

# Import configurations
from config import (
    UPLOAD_FOLDER, CHROMA_DB, MAX_CONTENT_LENGTH,
    LLM_MODEL, LLM_TEMPERATURE, EMBEDDING_MODEL, OLLAMA_HOST,
    ENABLE_KNOWLEDGE_GRAPH, ENABLE_LLM_ENTITY_EXTRACTION,
    TOP_K_RESULTS, runtime_config
)

# Import classes
from file_tracker import IndexedFilesTracker

# Import functions
from document_processor import (
    process_document, 
    extract_text_from_file,
    scan_and_index_data_store
)
from search import (
    hybrid_search, 
    build_context,
    DOCUMENT_GROUNDED_PROMPT,
    GENERAL_KNOWLEDGE_PROMPT,
    NO_CONTEXT_MESSAGE,
    INSUFFICIENT_CONTEXT_MESSAGE,
    GENERAL_KNOWLEDGE_PREFIX
)

# Import Guardrails
from guardrails_handler import (
    get_guardrails_handler,
    check_input_security,
    check_output_security,
    SecurityLevel
)


# ============================================================================
# FLASK APP SETUP
# ============================================================================

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH


# ============================================================================
# INITIALIZE ALL COMPONENTS
# ============================================================================

print("\n" + "="*60)
print("🏭 GRAPHRAG SECURITY ARCHITECT")
print("="*60)

# Show mode
if ENABLE_KNOWLEDGE_GRAPH:
    print("📊 Mode: Full (Vector + Knowledge Graph)")
else:
    print("⚡ Mode: Fast (Vector Search Only)")

# 1. Create File Tracker
print("\n📁 Initializing File Tracker...")
indexed_tracker = IndexedFilesTracker()

# 2. Create LLM with timeout
print(f"🤖 Initializing LLM ({LLM_MODEL})...")
print(f"   Ollama Host: {OLLAMA_HOST}")

# Parse Ollama host for base_url
ollama_base_url = OLLAMA_HOST.rstrip('/')

# Verify Ollama connectivity
print(f"\n🔗 Verifying Ollama connection at {ollama_base_url}...")
try:
    ollama_check = requests.get(f"{ollama_base_url}/api/tags", timeout=10)
    if ollama_check.status_code == 200:
        models = ollama_check.json().get('models', [])
        model_names = [m.get('name', '') for m in models]
        print(f"   ✅ Ollama connected. Available models: {', '.join(model_names[:5])}")
        
        # Check for required models
        if not any(EMBEDDING_MODEL.split(':')[0] in m for m in model_names):
            print(f"   ⚠️  Warning: {EMBEDDING_MODEL} not found. Run: ollama pull {EMBEDDING_MODEL}")
        if not any(LLM_MODEL.split(':')[0] in m for m in model_names):
            print(f"   ⚠️  Warning: {LLM_MODEL} not found. Run: ollama pull {LLM_MODEL}")
    else:
        print(f"   ⚠️  Ollama responded with status {ollama_check.status_code}")
except requests.exceptions.ConnectionError:
    print(f"   ❌ Cannot connect to Ollama at {ollama_base_url}")
    print(f"   💡 Make sure Ollama is running: ollama serve")
except Exception as e:
    print(f"   ⚠️  Ollama check error: {e}")

llm = ChatOllama(
    model=LLM_MODEL, 
    temperature=LLM_TEMPERATURE,
    base_url=ollama_base_url,
    num_ctx=4096,  # Context window size
    timeout=120    # 2 minute timeout
)

# 3. OPTIONAL: Create Neo4j Graph and Entity Extractor
neo4j_graph = None
entity_extractor = None
entity_resolver = None

if ENABLE_KNOWLEDGE_GRAPH:
    print("🕸️  Initializing Neo4j (Knowledge Graph enabled)...")
    try:
        from entity_resolver import EntityResolver
        from neo4j_graph import ValidatedNeo4jGraph
        
        entity_resolver = EntityResolver()
        neo4j_graph = ValidatedNeo4jGraph(entity_resolver)
        runtime_config.neo4j_connected = True
        runtime_config.knowledge_graph_enabled = True
    except Exception as e:
        print(f"⚠️  Neo4j initialization failed: {e}")
        print("   Continuing without Knowledge Graph...")
        neo4j_graph = None
        runtime_config.neo4j_connected = False

if ENABLE_LLM_ENTITY_EXTRACTION and neo4j_graph:
    print("🔍 Initializing Entity Extractor (LLM extraction enabled)...")
    try:
        from entity_extractor import ValidatedEntityExtractor
        entity_extractor = ValidatedEntityExtractor(llm)
        runtime_config.entity_extractor_ready = True
        runtime_config.entity_extraction_enabled = True
    except Exception as e:
        print(f"⚠️  Entity Extractor initialization failed: {e}")
        entity_extractor = None
        runtime_config.entity_extractor_ready = False
else:
    print("⚡ Entity extraction disabled (fast indexing mode)")

# 4. Create Embeddings & Vector Store (ALWAYS)
print(f"📊 Initializing ChromaDB with {EMBEDDING_MODEL}...")

# Check if model exists in Ollama (trust ollama list, skip API test)
embedding_model_to_use = EMBEDDING_MODEL
print(f"   🔍 Checking embedding model availability...")

try:
    tags_response = requests.get(f"{ollama_base_url}/api/tags", timeout=10)
    if tags_response.status_code == 200:
        available_models = [m.get('name', '') for m in tags_response.json().get('models', [])]
        print(f"   📋 Available models: {available_models}")
        
        # Check if our embedding model is in the list
        model_base = EMBEDDING_MODEL.split(':')[0]
        matching_models = [m for m in available_models if model_base in m]
        
        if matching_models:
            # Use the exact name from ollama list
            embedding_model_to_use = matching_models[0]
            print(f"   ✅ Found embedding model: {embedding_model_to_use}")
        else:
            print(f"   ⚠️ Model '{EMBEDDING_MODEL}' not found in Ollama!")
            print(f"   💡 Run: ollama pull mxbai-embed-large")
            print(f"   📋 Available: {available_models}")
    else:
        print(f"   ⚠️ Could not list models, using default: {EMBEDDING_MODEL}")
except Exception as e:
    print(f"   ⚠️ Ollama check error: {e}")
    print(f"   📌 Using default: {EMBEDDING_MODEL}")

print(f"   📌 Using embedding model: {embedding_model_to_use}")

embeddings = OllamaEmbeddings(
    model=embedding_model_to_use,
    base_url=ollama_base_url
)

# Check if existing ChromaDB needs to be reset
chroma_needs_reset = False
if os.path.exists(CHROMA_DB):
    try:
        # Try to load existing collection
        test_store = Chroma(
            collection_name="validated_graphrag",
            persist_directory=CHROMA_DB,
            embedding_function=embeddings
        )
        # Test with a simple query
        test_store.similarity_search("test", k=1)
        print(f"   ✅ Existing ChromaDB loaded successfully")
    except Exception as e:
        error_str = str(e).lower()
        if "not found" in error_str or "model" in error_str or "404" in error_str:
            print(f"   ⚠️ ChromaDB embedding error: {e}")
            print(f"   🔄 Resetting database...")
            chroma_needs_reset = True
        else:
            print(f"   ⚠️ ChromaDB check warning: {e}")

if chroma_needs_reset:
    import shutil
    print(f"   🗑️ Removing old ChromaDB...")
    shutil.rmtree(CHROMA_DB, ignore_errors=True)
    # Also clear the tracker so files get re-indexed
    indexed_tracker.clear()
    print(f"   ✅ ChromaDB reset. Documents will be re-indexed.")

vector_store = Chroma(
    collection_name="validated_graphrag",
    persist_directory=CHROMA_DB,
    embedding_function=embeddings
)
print("✅ ChromaDB ready")

# 5. Scan data_store on startup
print("\n📂 Checking data_store for new documents...")
scan_and_index_data_store(neo4j_graph, vector_store, entity_extractor, indexed_tracker)

# 6. Initialize Guardrails
print("\n🛡️ Initializing Security Guardrails...")
guardrails = get_guardrails_handler()

print("\n" + "="*60)
print("✅ System Ready!")
if not ENABLE_KNOWLEDGE_GRAPH:
    print("   💡 To enable Knowledge Graph, set ENABLE_KNOWLEDGE_GRAPH=True in config.py")
print("="*60 + "\n")


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def home():
    """Serve the main chat interface"""
    return render_template('graphrag_index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Upload file to data_store and index it (skip if already indexed)"""
    try:
        file = request.files['file']
        filename = secure_filename(file.filename)
        force_reindex = request.form.get('force_reindex', 'false').lower() == 'true'
        
        # Import helper function
        from document_processor import is_document_in_chroma
        
        # Check if already in ChromaDB (unless force reindex)
        if not force_reindex and is_document_in_chroma(filename, vector_store):
            return jsonify({
                'success': False,
                'skipped': True,
                'message': f"'{filename}' is already indexed. Use force_reindex=true to re-index.",
                'filename': filename
            })
        
        # Save to data_store (persistent)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        print(f"📁 Saved: {filepath}")
        
        # Extract and process
        text = extract_text_from_file(filepath)
        
        if not text.strip():
            return jsonify({'error': 'Could not extract text from file'}), 400
        
        print(f"📄 Extracted {len(text)} characters from {filename}")
        
        # Process document (with force_reindex option)
        try:
            result = process_document(
                text, filename, filepath,
                neo4j_graph, vector_store, entity_extractor,
                force_reindex=force_reindex
            )
        except Exception as proc_error:
            print(f"⚠️ Processing error: {proc_error}")
            return jsonify({
                'success': False,
                'error': f'Error processing document: {str(proc_error)}',
                'filename': filename,
                'hint': 'The file may be too large or contain unsupported content.'
            }), 500
        
        # Check if it was skipped
        if result.get('skipped'):
            return jsonify({
                'success': False,
                'skipped': True,
                'message': f"'{filename}' was skipped: {result.get('reason', 'already indexed')}",
                'filename': filename
            })
        
        # Mark as indexed
        indexed_tracker.mark_indexed(filepath, result)
        
        return jsonify({
            'success': True,
            'skipped': False,
            'filename': filename,
            'saved_to': filepath,
            **result
        })
    
    except Exception as e:
        print(f"Upload error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/ask', methods=['POST'])
def ask():
    """
    Main Q&A endpoint.
    - Checks input with guardrails
    - Searches ALL documents in data_store
    - Asks permission before using general knowledge
    - Checks output with guardrails
    """
    try:
        data = request.json
        question = data.get('question', '').strip()
        use_general_knowledge = data.get('use_general_knowledge', False)

        if not question:
            return jsonify({'error': 'Please enter a question'}), 400

        # =====================================================================
        # GUARDRAILS: Check input security
        # =====================================================================
        is_safe, security_message = check_input_security(question)
        
        if not is_safe:
            return jsonify({
                'answer': f"🛡️ **Security Notice**\n\n{security_message}",
                'needs_permission': False,
                'used_general_knowledge': False,
                'blocked_by_guardrails': True,
                'sources': [],
                'graph_stats': {
                    'entities_found': 0,
                    'documents_found': 0
                }
            })

        # Search all data_store documents
        vector_hits, graph_hits = hybrid_search(
            question, vector_store, neo4j_graph, top_k=8
        )
        
        context = build_context(vector_hits, graph_hits)
        has_context = bool(vector_hits or graph_hits)
        
        # Debug logging
        print(f"\n🔍 Query: {question}")
        print(f"   Vector hits: {len(vector_hits)}")
        print(f"   Graph hits: {len(graph_hits)}")
        if vector_hits:
            print(f"   Top relevance: {vector_hits[0].get('relevance_score', 'N/A')}")
            print(f"   Sources: {[v.get('source') for v in vector_hits[:3]]}")

        # -----------------------------------------------------------------
        # CASE 1: User approved general knowledge
        # -----------------------------------------------------------------
        if use_general_knowledge:
            prompt = GENERAL_KNOWLEDGE_PROMPT.format(input=question)
            response = llm.invoke(prompt)
            answer = response.content if hasattr(response, 'content') else str(response)
            
            # Check output security
            _, _, answer = check_output_security(answer)
            
            return jsonify({
                'answer': GENERAL_KNOWLEDGE_PREFIX + answer,
                'needs_permission': False,
                'used_general_knowledge': True,
                'blocked_by_guardrails': False,
                'sources': [],
                'graph_stats': {
                    'entities_found': len(graph_hits),
                    'documents_found': len(vector_hits)
                }
            })

        # -----------------------------------------------------------------
        # CASE 2: No context found at all - ask permission
        # -----------------------------------------------------------------
        if not has_context:
            return jsonify({
                'answer': NO_CONTEXT_MESSAGE,
                'needs_permission': True,
                'used_general_knowledge': False,
                'blocked_by_guardrails': False,
                'sources': [],
                'graph_stats': {
                    'entities_found': 0,
                    'documents_found': 0
                }
            })

        # -----------------------------------------------------------------
        # CASE 3: Has context - try document-grounded answer
        # -----------------------------------------------------------------
        prompt = DOCUMENT_GROUNDED_PROMPT.format(context=context, input=question)
        response = llm.invoke(prompt)
        answer = response.content if hasattr(response, 'content') else str(response)
        
        # =====================================================================
        # GUARDRAILS: Check output security
        # =====================================================================
        is_output_safe, output_message, sanitized_answer = check_output_security(answer)
        
        if not is_output_safe:
            answer = sanitized_answer
        
        # Check if LLM returned NO_CONTEXT marker
        if '[NO_CONTEXT]' in answer.upper():
            # Only ask for permission if the LLM explicitly couldn't answer
            return jsonify({
                'answer': INSUFFICIENT_CONTEXT_MESSAGE,
                'needs_permission': True,
                'used_general_knowledge': False,
                'blocked_by_guardrails': False,
                'sources': [v.get('source') for v in vector_hits[:3] if v.get('source')],
                'context_preview': context[:500] + "..." if len(context) > 500 else context,
                'graph_stats': {
                    'entities_found': len(graph_hits),
                    'documents_found': len(vector_hits)
                }
            })
        
        # Success - answered from documents
        # Clean up the answer (remove any stray [NO_CONTEXT] markers)
        answer = answer.replace('[NO_CONTEXT]', '').strip()
        
        sources = list(set([v.get('source') for v in vector_hits[:5] if v.get('source')]))
        
        return jsonify({
            'answer': answer,
            'needs_permission': False,
            'used_general_knowledge': False,
            'blocked_by_guardrails': False,
            'sources': sources,
            'graph_stats': {
                'entities_found': len(graph_hits),
                'documents_found': len(vector_hits)
            }
        })

    except Exception as e:
        print(f"/ask error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# =============================================================================
# DEEP RESEARCH ENDPOINT
# =============================================================================

@app.route('/deep-research', methods=['POST'])
def deep_research():
    """
    Perform deep research with web search and document analysis
    """
    try:
        data = request.json
        topic = data.get('topic', '').strip()
        include_web = data.get('include_web', True)
        include_docs = data.get('include_docs', True)
        depth = data.get('depth', 'standard')  # quick, standard, deep
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        print(f"\n🔬 Deep Research Request: {topic}")
        print(f"   Web: {include_web}, Docs: {include_docs}, Depth: {depth}")
        
        # Security check
        is_safe, message = check_input_security(topic)
        if not is_safe:
            return jsonify({
                'error': message,
                'blocked_by_guardrails': True
            }), 400
        
        # Import and initialize researcher
        from deep_research import DeepResearcher, format_research_as_html, format_research_as_markdown
        
        researcher = DeepResearcher(
            llm=llm,
            vector_store=vector_store if include_docs else None,
            neo4j_graph=neo4j_graph if include_docs else None
        )
        
        # Perform research
        findings = researcher.research(
            topic=topic,
            include_web=include_web,
            include_docs=include_docs,
            depth=depth
        )
        
        # Format response
        return jsonify({
            'success': True,
            'query': findings.query,
            'synthesis': findings.synthesis,
            'key_themes': findings.key_themes,
            'gaps': findings.gaps_identified,
            'ideas': findings.novel_ideas,
            'sources': findings.sources[:15],
            'web_results_count': len(findings.web_results),
            'has_document_context': bool(findings.document_context),
            'html': format_research_as_html(findings),
            'markdown': format_research_as_markdown(findings),
            'timestamp': findings.timestamp
        })
    
    except ImportError as e:
        return jsonify({
            'error': f'Deep research dependencies not installed: {str(e)}',
            'hint': 'Run: pip install duckduckgo-search beautifulsoup4 requests'
        }), 500
    
    except Exception as e:
        print(f"/deep-research error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/generate-ideas', methods=['POST'])
def generate_ideas():
    """
    Generate novel ideas based on a topic
    """
    try:
        data = request.json
        topic = data.get('topic', '').strip()
        context = data.get('context', '')
        num_ideas = min(data.get('num_ideas', 5), 10)  # Max 10 ideas
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        # Security check
        is_safe, message = check_input_security(topic)
        if not is_safe:
            return jsonify({'error': message, 'blocked_by_guardrails': True}), 400
        
        from deep_research import DeepResearcher
        
        researcher = DeepResearcher(llm=llm, vector_store=vector_store)
        ideas = researcher.generate_ideas(topic, context, num_ideas)
        
        return jsonify({
            'success': True,
            'topic': topic,
            'ideas': ideas,
            'count': len(ideas)
        })
    
    except Exception as e:
        print(f"/generate-ideas error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/web-search', methods=['POST'])
def web_search_only():
    """
    Perform web search only (no synthesis)
    """
    try:
        data = request.json
        query = data.get('query', '').strip()
        max_results = min(data.get('max_results', 10), 20)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        from deep_research import WebSearcher
        
        searcher = WebSearcher()
        
        if not searcher.available:
            return jsonify({
                'error': 'Web search not available',
                'hint': 'Install with: pip install duckduckgo-search'
            }), 500
        
        results = searcher.search(query, max_results)
        
        return jsonify({
            'success': True,
            'query': query,
            'results': [
                {
                    'title': r.title,
                    'url': r.url,
                    'snippet': r.snippet,
                    'source': r.source
                }
                for r in results
            ],
            'count': len(results)
        })
    
    except Exception as e:
        print(f"/web-search error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/graph-stats', methods=['GET'])
def graph_stats():
    """Get graph and document statistics"""
    if neo4j_graph:
        stats = neo4j_graph.get_statistics()
    else:
        stats = {
            'total_entities': 0,
            'total_relationships': 0,
            'knowledge_graph_enabled': False
        }
    
    stats['total_documents'] = len(indexed_tracker.get_all_indexed())
    stats['knowledge_graph_enabled'] = neo4j_graph is not None
    return jsonify(stats)


@app.route('/data-store-files', methods=['GET'])
def list_data_store_files():
    """List all indexed files in data_store"""
    files = []
    for filepath in indexed_tracker.get_all_indexed():
        if os.path.exists(filepath):
            info = indexed_tracker.get_file_stats(filepath)
            files.append({
                'path': filepath,
                'filename': os.path.basename(filepath),
                'indexed_at': info.get('indexed_at'),
                'stats': info.get('stats', {})
            })
    return jsonify({'files': files, 'total': len(files)})


@app.route('/entity-resolution-stats', methods=['GET'])
def entity_resolution_stats():
    """Get entity resolution statistics"""
    if entity_resolver:
        total_aliases = len(entity_resolver.entity_aliases)
        canonical_count = len(entity_resolver.canonical_entities)
        
        return jsonify({
            'enabled': True,
            'total_aliases': total_aliases,
            'canonical_entities': canonical_count,
            'resolution_rate': f"{(canonical_count/total_aliases*100) if total_aliases > 0 else 0:.1f}%"
        })
    else:
        return jsonify({
            'enabled': False,
            'message': 'Entity resolution is disabled (Knowledge Graph not enabled)'
        })


@app.route('/reindex', methods=['POST'])
def reindex_data_store():
    """Force re-index all files in data_store"""
    try:
        indexed_tracker.clear()
        files_indexed = scan_and_index_data_store(
            neo4j_graph, vector_store, entity_extractor, indexed_tracker
        )
        return jsonify({
            'success': True,
            'files_indexed': files_indexed
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/chroma-status', methods=['GET'])
def chroma_status():
    """Get ChromaDB collection status and indexed documents"""
    try:
        from document_processor import get_indexed_sources_from_chroma
        
        sources = get_indexed_sources_from_chroma(vector_store)
        
        # Get collection count
        collection = vector_store._collection
        total_chunks = collection.count()
        
        return jsonify({
            'total_documents': len(sources),
            'total_chunks': total_chunks,
            'documents': sorted(list(sources)),
            'collection_name': 'validated_graphrag'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/delete-document', methods=['POST'])
def delete_document():
    """Delete a document from ChromaDB and file tracker"""
    try:
        data = request.json
        filename = data.get('filename', '').strip()
        delete_file = data.get('delete_file', False)  # Also delete from data_store?
        
        if not filename:
            return jsonify({'error': 'Filename required'}), 400
        
        from document_processor import delete_document_from_chroma
        
        # Delete from ChromaDB
        chunks_deleted = delete_document_from_chroma(filename, vector_store)
        
        # Remove from file tracker
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        indexed_tracker.remove(filepath)
        
        # Optionally delete file from data_store
        file_deleted = False
        if delete_file and os.path.exists(filepath):
            os.remove(filepath)
            file_deleted = True
        
        return jsonify({
            'success': True,
            'filename': filename,
            'chunks_deleted': chunks_deleted,
            'removed_from_tracker': True,
            'file_deleted': file_deleted
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/check-indexed', methods=['POST'])
def check_indexed():
    """Check if a specific file is already indexed"""
    try:
        data = request.json
        filename = data.get('filename', '').strip()
        
        if not filename:
            return jsonify({'error': 'Filename required'}), 400
        
        from document_processor import is_document_in_chroma
        
        in_chroma = is_document_in_chroma(filename, vector_store)
        
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        in_tracker = indexed_tracker.is_indexed(filepath)
        
        return jsonify({
            'filename': filename,
            'in_chroma': in_chroma,
            'in_tracker': in_tracker,
            'is_indexed': in_chroma or in_tracker
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/clear', methods=['POST'])
def clear_chat():
    """Clear chat history (placeholder - history managed by frontend)"""
    return jsonify({'success': True})


@app.route('/debug-search', methods=['POST'])
def debug_search():
    """
    Debug endpoint to test search results directly.
    Useful for troubleshooting why answers aren't being found.
    """
    try:
        data = request.json
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Query required'}), 400
        
        # Perform search
        vector_hits, graph_hits = hybrid_search(query, vector_store, neo4j_graph, top_k=8)
        
        # Build context
        context = build_context(vector_hits, graph_hits)
        
        return jsonify({
            'query': query,
            'vector_results': [
                {
                    'source': v.get('source'),
                    'relevance_score': v.get('relevance_score'),
                    'text_preview': v.get('text', '')[:300] + '...' if len(v.get('text', '')) > 300 else v.get('text', ''),
                    'chunk_index': v.get('chunk_index')
                }
                for v in vector_hits
            ],
            'graph_results': graph_hits,
            'context_length': len(context),
            'context_preview': context[:1000] + '...' if len(context) > 1000 else context,
            'has_results': bool(vector_hits or graph_hits)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/security-check', methods=['POST'])
def security_check():
    """
    Test endpoint to check if input passes security guardrails.
    Useful for debugging and testing.
    """
    try:
        data = request.json
        text = data.get('text', '').strip()
        check_type = data.get('type', 'input')  # 'input' or 'output'
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        handler = get_guardrails_handler()
        
        if check_type == 'input':
            result = handler.check_input(text)
        else:
            result = handler.check_output(text)
        
        return jsonify({
            'level': result.level.value,
            'message': result.message,
            'detected_issues': result.detected_issues,
            'is_safe': result.level == SecurityLevel.SAFE
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/security-stats', methods=['GET'])
def security_stats():
    """Get security guardrails information"""
    handler = get_guardrails_handler()
    
    return jsonify({
        'guardrails_enabled': True,
        'nemo_available': handler.nemo_available,
        'checks': {
            'input': [
                'prompt_injection',
                'jailbreak_detection',
                'malicious_code_request',
                'toxicity',
                'pii_extraction_request'
            ],
            'output': [
                'pii_redaction',
                'unsafe_content',
                'instruction_leakage'
            ]
        }
    })


@app.route('/config-status', methods=['GET'])
def config_status():
    """Get current configuration status"""
    return jsonify({
        'knowledge_graph_enabled': runtime_config.knowledge_graph_enabled,
        'entity_extraction_enabled': runtime_config.entity_extraction_enabled,
        'neo4j_connected': runtime_config.neo4j_connected,
        'entity_extractor_ready': runtime_config.entity_extractor_ready,
        'vector_store': 'ChromaDB',
        'llm_model': LLM_MODEL,
        'embedding_model': EMBEDDING_MODEL,
        'mode': 'Full (Vector + KG)' if runtime_config.knowledge_graph_enabled else 'Fast (Vector Only)'
    })


@app.route('/config/enable-kg', methods=['POST'])
def enable_knowledge_graph():
    """Enable Knowledge Graph at runtime"""
    global neo4j_graph, entity_resolver, entity_extractor
    
    try:
        # Check if already enabled
        if runtime_config.knowledge_graph_enabled and neo4j_graph:
            return jsonify({
                'success': True,
                'message': 'Knowledge Graph is already enabled',
                'status': runtime_config.to_dict()
            })
        
        # Initialize Neo4j if not already
        if neo4j_graph is None:
            print("🕸️  Initializing Neo4j (Knowledge Graph enabled by user)...")
            try:
                from entity_resolver import EntityResolver
                from neo4j_graph import ValidatedNeo4jGraph
                
                entity_resolver = EntityResolver()
                neo4j_graph = ValidatedNeo4jGraph(entity_resolver)
                runtime_config.neo4j_connected = True
                print("✅ Neo4j connected")
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Failed to connect to Neo4j: {str(e)}',
                    'hint': 'Make sure Neo4j is running: docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest'
                }), 500
        
        # Initialize entity extractor if not already
        if entity_extractor is None:
            print("🔍 Initializing Entity Extractor...")
            try:
                from entity_extractor import ValidatedEntityExtractor
                entity_extractor = ValidatedEntityExtractor(llm)
                runtime_config.entity_extractor_ready = True
                print("✅ Entity Extractor ready")
            except Exception as e:
                print(f"⚠️ Entity Extractor failed: {e}")
        
        # Update runtime config
        runtime_config.knowledge_graph_enabled = True
        runtime_config.entity_extraction_enabled = True
        
        return jsonify({
            'success': True,
            'message': 'Knowledge Graph enabled successfully',
            'status': runtime_config.to_dict(),
            'note': 'New documents will now be indexed with entity extraction. Existing documents need to be re-indexed to add to KG.'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/config/disable-kg', methods=['POST'])
def disable_knowledge_graph():
    """Disable Knowledge Graph at runtime (keeps Neo4j data, just stops using it)"""
    
    runtime_config.knowledge_graph_enabled = False
    runtime_config.entity_extraction_enabled = False
    
    return jsonify({
        'success': True,
        'message': 'Knowledge Graph disabled. Vector search only mode active.',
        'status': runtime_config.to_dict(),
        'note': 'Neo4j data is preserved. You can re-enable KG anytime.'
    })


@app.route('/config/toggle-kg', methods=['POST'])
def toggle_knowledge_graph():
    """Toggle Knowledge Graph on/off"""
    if runtime_config.knowledge_graph_enabled:
        return disable_knowledge_graph()
    else:
        return enable_knowledge_graph()


@app.route('/config/reindex-with-kg', methods=['POST'])
def reindex_with_kg():
    """Re-index all documents with Knowledge Graph enabled"""
    global neo4j_graph, entity_extractor
    
    if not runtime_config.knowledge_graph_enabled:
        return jsonify({
            'success': False,
            'error': 'Knowledge Graph is not enabled. Enable it first with /config/enable-kg'
        }), 400
    
    if not neo4j_graph:
        return jsonify({
            'success': False,
            'error': 'Neo4j is not connected'
        }), 500
    
    try:
        # Clear tracker to force re-index
        indexed_tracker.clear()
        
        # Re-scan with entity extraction
        files_indexed = scan_and_index_data_store(
            neo4j_graph, vector_store, entity_extractor, indexed_tracker
        )
        
        return jsonify({
            'success': True,
            'files_indexed': files_indexed,
            'message': f'Re-indexed {files_indexed} files with Knowledge Graph extraction'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# SEARCH PARAMETERS API
# =============================================================================

@app.route('/config/search-params', methods=['GET'])
def get_search_params():
    """Get current search parameters"""
    return jsonify({
        'success': True,
        'params': runtime_config.search_params
    })


@app.route('/config/search-params', methods=['POST'])
def update_search_params():
    """Update search parameters"""
    try:
        data = request.json
        
        # Validate and update parameters
        if 'top_k' in data:
            top_k = int(data['top_k'])
            if 1 <= top_k <= 20:
                runtime_config.search_params['top_k'] = top_k
        
        if 'min_relevance' in data:
            min_rel = float(data['min_relevance'])
            if 0.0 <= min_rel <= 1.0:
                runtime_config.search_params['min_relevance'] = min_rel
        
        if 'search_mode' in data:
            mode = data['search_mode']
            if mode in ['vector', 'graph', 'hybrid']:
                runtime_config.search_params['search_mode'] = mode
        
        if 'context_window' in data:
            ctx = int(data['context_window'])
            if 1000 <= ctx <= 10000:
                runtime_config.search_params['context_window'] = ctx
        
        if 'use_reranking' in data:
            runtime_config.search_params['use_reranking'] = bool(data['use_reranking'])
        
        return jsonify({
            'success': True,
            'message': 'Search parameters updated',
            'params': runtime_config.search_params
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


# =============================================================================
# GUARDRAILS CONFIG API
# =============================================================================

@app.route('/config/guardrails', methods=['GET'])
def get_guardrails_config():
    """Get current guardrails configuration"""
    return jsonify({
        'success': True,
        'enabled': runtime_config.guardrails_enabled,
        'config': runtime_config.guardrails_config
    })


@app.route('/config/guardrails', methods=['POST'])
def update_guardrails_config():
    """Update guardrails configuration"""
    try:
        data = request.json
        
        # Update master switch
        if 'enabled' in data:
            runtime_config.guardrails_enabled = bool(data['enabled'])
        
        # Update individual settings
        config_keys = ['block_injection', 'block_jailbreak', 'pii_redaction', 
                       'content_filtering', 'log_blocked', 'strict_mode']
        
        for key in config_keys:
            if key in data:
                runtime_config.guardrails_config[key] = bool(data[key])
        
        return jsonify({
            'success': True,
            'message': 'Guardrails configuration updated',
            'enabled': runtime_config.guardrails_enabled,
            'config': runtime_config.guardrails_config
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


# =============================================================================
# FULL CONFIG STATUS (updated)
# =============================================================================

@app.route('/config-status', methods=['GET'])
def full_config_status():
    """Get complete configuration status"""
    return jsonify({
        'app_name': 'AI-Assistant-SelfTutoring',
        'version': '2.0.0',
        'mode': 'Full (Knowledge Graph)' if runtime_config.knowledge_graph_enabled else 'Fast (Vector Only)',
        'knowledge_graph_enabled': runtime_config.knowledge_graph_enabled,
        'entity_extraction_enabled': runtime_config.entity_extraction_enabled,
        'neo4j_connected': runtime_config.neo4j_connected,
        'entity_extractor_ready': runtime_config.entity_extractor_ready,
        'guardrails_enabled': runtime_config.guardrails_enabled,
        'guardrails_config': runtime_config.guardrails_config,
        'search_params': runtime_config.search_params,
        'llm_model': LLM_MODEL,
        'embedding_model': EMBEDDING_MODEL,
        'max_upload_mb': MAX_CONTENT_LENGTH // (1024 * 1024)
    })


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n🚀 Starting AI-Assistant-SelfTutoring v2.0...")
    print("   📄 Document-Grounded Responses")
    if ENABLE_KNOWLEDGE_GRAPH and neo4j_graph:
        print("   🕸️  Knowledge Graph: ENABLED")
    else:
        print("   ⚡ Knowledge Graph: DISABLED (fast mode)")
    print("   💾 Persistent data_store")
    print("   🛡️  Security Guardrails Enabled")
    print(f"   📤 Max Upload: {MAX_CONTENT_LENGTH // (1024 * 1024)} MB")
    print("\n   Open: http://localhost:5000\n")
    
    try:
        app.run(debug=False, host='0.0.0.0', port=5000)
    finally:
        if neo4j_graph:
            neo4j_graph.close()

# 🎓 AI-Assistant-Self Tutoring

A **self-tutoring AI assistant** with document grounding, knowledge graphs, and deep research capabilities. Upload your learning materials and get intelligent, cited answers from your documents.
<img width="929" height="440" alt="image" src="https://github.com/user-attachments/assets/9a3ffef4-962c-441b-90e4-85bd6be3efa4" />

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-orange.svg)

---

## ✨ Key Features

- 📄 **Document-Grounded Answers** - Responses based ONLY on your uploaded documents
- 🔍 **Hybrid RAG Search** - Combines vector similarity + knowledge graph traversal
- 🕸️ **Knowledge Graph** - Builds entity relationships using Neo4j (optional)
- 🔬 **Deep Research** - Web search + document synthesis
- 🤖 **Local LLM** - Uses Ollama (no API keys needed)
- 🛡️ **Security Guardrails** - Configurable content filtering and safety checks
- 💾 **Large File Support** - Up to 50MB per document

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Ollama** - [Download here](https://ollama.com)
- **Neo4j** (optional) - For knowledge graph features
- **Docker** (optional) - For containerized deployment

### Installation

**Linux/macOS:**
```bash
# Clone the repository
git clone <repository-url>
cd graphrag_project

# Make scripts executable
chmod +x startup.sh check_models.sh check_indexing.sh upgrade_llm.sh

# Run the startup script (handles everything automatically)
./startup.sh
```

**Windows:**
```batch
REM Clone the repository
git clone <repository-url>
cd graphrag_project

REM Run the startup script
startup.bat
```

The startup script will:
1. ✅ Check system requirements
2. ✅ Verify Ollama is running
3. ✅ Check/download required models
4. ✅ Install Python dependencies
5. ✅ Start the application

**Access the application at:** http://localhost:5000

---

## 📖 Usage

### Basic Workflow

1. **Start the Application**
   ```bash
   ./startup.sh
   ```

2. **Upload Documents**
   - Go to http://localhost:5000
   - Upload PDFs, DOCX, TXT, or other supported formats
   - Maximum size: 50MB per file

3. **Ask Questions**
   - Type your question in the chat interface
   - Get answers grounded in your documents
   - See source citations for each answer

### Supported File Formats

- 📄 PDF
- 📝 DOCX
- 📃 TXT, MD
- 📊 CSV, JSON
- 🌐 HTML, XML

---

## ⚙️ Configuration

### Operating Modes

**Fast Mode (Default)** - Vector search only, no knowledge graph
```bash
./startup.sh --fast
```

**Full Mode** - With knowledge graph (requires Neo4j)
```bash
./startup.sh --full
```

**Docker Mode** - Containerized deployment
```bash
./startup.sh --docker
```

### Environment Variables

Create a `.env` file (copy from `.env.example`):

```bash
# LLM Configuration
LLM_MODEL=llama3.2:3b                 # Recommended: 3b or 8b variant
EMBEDDING_MODEL=nomic-embed-text      # Most reliable option

# Ollama Connection
OLLAMA_HOST=http://localhost:11434

# Optional: Neo4j (for knowledge graph)
# ENABLE_KNOWLEDGE_GRAPH=true
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=your-password
```

### Model Recommendations

| Model | Size | RAM Required | Best For | Performance |
|-------|------|--------------|----------|-------------|
| `llama3.2:3b` | 2GB | 4GB+ | Balanced use | ⭐⭐⭐⭐ Recommended |
| `llama3:8b` | 5GB | 8GB+ | High accuracy | ⭐⭐⭐⭐⭐ Best quality |
| `qwen2.5:7b` | 4GB | 8GB+ | Technical docs | ⭐⭐⭐⭐⭐ |
| `phi3:3.8b` | 2.3GB | 4GB+ | Low resources | ⭐⭐⭐ |

**Upgrade your LLM:**
```bash
./upgrade_llm.sh
```

### Embedding Models

| Model | Size | Speed | Reliability |
|-------|------|-------|-------------|
| `nomic-embed-text` | 700MB | Fast | ✅ Most reliable |
| `all-minilm` | 80MB | Very Fast | ✅ Very reliable |
| `mxbai-embed-large` | 1.5GB | Slower | ⚠️ May have detection issues |

---

## 🛠️ Utility Scripts

### check_models.sh
Verify Ollama models are installed and working:
```bash
./check_models.sh          # Check models
./check_models.sh --pull   # Auto-pull missing models
```

### check_indexing.sh
Diagnose document indexing issues:
```bash
./check_indexing.sh
```

Shows:
- Documents in `data_store/`
- ChromaDB indexing status
- Test search results
- Current configuration

### upgrade_llm.sh
Upgrade to a better LLM model:
```bash
./upgrade_llm.sh
```

Features:
- Auto-detects system RAM
- Recommends best model for your system
- Downloads and configures automatically

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Model Not Found After Pulling

**Problem:** Ran `ollama pull <model>` but model still shows 404 errors

**Solution:**
```bash
# Restart Ollama service
pkill ollama && ollama serve &

# Verify model appears
ollama list
```

#### 2. Documents Not Found in Search

**Problem:** Documents are indexed but queries return "Not found in your documents"

**Cause:** LLM model is too weak (e.g., llama3.2:1b)

**Solution:**
```bash
# Upgrade to 3b or 8b variant
./upgrade_llm.sh
```

#### 3. ChromaDB Reset After Model Change

**Problem:** Changing embedding models wipes the database

**Solution:**
```bash
# Stick with one embedding model, or re-index
./startup.sh
# Wait for documents to re-index automatically
```

For detailed troubleshooting, see [TROUBLESHOOTING_INDEXING.md](TROUBLESHOOTING_INDEXING.md).

---

## 🐳 Docker Deployment

### Quick Start

```bash
# Fast Mode (uses host Ollama)
docker-compose up -d graphrag

# Full Mode (with Neo4j knowledge graph)
docker-compose --profile kg up -d

# With containerized Ollama (GPU)
docker-compose --profile ollama up -d
```

### Environment Configuration

```bash
# Create .env file
cp .env.example .env

# Edit configuration
nano .env
```

---

## 📚 API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ask` | POST | Ask a question |
| `/upload` | POST | Upload document |
| `/deep-research` | POST | Web research + synthesis |
| `/config-status` | GET | Get configuration |

### Diagnostic Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chroma-status` | GET | Index statistics |
| `/debug-search` | POST | Test vector search |
| `/graph-stats` | GET | Knowledge graph stats |
| `/data-store-files` | GET | List indexed files |

### Example: Ask Question

```bash
curl -X POST http://localhost:5000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the security best practices?",
    "mode": "hybrid"
  }'
```

### Example: Upload Document

```bash
curl -X POST http://localhost:5000/upload \
  -F "file=@document.pdf"
```

---

## 📁 Project Structure

```
graphrag_project/
├── graphrag_app.py          # Main Flask application
├── config.py                # Configuration with auto-detection
├── search.py                # Hybrid RAG search
├── document_processor.py    # Document parsing & chunking
├── deep_research.py         # Web research functionality
├── guardrails_handler.py    # Security guardrails
│
├── entity_extractor.py      # LLM-based entity extraction
├── entity_resolver.py       # Entity deduplication
├── neo4j_graph.py           # Knowledge graph operations
├── ontology.py              # Entity schemas
│
├── startup.sh               # Linux/macOS startup script
├── startup.bat              # Windows startup script
├── check_models.sh          # Model verification
├── check_indexing.sh        # Indexing diagnostics
├── upgrade_llm.sh           # LLM upgrade helper
│
├── Dockerfile               # Container build
├── docker-compose.yml       # Multi-service orchestration
├── docker-entrypoint.sh     # Container startup
│
├── templates/               # Web UI templates
├── guardrails/              # Guardrails configuration
│
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
└── README.md                # This file
```

---

## 🔄 Advanced Features

### Knowledge Graph Mode

Enable entity extraction and relationship mapping:

```bash
# Start with knowledge graph
./startup.sh --full

# Or enable via API
curl -X POST http://localhost:5000/config/enable-kg
```

### Deep Research

Perform web-based research with document synthesis:

```bash
curl -X POST http://localhost:5000/deep-research \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Machine learning best practices",
    "include_web": true,
    "include_docs": true,
    "depth": "standard"
  }'
```

**Depth Levels:**
- `quick` - ~5 sources, 30 seconds
- `standard` - ~15 sources, 1 minute
- `deep` - ~25+ sources, 2 minutes

### Configurable Search Parameters

```bash
curl -X POST http://localhost:5000/config/search-params \
  -H "Content-Type: application/json" \
  -d '{
    "top_k": 8,
    "min_relevance": 0.4,
    "search_mode": "hybrid",
    "context_window": 8000
  }'
```

---

## 📝 Model Variant Auto-Detection

The application automatically detects model variants installed in Ollama:

- ✅ `.env` specifies `LLM_MODEL=llama3.2`
- ✅ You have `llama3.2:3b` installed
- ✅ App auto-detects and uses `llama3.2:3b`

**Console Output:**
```
🤖 Initializing LLM (llama3.2)...
ℹ️  Auto-detected model variant: llama3.2:3b (configured: llama3.2)
✅ LLM ready
```

**No configuration needed** - it just works!

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

MIT License - See LICENSE file for details.

---

## 🙏 Acknowledgments

Built with:
- [Ollama](https://ollama.com) - Local LLM runtime
- [LangChain](https://langchain.com) - LLM orchestration
- [ChromaDB](https://www.trychroma.com) - Vector database
- [Neo4j](https://neo4j.com) - Graph database
- [Flask](https://flask.palletsprojects.com) - Web framework

---

**Built with ❤️ for self-directed learners**

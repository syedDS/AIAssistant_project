#!/bin/bash
# =============================================================================
# AI-Assistant-SelfTutoring - Startup Script (Linux/macOS)
# =============================================================================
# 
# Usage:
#   ./startup.sh              - Start with defaults
#   ./startup.sh --full       - Start with Knowledge Graph enabled
#   ./startup.sh --ollama     - Start Ollama first, then app
#   ./startup.sh --docker     - Start using Docker Compose
#   ./startup.sh --help       - Show help
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Application info
APP_NAME="AI-Assistant-SelfTutoring"
VERSION="2.0.0"

# Print banner
print_banner() {
    echo -e "${PURPLE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║     🎓 AI-Assistant-SelfTutoring v${VERSION}                    ║"
    echo "║     Self-tutoring AI with Knowledge Graphs & Deep Research    ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Print help
print_help() {
    echo "Usage: ./startup.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --fast          Start in Fast Mode (vector search only) [default]"
    echo "  --full          Start with Knowledge Graph enabled (requires Neo4j)"
    echo "  --ollama        Start Ollama service first, then the application"
    echo "  --docker        Start using Docker Compose"
    echo "  --docker-full   Start Docker with Knowledge Graph (Neo4j)"
    echo "  --install       Install dependencies only"
    echo "  --check         Check system requirements"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./startup.sh                 # Start with defaults"
    echo "  ./startup.sh --full          # Enable Knowledge Graph"
    echo "  ./startup.sh --docker        # Use Docker"
    echo ""
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verify model is actually loaded in Ollama
verify_model_loaded() {
    local model_name=$1
    local max_wait=${2:-10}  # Default 10 seconds
    local elapsed=0

    echo -e "${CYAN}🔍 Verifying model is loaded in Ollama...${NC}"

    while [ $elapsed -lt $max_wait ]; do
        # Extract base model name for checking
        local base_model=$(echo "$model_name" | cut -d':' -f1)
        if curl -s http://localhost:11434/api/tags 2>/dev/null | grep -q "\"name\":\"${base_model}"; then
            local found_model=$(curl -s http://localhost:11434/api/tags | grep -o "\"name\":\"${base_model}[^\"]*\"" | head -1 | cut -d'"' -f4)
            echo -e "${GREEN}✅ Model '${found_model}' is loaded and ready${NC}"
            return 0
        fi

        if [ $elapsed -eq 0 ]; then
            echo -e "${YELLOW}   Waiting for model to appear in Ollama...${NC}"
        fi

        sleep 2
        elapsed=$((elapsed + 2))
    done

    return 1
}

# Prompt user to select embedding model
select_embedding_model() {
    echo ""
    echo -e "${CYAN}📊 Select an embedding model:${NC}"
    echo ""
    echo "  1) mxbai-embed-large (default, 334M params, best quality, ~1.5GB)"
    echo "  2) nomic-embed-text (137M params, faster, good quality, ~700MB)"
    echo "  3) all-minilm (22M params, very fast, smallest, ~80MB)"
    echo "  4) Enter custom model name"
    echo "  5) Skip (continue without pulling)"
    echo ""

    while true; do
        read -p "Enter your choice [1-5]: " choice
        case $choice in
            1)
                SELECTED_EMBEDDING_MODEL="mxbai-embed-large"
                break
                ;;
            2)
                SELECTED_EMBEDDING_MODEL="nomic-embed-text"
                break
                ;;
            3)
                SELECTED_EMBEDDING_MODEL="all-minilm"
                break
                ;;
            4)
                read -p "Enter custom model name: " custom_model
                if [ -n "$custom_model" ]; then
                    SELECTED_EMBEDDING_MODEL="$custom_model"
                    break
                else
                    echo -e "${RED}Model name cannot be empty${NC}"
                fi
                ;;
            5)
                echo -e "${YELLOW}Skipping model selection.${NC}"
                return 0
                ;;
            *)
                echo -e "${RED}Invalid choice. Please enter 1-5${NC}"
                ;;
        esac
    done

    echo -e "${GREEN}Selected model: ${SELECTED_EMBEDDING_MODEL}${NC}"

    # Ask if user wants to pull the model now
    echo ""
    read -p "Would you like to pull this model now? [Y/n]: " pull_choice
    case $pull_choice in
        [Nn]*)
            echo -e "${YELLOW}Skipping model pull. Make sure to pull it manually later.${NC}"
            ;;
        *)
            echo -e "${CYAN}📥 Pulling ${SELECTED_EMBEDDING_MODEL}...${NC}"
            if ollama pull "$SELECTED_EMBEDDING_MODEL"; then
                echo -e "${GREEN}✅ Model pulled successfully!${NC}"
                echo ""

                # Verify model appears in Ollama
                if ! verify_model_loaded "$SELECTED_EMBEDDING_MODEL" 10; then
                    echo -e "${YELLOW}⚠️  Model pulled but not yet showing in Ollama${NC}"
                    echo ""
                    echo -e "${CYAN}Troubleshooting steps:${NC}"
                    echo -e "1. Check if model is in the list: ${CYAN}ollama list${NC}"
                    echo -e "2. Try restarting Ollama:"
                    echo -e "   ${CYAN}pkill ollama && ollama serve &${NC}  (Linux/macOS)"
                    echo -e "   Or restart the Ollama service (Windows)"
                    echo -e "3. Try pulling with a specific tag: ${CYAN}ollama pull ${SELECTED_EMBEDDING_MODEL}:latest${NC}"
                    echo ""

                    read -p "Would you like to see all available models now? [Y/n]: " show_models
                    case $show_models in
                        [Nn]*) ;;
                        *)
                            echo ""
                            ollama list
                            echo ""
                            ;;
                    esac
                fi
            else
                echo -e "${RED}❌ Failed to pull model.${NC}"
                echo ""
                echo -e "${YELLOW}This could happen if:${NC}"
                echo -e "  - Model name is incorrect"
                echo -e "  - Network connection issues"
                echo -e "  - Ollama service is not running properly"
                echo ""
                echo -e "Try manually: ${CYAN}ollama pull ${SELECTED_EMBEDDING_MODEL}${NC}"
                return 1
            fi
            ;;
    esac

    # Update .env file
    if [ -f .env ]; then
        if grep -q "^EMBEDDING_MODEL=" .env; then
            # Replace existing line
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s/^EMBEDDING_MODEL=.*/EMBEDDING_MODEL=${SELECTED_EMBEDDING_MODEL}/" .env
            else
                sed -i "s/^EMBEDDING_MODEL=.*/EMBEDDING_MODEL=${SELECTED_EMBEDDING_MODEL}/" .env
            fi
            echo -e "${GREEN}✅ Updated EMBEDDING_MODEL in .env${NC}"
        else
            # Append to file
            echo "EMBEDDING_MODEL=${SELECTED_EMBEDDING_MODEL}" >> .env
            echo -e "${GREEN}✅ Added EMBEDDING_MODEL to .env${NC}"
        fi
    else
        # Create new .env from .env.example
        if [ -f .env.example ]; then
            cp .env.example .env
            if grep -q "^EMBEDDING_MODEL=" .env; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s/^EMBEDDING_MODEL=.*/EMBEDDING_MODEL=${SELECTED_EMBEDDING_MODEL}/" .env
                else
                    sed -i "s/^EMBEDDING_MODEL=.*/EMBEDDING_MODEL=${SELECTED_EMBEDDING_MODEL}/" .env
                fi
            else
                echo "EMBEDDING_MODEL=${SELECTED_EMBEDDING_MODEL}" >> .env
            fi
            echo -e "${GREEN}✅ Created .env with EMBEDDING_MODEL=${SELECTED_EMBEDDING_MODEL}${NC}"
        else
            echo "EMBEDDING_MODEL=${SELECTED_EMBEDDING_MODEL}" > .env
            echo -e "${GREEN}✅ Created .env with EMBEDDING_MODEL=${SELECTED_EMBEDDING_MODEL}${NC}"
        fi
    fi

    export EMBEDDING_MODEL="$SELECTED_EMBEDDING_MODEL"
}

# Check system requirements
check_requirements() {
    echo -e "${CYAN}🔍 Checking system requirements...${NC}"
    echo ""
    
    local all_good=true
    
    # Python
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        echo -e "  ${GREEN}✅ Python: $PYTHON_VERSION${NC}"
    else
        echo -e "  ${RED}❌ Python 3 not found${NC}"
        all_good=false
    fi
    
    # pip
    if command_exists pip3 || command_exists pip; then
        echo -e "  ${GREEN}✅ pip installed${NC}"
    else
        echo -e "  ${RED}❌ pip not found${NC}"
        all_good=false
    fi
    
    # Ollama
    if command_exists ollama; then
        echo -e "  ${GREEN}✅ Ollama installed${NC}"
        
        # Check if Ollama is running
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            echo -e "  ${GREEN}✅ Ollama is running${NC}"
            
            # Check for required models
            # Use grep -o to detect llama3.2 with any tag (e.g., llama3.2:1b, llama3.2:3b)
            LLAMA_MODEL=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"llama3\.2[^"]*"' | head -1 | cut -d'"' -f4)
            if [ -n "$LLAMA_MODEL" ]; then
                echo -e "  ${GREEN}✅ Model: ${LLAMA_MODEL}${NC}"
            else
                echo -e "  ${YELLOW}⚠️  Model llama3.2 not found. Run: ollama pull llama3.2:latest${NC}"
            fi

            # Check for embedding model (read from .env if available)
            REQUIRED_EMBED_MODEL="${EMBEDDING_MODEL:-mxbai-embed-large}"
            if [ -f .env ] && grep -q "^EMBEDDING_MODEL=" .env; then
                REQUIRED_EMBED_MODEL=$(grep "^EMBEDDING_MODEL=" .env | cut -d'=' -f2)
            fi

            EMBED_MODEL=$(curl -s http://localhost:11434/api/tags | grep -o "\"name\":\"${REQUIRED_EMBED_MODEL}[^\"]*\"" | head -1 | cut -d'"' -f4)
            if [ -n "$EMBED_MODEL" ]; then
                echo -e "  ${GREEN}✅ Model: ${EMBED_MODEL}${NC}"
            else
                echo -e "  ${YELLOW}⚠️  Model ${REQUIRED_EMBED_MODEL} not found.${NC}"
                echo -e "  ${CYAN}   Tip: Run ./check_models.sh for help with missing models${NC}"
                EMBEDDING_MODEL_MISSING=true
            fi
        else
            echo -e "  ${YELLOW}⚠️  Ollama not running. Start with: ollama serve${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠️  Ollama not installed (optional for Docker)${NC}"
    fi

    # Docker (optional)
    if command_exists docker; then
        echo -e "  ${GREEN}✅ Docker installed${NC}"
    else
        echo -e "  ${YELLOW}ℹ️  Docker not installed (optional)${NC}"
    fi

    # Neo4j (optional)
    if curl -s http://localhost:7474 >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Neo4j is running${NC}"
    else
        echo -e "  ${YELLOW}ℹ️  Neo4j not running (optional for Full Mode)${NC}"
    fi

    echo ""

    # If embedding model is missing and Ollama is running, offer to select one
    if [ "${EMBEDDING_MODEL_MISSING:-false}" = "true" ]; then
        echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}⚠️  Embedding model not found${NC}"
        echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        read -p "Would you like to select/pull an embedding model now? [Y/n]: " select_choice
        case $select_choice in
            [Nn]*)
                echo -e "${YELLOW}Continuing without embedding model. The app may fail to start.${NC}"
                ;;
            *)
                select_embedding_model
                ;;
        esac
        echo ""
    fi

    if $all_good; then
        echo -e "${GREEN}✅ All required dependencies are installed!${NC}"
        return 0
    else
        echo -e "${RED}❌ Some required dependencies are missing.${NC}"
        return 1
    fi
}

# Install dependencies
install_dependencies() {
    echo -e "${CYAN}📦 Installing dependencies...${NC}"
    
    # Check for virtual environment
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    pip install -r requirements.txt
    
    echo -e "${GREEN}✅ Dependencies installed!${NC}"
}

# Start Ollama and pull models
start_ollama() {
    echo -e "${CYAN}🤖 Starting Ollama...${NC}"
    
    if ! command_exists ollama; then
        echo -e "${RED}❌ Ollama not installed. Install from: https://ollama.com${NC}"
        exit 1
    fi
    
    # Start Ollama in background if not running
    if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo -e "${YELLOW}Starting Ollama server...${NC}"
        ollama serve &
        sleep 5
    fi
    
    # Pull required models
    echo -e "${CYAN}📥 Pulling required models...${NC}"
    ollama pull llama3.2:latest
    ollama pull mxbai-embed-large:latest
    
    echo -e "${GREEN}✅ Ollama ready!${NC}"
}

# Start the application
start_app() {
    local mode=$1
    
    echo -e "${CYAN}🚀 Starting ${APP_NAME}...${NC}"
    
    # Activate virtual environment if exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Set environment variables based on mode
    if [ "$mode" == "full" ]; then
        export ENABLE_KNOWLEDGE_GRAPH=true
        export ENABLE_LLM_ENTITY_EXTRACTION=true
        echo -e "${PURPLE}Mode: Full (Knowledge Graph + Entity Extraction)${NC}"
    else
        export ENABLE_KNOWLEDGE_GRAPH=false
        export ENABLE_LLM_ENTITY_EXTRACTION=false
        echo -e "${GREEN}Mode: Fast (Vector Search Only)${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}🌐 Access the application at: ${CYAN}http://localhost:5000${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""
    
    # Start the application
    python graphrag_app.py
}

# Start with Docker
start_docker() {
    local mode=$1
    
    echo -e "${CYAN}🐳 Starting with Docker...${NC}"
    
    if ! command_exists docker; then
        echo -e "${RED}❌ Docker not installed${NC}"
        exit 1
    fi
    
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker Compose not installed${NC}"
        exit 1
    fi
    
    # Determine docker-compose command
    if docker compose version >/dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    if [ "$mode" == "full" ]; then
        echo -e "${PURPLE}Mode: Full (with Neo4j)${NC}"
        ENABLE_KNOWLEDGE_GRAPH=true $COMPOSE_CMD --profile kg up -d
    else
        echo -e "${GREEN}Mode: Fast${NC}"
        $COMPOSE_CMD up -d graphrag
    fi
    
    echo ""
    echo -e "${GREEN}🌐 Access the application at: ${CYAN}http://localhost:5000${NC}"
    echo -e "${YELLOW}View logs: $COMPOSE_CMD logs -f${NC}"
    echo -e "${YELLOW}Stop: $COMPOSE_CMD down${NC}"
}

# Main script
main() {
    print_banner
    
    case "${1:-}" in
        --help|-h)
            print_help
            ;;
        --check)
            check_requirements
            ;;
        --install)
            install_dependencies
            ;;
        --ollama)
            start_ollama
            start_app "fast"
            ;;
        --full)
            check_requirements
            start_app "full"
            ;;
        --docker)
            start_docker "fast"
            ;;
        --docker-full)
            start_docker "full"
            ;;
        --fast|"")
            check_requirements
            start_app "fast"
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            print_help
            exit 1
            ;;
    esac
}

# Run main
main "$@"

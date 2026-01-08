@echo off
REM =============================================================================
REM AI-Assistant-SelfTutoring - Startup Script (Windows)
REM =============================================================================
REM 
REM Usage:
REM   startup.bat              - Start with defaults
REM   startup.bat --full       - Start with Knowledge Graph enabled
REM   startup.bat --ollama     - Start Ollama first, then app
REM   startup.bat --docker     - Start using Docker Compose
REM   startup.bat --help       - Show help
REM
REM =============================================================================

setlocal EnableDelayedExpansion

REM Application info
set APP_NAME=AI-Assistant-SelfTutoring
set VERSION=2.0.0

REM Colors (Windows 10+)
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "CYAN=[96m"
set "PURPLE=[95m"
set "NC=[0m"

REM Print banner
echo.
echo %PURPLE%╔═══════════════════════════════════════════════════════════════╗%NC%
echo %PURPLE%║                                                               ║%NC%
echo %PURPLE%║     🎓 AI-Assistant-SelfTutoring v%VERSION%                    ║%NC%
echo %PURPLE%║     Self-tutoring AI with Knowledge Graphs ^& Deep Research    ║%NC%
echo %PURPLE%║                                                               ║%NC%
echo %PURPLE%╚═══════════════════════════════════════════════════════════════╝%NC%
echo.

REM Parse arguments
if "%1"=="" goto :start_fast
if "%1"=="--help" goto :show_help
if "%1"=="-h" goto :show_help
if "%1"=="--check" goto :check_requirements
if "%1"=="--install" goto :install_deps
if "%1"=="--ollama" goto :start_ollama
if "%1"=="--full" goto :start_full
if "%1"=="--fast" goto :start_fast
if "%1"=="--docker" goto :start_docker
if "%1"=="--docker-full" goto :start_docker_full

echo %RED%Unknown option: %1%NC%
goto :show_help

:show_help
echo Usage: startup.bat [OPTIONS]
echo.
echo Options:
echo   --fast          Start in Fast Mode (vector search only) [default]
echo   --full          Start with Knowledge Graph enabled (requires Neo4j)
echo   --ollama        Start Ollama service first, then the application
echo   --docker        Start using Docker Compose
echo   --docker-full   Start Docker with Knowledge Graph (Neo4j)
echo   --install       Install dependencies only
echo   --check         Check system requirements
echo   --help          Show this help message
echo.
echo Examples:
echo   startup.bat                 # Start with defaults
echo   startup.bat --full          # Enable Knowledge Graph
echo   startup.bat --docker        # Use Docker
echo.
goto :end

:check_requirements
echo %CYAN%🔍 Checking system requirements...%NC%
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
    echo   %GREEN%✅ Python: !PYVER!%NC%
) else (
    echo   %RED%❌ Python not found%NC%
)

REM Check pip
pip --version >nul 2>&1
if %errorlevel%==0 (
    echo   %GREEN%✅ pip installed%NC%
) else (
    echo   %RED%❌ pip not found%NC%
)

REM Check Ollama
ollama --version >nul 2>&1
if %errorlevel%==0 (
    echo   %GREEN%✅ Ollama installed%NC%
    
    REM Check if Ollama is running
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %errorlevel%==0 (
        echo   %GREEN%✅ Ollama is running%NC%
    ) else (
        echo   %YELLOW%⚠️  Ollama not running. Start with: ollama serve%NC%
    )
) else (
    echo   %YELLOW%⚠️  Ollama not installed (optional for Docker)%NC%
)

REM Check Docker
docker --version >nul 2>&1
if %errorlevel%==0 (
    echo   %GREEN%✅ Docker installed%NC%
) else (
    echo   %YELLOW%ℹ️  Docker not installed (optional)%NC%
)

echo.
goto :end

:install_deps
echo %CYAN%📦 Installing dependencies...%NC%

REM Check for virtual environment
if not exist "venv" (
    echo %YELLOW%Creating virtual environment...%NC%
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip
pip install --upgrade pip

REM Install requirements
pip install -r requirements.txt

echo %GREEN%✅ Dependencies installed!%NC%
goto :end

:start_ollama
echo %CYAN%🤖 Starting Ollama...%NC%

REM Check if Ollama is installed
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%❌ Ollama not installed. Install from: https://ollama.com%NC%
    goto :end
)

REM Start Ollama if not running
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo %YELLOW%Starting Ollama server...%NC%
    start "" ollama serve
    timeout /t 5 >nul
)

REM Pull required models
echo %CYAN%📥 Pulling required models...%NC%
ollama pull llama3.2:latest
ollama pull mxbai-embed-large:latest

echo %GREEN%✅ Ollama ready!%NC%
goto :start_fast

:start_fast
echo %CYAN%🚀 Starting %APP_NAME%...%NC%
echo %GREEN%Mode: Fast (Vector Search Only)%NC%
echo.

REM Activate virtual environment if exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Set environment variables
set ENABLE_KNOWLEDGE_GRAPH=false
set ENABLE_LLM_ENTITY_EXTRACTION=false

echo %GREEN%🌐 Access the application at: %CYAN%http://localhost:5000%NC%
echo %YELLOW%Press Ctrl+C to stop%NC%
echo.

python graphrag_app.py
goto :end

:start_full
echo %CYAN%🚀 Starting %APP_NAME%...%NC%
echo %PURPLE%Mode: Full (Knowledge Graph + Entity Extraction)%NC%
echo.

REM Activate virtual environment if exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Set environment variables
set ENABLE_KNOWLEDGE_GRAPH=true
set ENABLE_LLM_ENTITY_EXTRACTION=true

echo %GREEN%🌐 Access the application at: %CYAN%http://localhost:5000%NC%
echo %YELLOW%Press Ctrl+C to stop%NC%
echo.

python graphrag_app.py
goto :end

:start_docker
echo %CYAN%🐳 Starting with Docker...%NC%
echo %GREEN%Mode: Fast%NC%

docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%❌ Docker not installed%NC%
    goto :end
)

docker-compose up -d graphrag

echo.
echo %GREEN%🌐 Access the application at: %CYAN%http://localhost:5000%NC%
echo %YELLOW%View logs: docker-compose logs -f%NC%
echo %YELLOW%Stop: docker-compose down%NC%
goto :end

:start_docker_full
echo %CYAN%🐳 Starting with Docker...%NC%
echo %PURPLE%Mode: Full (with Neo4j)%NC%

docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%❌ Docker not installed%NC%
    goto :end
)

set ENABLE_KNOWLEDGE_GRAPH=true
docker-compose --profile kg up -d

echo.
echo %GREEN%🌐 Access the application at: %CYAN%http://localhost:5000%NC%
echo %YELLOW%View logs: docker-compose logs -f%NC%
echo %YELLOW%Stop: docker-compose down%NC%
goto :end

:end
endlocal

set -e 
chmod -R +x raiseticket/

if ! command -v ollama &> /dev/null; then
    echo "RAISETICKET:: OLLAMA NOT FOUND"
    echo "RAISETICKET:: INSTALLING OLLAMA"
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "RAISETICKET:: OLLAMA ALREADY INSTALLED"
fi

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "RAISETICKET:: STARTING OLLAMA SERVE IN THE BACKGROUND"
    nonup ollama serve > /tmp/ollama.log 2?&1; 
    sleep 3
else 
    echo "RAISETICKET:: OLLAMA IS ALREADY RUNNING"
fi

echo "RAISETICKET:: PULLING EMBEDDING MODEL -- NOMIC EMBED TEXT"
ollama pull nomic-embed-text

echo "RAISETICKET:: PULLING FIX AGENT MODEL --QWEN2.5 CODER:7B"
ollama pull qwen2.5-coder:7b

echo
echo "RAISETICKET:: DONE...VERIFY WITH PYTHON `python3 raiseticket/check_env.py`"

 
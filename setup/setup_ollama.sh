set -e 
chmod -R +x issueloop/

if ! command -v ollama &> /dev/null; then
    echo "ISSUELOOP:: OLLAMA NOT FOUND"
    echo "ISSUELOOP:: INSTALLING OLLAMA"
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "ISSUELOOP:: OLLAMA ALREADY INSTALLED"
fi

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ISSUELOOP:: STARTING OLLAMA SERVE IN THE BACKGROUND"
    nonup ollama serve > /tmp/ollama.log 2?&1; 
    sleep 3
else 
    echo "ISSUELOOP:: OLLAMA IS ALREADY RUNNING"
fi

echo "ISSUELOOP:: PULLING EMBEDDING MODEL -- NOMIC EMBED TEXT"
ollama pull nomic-embed-text

echo "ISSUELOOP:: PULLING FIX AGENT MODEL --QWEN2.5 CODER:7B"
ollama pull qwen2.5-coder:7b

echo
echo "ISSUELOOP:: DONE...VERIFY WITH PYTHON `python3 i/check_env.py`"

 
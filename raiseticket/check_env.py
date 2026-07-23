import shutil
import subprocess
import sys
import requests
OLLAMA_URL="http://localhost:11434"
REQUIRED_MODELS = {
    "nomic-embed-text": "blocking",   
    "qwen2.5-coder:7b": "blocking",   
}

REQUIRED_BY_PACKAGES = ["chromadb", "requests", "yaml", "pathspec"]


def check(label:str, ok:bool, detail:str = "", blocking: bool = True):
    status = "PASS" if ok else ("FAIL" if blocking else "WARN")
    print(f"RAISETICKET:: [{status}] {label}" + (f" -- {detail}" if detail else ""))
    return ok or not blocking


def main():
    all_ok = True
    ollama_path = shutil.which("ollama")
    all_ok &= check("ollama binary on PATH", ollama_path is not None, ollama_path or "RAISETICKET:: NOT FOUND -- RUN MANUALLY `run setup.sh")
    
    server_up = False
    try: 
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        server_up = r.status_code == 200
    except requests.exceptions.ConnectionError:
        pass
    all_ok &= check("ollama server responding", server_up, f"{OLLAMA_URL}/api/tags — run: ollama serve")
    
    pulled_models = set()
    if server_up:
        try:
            tags = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).json()
            pulled_models = {m["name"] for m in tags.get("models", [])}
        except Exception as e:
            check("could not parse ollama /api/tags response", False, str(e))
    
    for model, level in REQUIRED_MODELS.items():
        is_blocking = level == "blocking"
        have_it = any(model in m for m in pulled_models)
        ok = check(f"model pulled: {model}", have_it, "" if have_it else f"run ollama pull {model}", blocking=is_blocking)
        all_ok &=ok
        
    for pkg in REQUIRED_BY_PACKAGES:
        try: 
            __import__(pkg)
            check(f"python package: {pkg}", True)
        except ImportError:
            all_ok &= check(f"pyhton package: {pkg}", False, "run: pip insrall -r requirements.txt")
    
    gpu = shutil.which("nvidia-smi")
    if gpu:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader"],
                            capture_output=True, text=True)
        check("GPU Detected", True, out.stdout.strip(), blocking=False)
    else: 
        check("GPU Detected", False, "no nvidia-smi --CPU onlly inference, expect it to be slow", blocking=False)
        
    print()
    print("RAISETICKET:: ALL BLOCKS CHECKS PASSED" if all_ok else "RAISETICKET:: BLOCKING CHECK FAILED --fix the real FAIL lines above before the proceding")
    
    return 0 if all_ok else 1

if __name__=="__main__":
    sys.exit(main())
import shutil
import sys

import requests

from .config import get_config

OLLAMA_URL = "http://localhost:11434"
REQUIRED_MODELS = {"qwen2.5-coder:7b": "blocking"}
CORE_PY_PACKAGES = ["requests", "yaml", "pathspec"]


def check(label: str, ok: bool, detail: str = "", blocking: bool = True):
    status = "PASS" if ok else ("FAIL" if blocking else "WARN")
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))
    return ok or not blocking


def _check_provider(cfg, label_prefix: str, blocking: bool) -> bool:
    ok = True
    if cfg.provider == "ollama":
        ollama_path = shutil.which("ollama")
        ok &= check(f"{label_prefix} ollama binary on PATH", ollama_path is not None,
                    ollama_path or "not found — run setup_ollama.sh", blocking=blocking)

        server_up = False
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
            server_up = r.status_code == 200
        except requests.exceptions.ConnectionError:
            pass
        ok &= check(f"{label_prefix} ollama server responding", server_up,
                    f"{OLLAMA_URL}/api/tags — run: ollama serve", blocking=blocking)

        pulled_models = set()
        if server_up:
            try:
                tags = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).json()
                pulled_models = {m["name"] for m in tags.get("models", [])}
            except Exception as e:
                check(f"{label_prefix} could not parse ollama /api/tags response", False, str(e), blocking=False)

        for model, level in REQUIRED_MODELS.items():
            have_it = any(model in m for m in pulled_models)
            ok &= check(f"{label_prefix} model pulled: {model}", have_it,
                        "" if have_it else f"run: ollama pull {model}", blocking=(blocking and level == "blocking"))
    else:
        ok &= check(f"{label_prefix} llm provider: {cfg.provider}", bool(cfg.api_key),
                    "" if cfg.api_key else "set llm.apiKey via issueloop.use(llm={...})", blocking=blocking)
    return ok


def main():
    all_ok = True
    cfg = get_config()

    for pkg in CORE_PY_PACKAGES:
        try:
            __import__(pkg)
            check(f"python package: {pkg}", True)
        except ImportError:
            all_ok &= check(f"python package: {pkg}", False, "run: pip install -r requirements.txt")

    if cfg.database == "local":
        check("database backend: local (sqlite)", True, "no external service required")
    elif cfg.database == "supabase":
        import os
        configured = bool(os.environ.get("SUPABASE_URL")) and bool(os.environ.get("SUPABASE_KEY"))
        all_ok &= check("SUPABASE_URL / SUPABASE_KEY set", configured,
                         "" if configured else "copy .env.example to .env and fill them in")
        try:
            import supabase
            check("python package: supabase", True)
        except ImportError:
            all_ok &= check("python package: supabase", False, 'run: pip install -e ".[supabase]"')

    providers = cfg.llm_providers if cfg.llm_providers else [cfg.llm]
    if len(providers) == 1:
        all_ok &= _check_provider(providers[0], "", blocking=True)
    else:
        any_provider_ready = False
        for idx, p in enumerate(providers):
            label = f"[priority {idx + 1}/{len(providers)}]"
            provider_ok = _check_provider(p, label, blocking=False)
            any_provider_ready = any_provider_ready or provider_ok
        all_ok &= check(f"at least one of {len(providers)} configured LLM providers is ready", any_provider_ready)

    print()
    print("ALL BLOCKING CHECKS PASSED" if all_ok else "BLOCKING CHECKS FAILED — fix the FAIL lines above before proceeding")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
from pathlib import Path
import requests
import yaml
CONFIG_PATH=Path(__file__).resolve().parent.parent/"config"/"provider_config.yaml"

def _load_config():
    return yaml.safe_load(CONFIG_PATH.read_text())["reasoning"]

def chat(prompt: str, system: str=""):
    cfg=_load_config()
    if cfg["provider"]!="ollama":
        raise NotImplementedError(
            f"RAISETICKET:: provider '{cfg['provider']}' not wired yet -- extend llm.py;s chat for it"
        )
    messages=[]
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user","content": prompt})
    resp=requests.post(
        f"{cfg['base_url']}/api/chat",
        json={"model": cfg["model"], "messages": messages, "stream": False},
        timeout=120
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]
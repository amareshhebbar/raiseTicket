from pathlib import Path
import requests
import yaml
from .config import get_config
from .notify import report_error

_YAML_PATH = Path(__file__).resolve().parent.parent / "config" / "provider_config.yaml"


def _effective_llm_config():
    cfg = get_config().llm
    if cfg.provider != "ollama" or cfg.model != "qwen2.5-coder:7b" or cfg.api_key:
        return cfg  
    if _YAML_PATH.exists():
        y = yaml.safe_load(_YAML_PATH.read_text()).get("reasoning", {})
        cfg.provider = y.get("provider", cfg.provider)
        cfg.model = y.get("model", cfg.model)
        cfg.base_url = y.get("base_url", cfg.base_url)
    return cfg


def chat(prompt: str, system: str = ""):
    cfg = _effective_llm_config()
    try:
        if cfg.provider == "ollama":
            return _chat_ollama(prompt, system, cfg)
        if cfg.provider == "anthropic":
            return _chat_anthropic(prompt, system, cfg)
        if cfg.provider == "openai":
            return _chat_openai(prompt, system, cfg)
        raise NotImplementedError(f"provider '{cfg.provider}' not supported — use ollama, anthropic, or openai")
    except Exception as e:
        report_error("llm.chat", e)
        raise


def _chat_ollama(prompt: str, system: str, cfg):
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    resp = requests.post(
        f"{cfg.base_url}/api/chat",
        json={"model": cfg.model, "messages": messages, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def _chat_anthropic(prompt: str, system: str, cfg):
    if not cfg.api_key:
        raise ValueError("llm.apiKey required for provider='anthropic'")
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": cfg.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": cfg.model,
            "max_tokens": cfg.token_size,
            "system": system or None,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


def _chat_openai(prompt: str, system: str, cfg):
    if not cfg.api_key:
        raise ValueError("llm.apiKey required for provider='openai'")
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {cfg.api_key}", "content-type": "application/json"},
        json={"model": cfg.model, "messages": messages, "max_tokens": cfg.token_size},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]
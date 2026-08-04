import json
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

from .config import get_config
from .config_paths import resolve_config_path
from .notify import report_error

_USAGE_LOG = Path(__file__).resolve().parent.parent / "data" / "logs" / "llm_usage.jsonl"


def _effective_llm_providers():
    cfg = get_config()
    providers = list(cfg.llm_providers) if cfg.llm_providers else [cfg.llm]

    if len(providers) == 1:
        p = providers[0]
        if p.provider == "ollama" and p.model == "qwen2.5-coder:7b" and not p.api_key:
            yaml_path = resolve_config_path("provider_config.yaml")
            if yaml_path.exists():
                y = yaml.safe_load(yaml_path.read_text()).get("reasoning", {})
                p.provider = y.get("provider", p.provider)
                p.model = y.get("model", p.model)
                p.base_url = y.get("base_url", p.base_url)

    return providers


def _record_usage(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> None:
    _USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _USAGE_LOG.open("a") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }) + "\n")


def chat(prompt: str, system: str = ""):
    providers = _effective_llm_providers()
    last_exc = None

    for idx, cfg in enumerate(providers):
        is_last = idx == len(providers) - 1
        try:
            if cfg.provider == "ollama":
                return _chat_ollama(prompt, system, cfg)
            if cfg.provider == "anthropic":
                return _chat_anthropic(prompt, system, cfg)
            if cfg.provider == "openai":
                return _chat_openai(prompt, system, cfg)
            raise NotImplementedError(f"provider '{cfg.provider}' not supported — use ollama, anthropic, or openai")
        except Exception as e:
            last_exc = e
            label = f"llm.chat (provider {idx + 1}/{len(providers)}: {cfg.provider})"
            report_error(label, e)
            if is_last:
                raise
            continue

    raise last_exc if last_exc else RuntimeError("no LLM providers configured")


def _chat_ollama(prompt: str, system: str, cfg):
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    resp = requests.post(
        f"{cfg.base_url}/api/chat",
        json={"model": cfg.model, "messages": messages, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    body = resp.json()
    _record_usage(
        "ollama", cfg.model,
        body.get("prompt_eval_count", 0),
        body.get("eval_count", 0),
    )
    return body["message"]["content"]


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
    body = resp.json()
    usage = body.get("usage", {})
    _record_usage(
        "anthropic", cfg.model,
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0),
    )
    return body["content"][0]["text"]


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
    body = resp.json()
    usage = body.get("usage", {})
    _record_usage(
        "openai", cfg.model,
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
    )
    return body["choices"][0]["message"]["content"]


def get_token_consumption(provider: str = None) -> dict:
    if not _USAGE_LOG.exists():
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}
    for line in _USAGE_LOG.read_text().splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if provider and entry["provider"] != provider:
            continue
        totals["prompt_tokens"] += entry["prompt_tokens"]
        totals["completion_tokens"] += entry["completion_tokens"]
        totals["total_tokens"] += entry["total_tokens"]
        totals["calls"] += 1
    return totals


def get_token_consumption_by_provider() -> dict:
    if not _USAGE_LOG.exists():
        return {}
    by_provider: dict = {}
    for line in _USAGE_LOG.read_text().splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        bucket = by_provider.setdefault(entry["provider"], {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0})
        bucket["prompt_tokens"] += entry["prompt_tokens"]
        bucket["completion_tokens"] += entry["completion_tokens"]
        bucket["total_tokens"] += entry["total_tokens"]
        bucket["calls"] += 1
    return by_provider


def get_llm_call_history(limit: int = 50) -> list:
    if not _USAGE_LOG.exists():
        return []
    lines = [json.loads(l) for l in _USAGE_LOG.read_text().splitlines() if l.strip()]
    return lines[-limit:]
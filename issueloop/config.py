from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class LLMConfig:
    provider: str = "ollama"
    model: str = "qwen2.5-coder:7b"
    api_key: Optional[str] = None
    base_url: str = "http://localhost:11434"
    token_size: int = 1024


@dataclass
class NotifyConfig:
    email: Optional[str] = None
    webhook: Optional[str] = None


@dataclass
class Config:
    database: str = "local"
    database_path: Optional[str] = None
    retention_days: int = 30
    llm: LLMConfig = field(default_factory=LLMConfig)
    llm_providers: List[LLMConfig] = field(default_factory=list)
    notify: NotifyConfig = field(default_factory=NotifyConfig)


_config = Config()


def _build_llm_config(d: dict) -> LLMConfig:
    return LLMConfig(
        provider=d.get("provider", "ollama"),
        model=d.get("model", "qwen2.5-coder:7b"),
        api_key=d.get("apiKey") or d.get("api_key"),
        base_url=d.get("baseUrl") or d.get("base_url", "http://localhost:11434"),
        token_size=d.get("tokenSize") or d.get("token_size", 1024),
    )


def use(
    database: str = "local",
    database_path: Optional[str] = None,
    retention_days: int = 30,
    llm: Optional[dict] = None,
    notify: Optional[dict] = None,
):
    global _config
    llm = llm or {}
    notify = notify or {}

    if "providers" in llm:
        provider_dicts = llm["providers"]
    else:
        provider_dicts = [llm]

    llm_providers = [_build_llm_config(d) for d in provider_dicts] or [LLMConfig()]

    _config = Config(
        database=database,
        database_path=database_path,
        retention_days=retention_days,
        llm=llm_providers[0],
        llm_providers=llm_providers,
        notify=NotifyConfig(
            email=notify.get("email"),
            webhook=notify.get("webhook"),
        ),
    )
    return _config


def get_config():
    return _config
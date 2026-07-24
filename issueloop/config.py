from dataclasses import dataclass, field
from typing import Optional

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
    notify: NotifyConfig = field(default_factory=NotifyConfig)
    
_config = Config()

def use(
    database: str = "local",
    database_path: Optional[str] = None,
    retention_days: int = 30,
    llm: Optional[dict] = None,
    notify: Optional[dict] = None):
    global _config
    llm = llm or {}
    notify = notify or {}
    _config = Config(
        database=database,
        database_path=database_path,
        retention_days=retention_days,
        llm=LLMConfig(
            provider=llm.get("provider", "ollama"),
            model=llm.get("model", "qwen2.5-coder:7b"),
            api_key=llm.get("apiKey") or llm.get("api_key"),
            base_url=llm.get("baseUrl") or llm.get("base_url", "http://localhost:11434"),
            token_size=llm.get("tokenSize") or llm.get("token_size", 1024),
        ),
        notify=NotifyConfig(
            email=notify.get("email"),
            webhook=notify.get("webhook"),
        ),
    )
    return _config


def get_config():
    return _config

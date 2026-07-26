
import issueloop
from issueloop.config import get_config


def test_use_sets_database_and_llm_snake_case():
    issueloop.use(database="local", llm={"provider": "anthropic", "model": "claude-sonnet-4-6",
                                          "api_key": "sk-test", "token_size": 2048})
    cfg = get_config()
    assert cfg.database == "local"
    assert cfg.llm.provider == "anthropic"
    assert cfg.llm.model == "claude-sonnet-4-6"
    assert cfg.llm.api_key == "sk-test"
    assert cfg.llm.token_size == 2048


def test_use_accepts_camel_case():
    issueloop.use(llm={"apiKey": "sk-camel", "tokenSize": 4096, "baseUrl": "http://x"})
    cfg = get_config()
    assert cfg.llm.api_key == "sk-camel"
    assert cfg.llm.token_size == 4096
    assert cfg.llm.base_url == "http://x"


def test_use_defaults_to_local_and_ollama():
    issueloop.use()
    cfg = get_config()
    assert cfg.database == "local"
    assert cfg.llm.provider == "ollama"
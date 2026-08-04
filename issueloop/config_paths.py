import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULTS_DIR = Path(__file__).resolve().parent / "_defaults"

_ENV_VARS = {
    "permission.yaml": "ISSUELOOP_PERMISSION_PATH",
    "provider_config.yaml": "ISSUELOOP_PROVIDER_CONFIG_PATH",
}


def resolve_config_path(filename: str) -> Path:
    env_var = _ENV_VARS.get(filename)
    if env_var and os.environ.get(env_var):
        return Path(os.environ[env_var])

    cwd_candidate = Path.cwd() / "config" / filename
    if cwd_candidate.exists():
        return cwd_candidate

    checkout_candidate = _PROJECT_ROOT / "config" / filename
    if checkout_candidate.exists():
        return checkout_candidate

    return _DEFAULTS_DIR / filename
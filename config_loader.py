import yaml
from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)

# Load .env file first
load_dotenv()

def _resolve_env(value):
    """Replace ${VAR} with environment variable value."""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]  # strip ${ and }
        resolved = os.getenv(env_var)
        if resolved is None:
            logger.warning(f"Environment variable '{env_var}' not set.")
        return resolved
    return value

def _resolve_nested_env(data):
    """Recursively resolve env vars in nested dict/lists."""
    if isinstance(data, dict):
        return {k: _resolve_nested_env(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_resolve_nested_env(i) for i in data]
    else:
        return _resolve_env(data)

def load_config(path="config.yaml"):
    """
    Load configuration from YAML file and resolve environment variables.
    """
    if not os.path.isfile(path):
        logger.error(f"Config file not found: {path}")
        raise FileNotFoundError(f"Config file not found: {path}")

    try:
        with open(path, "r") as f:
            raw_config = yaml.safe_load(f)
        config = _resolve_nested_env(raw_config)
        logger.info(f"Configuration loaded from {path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

"""
Configuration management module.
Supports loading from environment variables (.env), config.json file, or defaults.
"""
import json
import os
import threading
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

DEFAULT_CONFIG = {
    "monitor": {
        "check_dates": ["20260213", "20260214", "20260215"],
        "interval_seconds": 60,
        "notify_on_available": True,
    },
    "email": {
        "mail_host": "smtp.qq.com",
        "mail_port": None,  # Auto-detect based on mail_host (465 for SSL, 587 for TLS)
        "mail_user": "",
        "mail_pass": "",
        "sender": "",
        "receivers": [""],
    },
}

_CONFIG_LOCK = threading.Lock()


def _config_path():
    """Get the path to config.json in the config directory."""
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config", "config.json"
    )


def _merge_config(base, override):
    """Recursively merge override config into base config."""
    if not isinstance(override, dict):
        return base
    merged = dict(base)
    for key, value in override.items():
        if key in base and isinstance(base[key], dict):
            merged[key] = _merge_config(base[key], value)
        else:
            merged[key] = value
    return merged


def _load_config_from_env():
    """Load configuration from environment variables (for Railway deployment)."""
    env_config = {}
    
    # Monitor settings from environment
    monitor_all = os.getenv("MONITOR_ALL_DATES", "false").lower() in ("true", "1", "yes")
    if monitor_all:
        check_dates = ["all"]
    else:
        check_dates_str = os.getenv("MONITOR_CHECK_DATES", "")
        check_dates = [d.strip() for d in check_dates_str.split(",") if d.strip()] if check_dates_str else None
    
    interval_seconds_str = os.getenv("MONITOR_INTERVAL_SECONDS", "")
    interval_seconds = int(interval_seconds_str) if interval_seconds_str.isdigit() else None
    
    notify_on_available_str = os.getenv("MONITOR_NOTIFY_ON_AVAILABLE", "").lower()
    notify_on_available = notify_on_available_str in ("true", "1", "yes") if notify_on_available_str else None
    
    if check_dates is not None or interval_seconds is not None or notify_on_available is not None:
        env_config["monitor"] = {}
        if check_dates is not None:
            env_config["monitor"]["check_dates"] = check_dates
        if interval_seconds is not None:
            env_config["monitor"]["interval_seconds"] = interval_seconds
        if notify_on_available is not None:
            env_config["monitor"]["notify_on_available"] = notify_on_available
    
    # Email settings from environment
    mail_port_str = os.getenv("MAIL_PORT", "").strip()
    mail_port = int(mail_port_str) if mail_port_str.isdigit() else None
    
    email_vars = {
        "mail_host": os.getenv("MAIL_HOST", "").strip(),
        "mail_port": mail_port,
        "mail_user": os.getenv("MAIL_USER", "").strip(),
        "mail_pass": os.getenv("MAIL_PASS", "").strip(),
        "sender": os.getenv("SENDER", "").strip(),
        "receivers": [r.strip() for r in os.getenv("RECEIVERS", "").split(",") if r.strip()],
    }
    
    # Only include non-empty/non-None values
    if mail_port is None:
        del email_vars["mail_port"]
    
    if any(v for v in email_vars.values() if v not in (None, [])):
        env_config["email"] = email_vars
    
    return env_config


def load_config():
    """Load configuration from .env first, then config.json, with .env taking precedence."""
    # Load from environment variables first
    env_config = _load_config_from_env()
    
    # Then try to load from config.json
    path = _config_path()
    with _CONFIG_LOCK:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    file_config = json.load(handle)
                    # Merge: env config overrides file config
                    file_config = _merge_config(DEFAULT_CONFIG, file_config)
                    return _merge_config(file_config, env_config)
            except (OSError, json.JSONDecodeError):
                pass
    
    # If no config.json or error, use defaults merged with env
    return _merge_config(DEFAULT_CONFIG, env_config)


def save_config(config):
    """Save configuration to config.json."""
    path = _config_path()
    # Ensure config directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with _CONFIG_LOCK:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2, ensure_ascii=True)
            handle.write("\n")

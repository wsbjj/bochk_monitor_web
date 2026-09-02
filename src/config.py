"""
Configuration management module.
Supports loading from environment variables (.env), config.json file, or defaults.

Priority (highest wins):
    1. data/config.json  — values saved from the Web UI
    2. Environment variables — bootstrap / first deploy
    3. DEFAULT_CONFIG
"""
import json
import os
import threading
from dotenv import load_dotenv

from .watchers import normalize_watchers

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
    "watchers": [],
}

_CONFIG_LOCK = threading.Lock()


def get_data_dir():
    """Return the persistent data directory.

    Resolution order:
        1. DATA_DIR environment variable
        2. RAILWAY_VOLUME_MOUNT_PATH (Railway volume)
        3. /app/data if that directory already exists
        4. <project_root>/data
    """
    explicit = os.getenv("DATA_DIR", "").strip()
    if explicit:
        return explicit

    railway_mount = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
    if railway_mount:
        return railway_mount

    if os.path.isdir("/app/data"):
        return "/app/data"

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "data")


def _config_path():
    """Get the path to config.json in the data directory."""
    return os.path.join(get_data_dir(), "config.json")


def get_persistence_info():
    """Return where config is stored and which source is currently active."""
    data_dir = get_data_dir()
    path = _config_path()
    volume_mount = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
    data_dir_env = os.getenv("DATA_DIR", "").strip()
    exists = os.path.isfile(path)
    if exists:
        source = "file"
    elif _load_config_from_env():
        source = "env"
    else:
        source = "default"
    return {
        "data_dir": data_dir,
        "config_path": path,
        "config_exists": exists,
        "volume_mount": volume_mount or None,
        "persistent": bool(volume_mount or data_dir_env),
        "source": source,
    }


def _merge_config(base, override):
    """Recursively merge override config into base config."""
    if not isinstance(override, dict):
        return base
    merged = dict(base)
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            merged[key] = _merge_config(base[key], value)
        else:
            merged[key] = value
    return merged


def _load_config_from_env():
    """Load configuration from environment variables (for Railway bootstrap)."""
    env_config = {}

    # Monitor settings from environment
    monitor_all = os.getenv("MONITOR_ALL_DATES", "false").lower() in ("true", "1", "yes")
    if monitor_all:
        check_dates = ["all"]
    else:
        check_dates_str = os.getenv("MONITOR_CHECK_DATES", "")
        check_dates = (
            [d.strip() for d in check_dates_str.split(",") if d.strip()]
            if check_dates_str
            else None
        )

    interval_seconds_str = os.getenv("MONITOR_INTERVAL_SECONDS", "")
    interval_seconds = int(interval_seconds_str) if interval_seconds_str.isdigit() else None

    notify_on_available_str = os.getenv("MONITOR_NOTIFY_ON_AVAILABLE", "").lower()
    notify_on_available = (
        notify_on_available_str in ("true", "1", "yes") if notify_on_available_str else None
    )

    if check_dates is not None or interval_seconds is not None or notify_on_available is not None:
        env_config["monitor"] = {}
        if check_dates is not None:
            env_config["monitor"]["check_dates"] = check_dates
        if interval_seconds is not None:
            env_config["monitor"]["interval_seconds"] = interval_seconds
        if notify_on_available is not None:
            env_config["monitor"]["notify_on_available"] = notify_on_available

    mail_port_str = os.getenv("MAIL_PORT", "").strip()
    mail_port = int(mail_port_str) if mail_port_str.isdigit() else None

    email_vars = {}
    mail_host = os.getenv("MAIL_HOST", "").strip()
    mail_user = os.getenv("MAIL_USER", "").strip()
    mail_pass = os.getenv("MAIL_PASS", "").strip()
    sender = os.getenv("SENDER", "").strip()
    receivers = [r.strip() for r in os.getenv("RECEIVERS", "").split(",") if r.strip()]
    if mail_host:
        email_vars["mail_host"] = mail_host
    if mail_port is not None:
        email_vars["mail_port"] = mail_port
    if mail_user:
        email_vars["mail_user"] = mail_user
    if mail_pass:
        email_vars["mail_pass"] = mail_pass
    if sender:
        email_vars["sender"] = sender
    if receivers:
        email_vars["receivers"] = receivers

    if email_vars:
        env_config["email"] = email_vars

    return env_config


def _read_file_config():
    """Read config.json if it exists; return empty dict otherwise."""
    path = _config_path()
    with _CONFIG_LOCK:
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}


def load_config():
    """Load configuration with Web UI file taking precedence over env vars."""
    env_config = _load_config_from_env()
    file_config = _read_file_config()
    merged = _merge_config(DEFAULT_CONFIG, env_config)
    merged = _merge_config(merged, file_config)
    return normalize_watchers(merged)


def save_config(config):
    """Save configuration to config.json on the persistent volume."""
    path = _config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with _CONFIG_LOCK:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2, ensure_ascii=True)
            handle.write("\n")

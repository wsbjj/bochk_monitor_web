import json
import os
import threading

DEFAULT_CONFIG = {
    "monitor": {
        "check_dates": ["20260213", "20260214", "20260215"],
        "interval_seconds": 60,
        "notify_on_available": True,
    },
    "email": {
        "mail_host": "smtp.qq.com",
        "mail_user": "",
        "mail_pass": "",
        "sender": "",
        "receivers": [""],
    },
}

_CONFIG_LOCK = threading.Lock()


def _config_path():
    return os.path.join(os.path.dirname(__file__), "config.json")


def _merge_config(base, override):
    if not isinstance(override, dict):
        return base
    merged = dict(base)
    for key, value in override.items():
        if key in base and isinstance(base[key], dict):
            merged[key] = _merge_config(base[key], value)
        else:
            merged[key] = value
    return merged


def load_config():
    path = _config_path()
    with _CONFIG_LOCK:
        if not os.path.exists(path):
            save_config(DEFAULT_CONFIG)
            return _merge_config(DEFAULT_CONFIG, {})
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            save_config(DEFAULT_CONFIG)
            return _merge_config(DEFAULT_CONFIG, {})
    return _merge_config(DEFAULT_CONFIG, data)


def save_config(config):
    path = _config_path()
    with _CONFIG_LOCK:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2, ensure_ascii=True)
            handle.write("\n")

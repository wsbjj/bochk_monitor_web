"""
Logging configuration module.
Handles logging to both console and rotating file.
"""
import logging
import logging.handlers
import os
import glob
import re
import ast
from time import strftime
import time

# Get timezone offset from env, default to 0
# Calculation: User Timezone - Server Timezone
# Example: User GMT+8, Server GMT-4 => Offset = 8 - (-4) = 12
try:
    TIMEZONE_OFFSET = float(os.getenv("TIMEZONE_OFFSET", "0"))
except ValueError:
    TIMEZONE_OFFSET = 0

def custom_time_converter(timestamp):
    """Convert timestamp to struct_time with timezone offset applied."""
    return time.localtime(timestamp + TIMEZONE_OFFSET * 3600)

logging.Formatter.converter = staticmethod(custom_time_converter)

def _get_data_dir():
    """Get the persistent data directory (shared with config)."""
    from .config import get_data_dir
    return get_data_dir()

# Create logs directory path inside data directory
LOGS_DIR = os.path.join(_get_data_dir(), "logs")
# Log filename based on date (daily log file)
LOG_FILENAME = os.path.join(LOGS_DIR, strftime("bochk_monitor_%Y_%m_%d.log"))

CYCLE_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Monitor cycle: (\d+) available dates: (\[[^\]]*\])(?: branches: (.*))?$"
)
ERROR_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Monitoring error: (.*)"
)
JSON_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*INFO: (\{.*\})"
)


def parse_cycle_log_line(line):
    """Parse one Monitor cycle log line into a history dict, or None."""
    cycle_match = CYCLE_PATTERN.search(line)
    if not cycle_match:
        return None
    available_list_str = cycle_match.group(3)
    available_list = [
        item.strip().strip("'").strip('"')
        for item in available_list_str.strip("[]").split(",")
        if item.strip()
    ]
    remarks_raw = (cycle_match.group(4) or "").strip()
    if remarks_raw in ("", "-"):
        remarks = None
        available_branches = []
    else:
        remarks = remarks_raw
        available_branches = [
            part.strip() for part in remarks_raw.split(",") if part.strip()
        ]
    return {
        "checked_at": cycle_match.group(1),
        "available_num": int(cycle_match.group(2)),
        "available_list": available_list,
        "available_branches": available_branches,
        "remarks": remarks,
        "eai_code": "SUCCESS",
        "error": None,
    }


def _upsert_history(history, index_by_ts, entry, replace=False):
    """Keep one history row per second; cycle lines can replace JSON dumps."""
    ts = entry["checked_at"]
    if ts in index_by_ts:
        if replace:
            history[index_by_ts[ts]] = entry
        return
    index_by_ts[ts] = len(history)
    history.append(entry)


def read_history_from_logs():
    """Read and parse all log files to reconstruct history."""
    history = []
    log_files = sorted(glob.glob(os.path.join(LOGS_DIR, "bochk_monitor_*.log")))
    index_by_ts = {}

    for log_file in log_files:
        try:
            with open(log_file, "r", encoding="utf-8") as handle:
                for line in handle:
                    parsed = parse_cycle_log_line(line)
                    if parsed:
                        _upsert_history(history, index_by_ts, parsed, replace=True)
                        continue

                    error_match = ERROR_PATTERN.search(line)
                    if error_match:
                        _upsert_history(
                            history,
                            index_by_ts,
                            {
                                "checked_at": error_match.group(1),
                                "available_num": None,
                                "available_list": [],
                                "available_branches": [],
                                "remarks": None,
                                "eai_code": None,
                                "error": error_match.group(2),
                            },
                        )
                        continue

                    json_match = JSON_PATTERN.search(line)
                    if json_match:
                        try:
                            data = ast.literal_eval(json_match.group(2))
                            if isinstance(data, dict) and "dateQuota" in data:
                                date_quota = data.get("dateQuota", {})
                                available_list = [
                                    date_key
                                    for date_key, status in date_quota.items()
                                    if status != "F"
                                ]
                                _upsert_history(
                                    history,
                                    index_by_ts,
                                    {
                                        "checked_at": json_match.group(1),
                                        "available_num": len(available_list),
                                        "available_list": available_list,
                                        "available_branches": [],
                                        "remarks": None,
                                        "eai_code": data.get("eaiCode", "SUCCESS"),
                                        "error": None,
                                    },
                                )
                        except Exception:
                            pass
        except Exception:
            continue

    return history


def _setup_logger():
    """Configure logger with console and file handlers."""
    # Ensure logs directory exists
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR, exist_ok=True)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Log format
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (Time-based rotation, daily)
    # when='midnight' means rotate at midnight
    # interval=1 means every 1 day
    # backupCount=30 keeps last 30 days of logs
    file_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_FILENAME, when='midnight', interval=1, backupCount=30, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# Initialize logger on module import
logger = _setup_logger()

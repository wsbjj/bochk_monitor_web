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

def _get_data_dir():
    """Get the persistent data directory (shared with config)."""
    project_root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(project_root, "data")

# Create logs directory path inside data directory
LOGS_DIR = os.path.join(_get_data_dir(), "logs")
# Log filename based on date (daily log file)
LOG_FILENAME = os.path.join(LOGS_DIR, strftime("bochk_monitor_%Y_%m_%d.log"))


def read_history_from_logs():
    """Read and parse all log files to reconstruct history."""
    history = []
    # Match both old hourly logs and new daily logs
    log_files = sorted(glob.glob(os.path.join(LOGS_DIR, "bochk_monitor_*.log")))
    
    # Regex patterns
    # 2026-02-12 11:15:35,123 INFO: Monitor cycle: 0 available dates: []
    cycle_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Monitor cycle: (\d+) available dates: (\[.*\])")
    # 2026-02-12 11:15:35,123 ERROR: Monitoring error: some error
    error_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Monitoring error: (.*)")
    # Legacy/Raw JSON log pattern: 2026-02-12 11:19:55,717 INFO: {'acceptTerms': None, ...}
    json_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*INFO: (\{.*\})")
    
    # Keep track of timestamps to prevent duplicates (since we log both summary and raw JSON now)
    seen_timestamps = set()

    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    cycle_match = cycle_pattern.search(line)
                    if cycle_match:
                        checked_at = cycle_match.group(1)
                        
                        # Dedup: if we already have a record for this second, skip
                        if checked_at in seen_timestamps:
                            continue
                            
                        available_num = int(cycle_match.group(2))
                        available_list_str = cycle_match.group(3)
                        # Parse list string "['20260213', '20260214']" -> list
                        available_list = [d.strip().strip("'").strip('"') for d in available_list_str.strip("[]").split(",") if d.strip()]
                        
                        history.append({
                            "checked_at": checked_at,
                            "available_num": available_num,
                            "available_list": available_list,
                            "eai_code": "SUCCESS", 
                            "error": None
                        })
                        seen_timestamps.add(checked_at)
                        continue
                        
                    error_match = error_pattern.search(line)
                    if error_match:
                        checked_at = error_match.group(1)
                        
                        # Dedup
                        if checked_at in seen_timestamps:
                            continue

                        error_msg = error_match.group(2)
                        history.append({
                            "checked_at": checked_at,
                            "available_num": None,
                            "available_list": [],
                            "eai_code": None,
                            "error": error_msg
                        })
                        seen_timestamps.add(checked_at)
                        continue

                    # Fallback: Try to parse raw JSON log (for older logs)
                    json_match = json_pattern.search(line)
                    if json_match:
                        try:
                            checked_at = json_match.group(1)
                            
                            # Dedup
                            if checked_at in seen_timestamps:
                                continue

                            json_str = json_match.group(2)
                            data = ast.literal_eval(json_str)
                            
                            if isinstance(data, dict) and 'dateQuota' in data:
                                date_quota = data.get('dateQuota', {})
                                available_list = []
                                for date_key, status in date_quota.items():
                                    if status != 'F':
                                        available_list.append(date_key)
                                
                                history.append({
                                    "checked_at": checked_at,
                                    "available_num": len(available_list),
                                    "available_list": available_list,
                                    "eai_code": data.get('eaiCode', 'SUCCESS'),
                                    "error": None
                                })
                                seen_timestamps.add(checked_at)
                        except Exception:
                            pass # Ignore parse errors for JSON lines
                            
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

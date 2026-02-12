"""Entry point for standalone monitoring worker.

This script runs the BOCHK appointment monitoring in standalone mode,
continuously polling the API and sending email notifications when
appointments become available.

This is used by Procfile for the worker dyno in Railway deployment.

Environment variables:
    CONFIG_FILE: Path to config.json (default: config/config.json)
    LOG_FILE: Path to log file (default: logs/bochk_monitor.log)
"""

from src.monitor import main

if __name__ == "__main__":
    main()

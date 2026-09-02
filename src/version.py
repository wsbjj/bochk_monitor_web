"""App version and build timestamp shown in the page footer."""
import os
import subprocess
from datetime import datetime, timedelta, timezone

APP_VERSION = "v1.1"


def get_build_time():
    """Return a display timestamp for this build.

    Prefer BUILD_TIME, then the latest git commit time, then this file's mtime.
    """
    explicit = os.getenv("BUILD_TIME", "").strip()
    if explicit:
        return explicit
    stamp = _git_commit_timestamp()
    if stamp is None:
        stamp = os.path.getmtime(__file__)
    return _format_timestamp(stamp)


def _format_timestamp(stamp):
    try:
        offset = float(os.getenv("TIMEZONE_OFFSET", "0"))
    except ValueError:
        offset = 0
    tzinfo = timezone(timedelta(hours=offset)) if offset else None
    moment = datetime.fromtimestamp(stamp, tz=tzinfo)
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def _git_commit_timestamp():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        output = subprocess.check_output(
            ["git", "log", "-1", "--format=%ct"],
            cwd=root,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return int(output.strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        return None

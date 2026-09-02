"""Flask web application for BOCHK appointment monitoring.

This module provides a web interface for monitoring BOCHK appointment availability,
managing monitor configuration, and viewing monitoring history.
"""

import glob
import json
from datetime import datetime, timedelta, timezone

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_basicauth import BasicAuth

from .config import get_persistence_info, load_config, save_config
from .logger import logger, read_history_from_logs, TIMEZONE_OFFSET
from .monitor import (
    collect_district_availability,
    cycle_available_count,
    enrich_availability_with_details,
    flatten_available_slots,
    get_branches,
    get_districts,
    get_jsonAvailableDateAndTime,
    log_monitor_cycle,
    notify_watchers,
    parse,
    peek_districts,
)
from .send_email import send_email
from .watchers import clean_watcher


import os
import threading
import time

# Build a fixed timezone from the same offset used in logger.py
_TZ_SHANGHAI = timezone(timedelta(hours=TIMEZONE_OFFSET)) if TIMEZONE_OFFSET else None


def _now():
    """Return timezone-aware current time (Asia/Shanghai if offset is set)."""
    if _TZ_SHANGHAI:
        return datetime.now(_TZ_SHANGHAI)
    return datetime.now()


def _now_str(fmt="%Y-%m-%d %H:%M:%S"):
    """Return formatted current time string in the configured timezone."""
    return _now().strftime(fmt)


def create_app():
    """Create and configure Flask application.

    Returns:
        Flask: Configured Flask application instance.
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
    )

    # Load Flask secret key from environment or use default
    app.secret_key = os.getenv(
        "FLASK_SECRET_KEY", "bochk-monitor-secret-key-change-in-production"
    )

    # Configure Basic Auth
    app.config['BASIC_AUTH_USERNAME'] = os.getenv('ADMIN_USERNAME', 'admin')
    app.config['BASIC_AUTH_PASSWORD'] = os.getenv('ADMIN_PASSWORD', 'admin')
    app.config['BASIC_AUTH_FORCE'] = True  # Protect entire site

    basic_auth = BasicAuth(app)

    # Initialize monitor state and register routes
    monitor_state = MonitorState(load_config())
    register_routes(app, monitor_state)

    return app, monitor_state


class MonitorState:
    """Manages monitoring state and background polling thread.

    Attributes:
        running (bool): Whether monitoring is currently active.
        interval_seconds (int): Seconds between checks.
        check_dates (list): Dates to check for availability.
        notify_on_available (bool): Whether to send email on availability.
        last_checked_at (str): Timestamp of last check.
        last_available_num (int): Number of available slots found.
        last_available_list (list): List of available dates.
        history (list): Recent monitoring events (limited to history_limit).
    """

    def __init__(self, config):
        """Initialize MonitorState from config.

        Args:
            config (dict): Configuration dictionary from config.load_config().
        """
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        monitor_config = config.get("monitor", {})
        self.interval_seconds = int(monitor_config.get("interval_seconds", 60))
        self.check_dates = list(monitor_config.get("check_dates") or [])
        self.watchers = [clean_watcher(item) for item in (config.get("watchers") or [])]
        self.notify_on_available = bool(
            monitor_config.get("notify_on_available", True)
        )
        self.last_checked_at = None
        self.last_available_num = 0
        self.last_available_list = []
        self.last_available_branches = []
        self.last_eai_code = None
        self.last_error = None
        self.history = []
        self.history_limit = 200

    def start(self):
        """Start the background monitoring thread."""
        with self.lock:
            if self.running:
                return
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
            logger.info("Monitor started")

    def stop(self):
        """Stop the background monitoring thread."""
        with self.lock:
            self.running = False
            logger.info("Monitor stopped")

    def update_config(self, interval_seconds, notify_on_available, watchers):
        """Update monitoring configuration."""
        with self.lock:
            self.interval_seconds = interval_seconds
            self.notify_on_available = notify_on_available
            self.watchers = [clean_watcher(item) for item in watchers]
            self.check_dates = _union_watcher_dates(self.watchers)

    def apply_config(self, config):
        """Apply configuration from config dict."""
        monitor_config = config.get("monitor", {})
        with self.lock:
            self.interval_seconds = int(
                monitor_config.get("interval_seconds", self.interval_seconds)
            )
            self.notify_on_available = bool(
                monitor_config.get("notify_on_available", self.notify_on_available)
            )
            self.watchers = [
                clean_watcher(item) for item in (config.get("watchers") or [])
            ]
            self.check_dates = _union_watcher_dates(self.watchers)

    def snapshot(self):
        """Take thread-safe snapshot of current state.

        Returns:
            dict: Current state snapshot with running status, configuration,
                  and recent results.
        """
        with self.lock:
            return {
                "running": self.running,
                "interval_seconds": self.interval_seconds,
                "check_dates": list(self.check_dates),
                "watchers": [dict(item) for item in self.watchers],
                "notify_on_available": self.notify_on_available,
                "last_checked_at": self.last_checked_at,
                "last_available_num": self.last_available_num,
                "last_available_list": list(self.last_available_list),
                "last_available_branches": list(self.last_available_branches),
                "last_eai_code": self.last_eai_code,
                "last_error": self.last_error,
                "history": list(self.history),
            }

    def _loop(self):
        """Background monitoring loop that runs in daemon thread."""
        while True:
            with self.lock:
                if not self.running:
                    break
                interval_seconds = self.interval_seconds
                notify_on_available = self.notify_on_available
                watchers = [dict(item) for item in self.watchers]

            try:
                res_json = get_jsonAvailableDateAndTime()
                logger.info(res_json)

                total_available_num, total_available_list = parse(res_json, ["all"])
                eai_code = res_json.get("eaiCode")
                checked_at = _now_str()

                district_availability = enrich_availability_with_details(
                    collect_district_availability(watchers, total_available_list)
                )
                slots = flatten_available_slots(district_availability)
                remarks = log_monitor_cycle(
                    total_available_num, total_available_list, slots
                )
                branch_labels = [
                    part.strip()
                    for part in (remarks or "").split(",")
                    if part.strip() and part.strip() != "-"
                ]
                display_num = cycle_available_count(total_available_num, slots)

                with self.lock:
                    self.last_checked_at = checked_at
                    self.last_available_num = display_num
                    self.last_available_list = list(total_available_list)
                    self.last_available_branches = list(branch_labels)
                    self.last_eai_code = eai_code
                    self.last_error = None
                    self._append_history(
                        {
                            "checked_at": checked_at,
                            "available_num": display_num,
                            "available_list": list(total_available_list),
                            "available_branches": list(branch_labels),
                            "remarks": remarks if remarks != "-" else None,
                            "eai_code": eai_code,
                            "error": None,
                        }
                    )

                if notify_on_available:
                    notify_watchers(
                        watchers,
                        total_available_list,
                        district_availability,
                        notify=True,
                    )

            except Exception as exc:  # pragma: no cover - defensive logging
                checked_at = _now_str()
                error_text = str(exc)
                with self.lock:
                    self.last_checked_at = checked_at
                    self.last_error = error_text
                    self._append_history(
                        {
                            "checked_at": checked_at,
                            "available_num": None,
                            "available_list": [],
                            "available_branches": [],
                            "remarks": None,
                            "eai_code": None,
                            "error": error_text,
                        }
                    )
                logger.error(f"Monitoring error: {error_text}")

            time.sleep(interval_seconds)

    def _append_history(self, entry):
        """Append entry to history, maintaining size limit.

        Args:
            entry (dict): History entry with check results.
        """
        self.history.append(entry)
        if len(self.history) > self.history_limit:
            self.history = self.history[-self.history_limit :]


def register_routes(app, monitor_state):
    """Register Flask routes with the application.

    Args:
        app (Flask): Flask application instance.
        monitor_state (MonitorState): Shared monitor state object.
    """

    @app.route("/favicon.ico")
    def favicon():
        """Serve favicon.ico."""
        return app.send_static_file("favicon.ico")

    @app.route("/")
    def index():
        """Display main monitoring dashboard."""
        state = monitor_state.snapshot()
        config = load_config()
        email_config = config.get("email", {})
        mail_port = email_config.get("mail_port")
        email_view = {
            "mail_host": email_config.get("mail_host", ""),
            "mail_port": mail_port if mail_port not in (None, "") else "",
            "mail_user": email_config.get("mail_user", ""),
            "mail_pass": email_config.get("mail_pass", ""),
            "sender": email_config.get("sender", ""),
        }
        return render_template(
            "index.html",
            state=state,
            email=email_view,
            watchers=config.get("watchers") or [],
            districts=peek_districts(),
            persistence=get_persistence_info(),
        )

    @app.route("/history")
    def history():
        """Display monitoring history in reverse chronological order."""
        # Read from logs to show full history
        full_history = read_history_from_logs()
        return render_template("history.html", history=full_history[::-1])

    @app.route("/config", methods=["POST"])
    def update_config():
        """Update monitor and email configuration from form submission."""
        interval_raw = request.form.get("interval_seconds", "60")
        notify_on_available = request.form.get("notify_on_available") == "on"
        mail_host = request.form.get("mail_host", "")
        mail_port_raw = request.form.get("mail_port", "")
        mail_user = request.form.get("mail_user", "")
        mail_pass = request.form.get("mail_pass", "")
        sender = request.form.get("sender", "")
        watchers = parse_watchers_form(request)
        if watchers is None:
            flash("关注人配置无效，未保存。请刷新页面后重试。", "error")
            return redirect(url_for("index"))
        interval_seconds = parse_interval_input(interval_raw)

        mail_port = None
        if mail_port_raw and mail_port_raw.strip().isdigit():
            mail_port = int(mail_port_raw.strip())

        config = load_config()
        config["watchers"] = watchers
        config["monitor"] = {
            "check_dates": _union_watcher_dates(watchers),
            "interval_seconds": interval_seconds,
            "notify_on_available": notify_on_available,
        }
        config["email"] = {
            "mail_host": mail_host.strip(),
            "mail_port": mail_port,
            "mail_user": mail_user.strip(),
            "mail_pass": mail_pass.strip(),
            "sender": sender.strip(),
            "receivers": [item["email"] for item in watchers],
        }
        try:
            save_config(config)
        except OSError as exc:
            flash("配置保存失败：{error}".format(error=exc), "error")
            return redirect(url_for("index"))

        monitor_state.update_config(interval_seconds, notify_on_available, watchers)
        saved_path = get_persistence_info()["config_path"]
        flash("配置已保存到 {path}，刷新后仍会保留。".format(path=saved_path), "success")
        return redirect(url_for("index"))

    @app.route("/test-email", methods=["POST"])
    def test_email():
        """Send test email to verify email configuration."""
        ok = send_email("测试邮件", "这是一封测试邮件。")
        if ok:
            flash("测试邮件发送成功", "success")
        else:
            flash("测试邮件发送失败，请检查邮箱配置", "error")
        return redirect(url_for("index"))

    @app.route("/api/next-7-days", methods=["GET"])
    def get_next_7_days():
        """API endpoint returning next 7 days in YYYYMMDD format."""
        today = _now()
        dates = []
        for i in range(7):
            future_date = today + timedelta(days=i)
            date_str = future_date.strftime("%Y%m%d")
            dates.append(date_str)
        return jsonify({"dates": dates})

    @app.route("/api/districts", methods=["GET"])
    def api_districts():
        """Return BOCHK district list for the watcher form."""
        return jsonify({"districts": get_districts()})

    @app.route("/api/branches", methods=["GET"])
    def api_branches():
        """Return branches for one district."""
        district = (request.args.get("district") or "").strip()
        return jsonify({"district": district, "branches": get_branches(district)})

    @app.route("/start", methods=["POST"])
    def start_monitor():
        """Start background monitoring."""
        monitor_state.start()
        return redirect(url_for("index"))

    @app.route("/stop", methods=["POST"])
    def stop_monitor():
        """Stop background monitoring."""
        monitor_state.stop()
        return redirect(url_for("index"))


def _union_watcher_dates(watchers):
    """Collect unique dates from watchers; empty means at least one person watches any date."""
    dates = []
    for watcher in watchers:
        cleaned = clean_watcher(watcher)
        for date in cleaned["dates"]:
            if date not in dates:
                dates.append(date)
    return dates


def parse_watchers_form(request):
    """Parse watchers from watchers_json, grouped fields, or legacy receivers.

    Returns a list of watchers, or None when watchers_json is present but unusable
    so the caller can refuse to overwrite saved people.
    """
    if "watchers_json" in request.form:
        raw = (request.form.get("watchers_json") or "").strip()
        if not raw:
            return None
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(loaded, list):
            return None
        cleaned = []
        for item in loaded:
            watcher = clean_watcher(item)
            if watcher["email"]:
                cleaned.append(watcher)
        return cleaned
    items = []
    emails = request.form.getlist("email[]")
    dates_list = request.form.getlist("dates[]")
    districts_list = request.form.getlist("districts[]")
    branches_list = request.form.getlist("branch_codes[]")
    for index, email in enumerate(emails):
        items.append(
            {
                "email": email,
                "dates": dates_list[index] if index < len(dates_list) else "",
                "districts": districts_list[index] if index < len(districts_list) else "",
                "branch_codes": branches_list[index] if index < len(branches_list) else "",
            }
        )
    if not items:
        receivers = parse_dates_input(request.form.get("receivers", ""))
        check_dates = parse_dates_input(request.form.get("check_dates", ""))
        if request.form.get("monitor_all") == "on" and not check_dates:
            check_dates = []
        for email in receivers:
            items.append(
                {
                    "email": email,
                    "dates": list(check_dates),
                    "districts": [],
                    "branch_codes": [],
                }
            )
    cleaned = []
    for item in items:
        watcher = clean_watcher(item)
        if watcher["email"]:
            cleaned.append(watcher)
    return cleaned


def parse_dates_input(value):
    """Parse comma/newline-separated date input into list.

    Args:
        value (str): Raw input string with comma or newline separators.

    Returns:
        list: Cleaned list of non-empty items.
    """
    items = [item.strip() for item in (value or "").replace("\n", ",").split(",")]
    return [item for item in items if item]


def parse_interval_input(value):
    """Parse and validate interval input.

    Args:
        value (str): Interval string (should be convertible to int).

    Returns:
        int: Interval in seconds, minimum 10, default 60.
    """
    try:
        interval_seconds = int(value)
    except ValueError:
        return 60
    return max(10, interval_seconds)


# Create app instance for import by entry points
app, monitor_state = create_app()

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")

    # In production, gunicorn will handle the web server
    # This block is for local development only
    monitor_state.start()
    app.run(host=host, port=port, debug=False)

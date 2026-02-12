"""Flask web application for BOCHK appointment monitoring.

This module provides a web interface for monitoring BOCHK appointment availability,
managing monitor configuration, and viewing monitoring history.
"""

import glob
from datetime import datetime, timedelta

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_basicauth import BasicAuth

from .config import load_config, save_config
from .logger import logger, read_history_from_logs
from .monitor import get_jsonAvailableDateAndTime, parse
from .send_email import send_email


import os
import threading
import time


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
        self.check_dates = list(
            monitor_config.get("check_dates", ["20260213", "20260214", "20260215"])
        )
        self.notify_on_available = bool(
            monitor_config.get("notify_on_available", True)
        )
        self.last_checked_at = None
        self.last_available_num = 0
        self.last_available_list = []
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

    def update_config(self, check_dates, interval_seconds, notify_on_available):
        """Update monitoring configuration.

        Args:
            check_dates (list): New dates to check.
            interval_seconds (int): New polling interval in seconds.
            notify_on_available (bool): Whether to send email on availability.
        """
        with self.lock:
            self.check_dates = check_dates
            self.interval_seconds = interval_seconds
            self.notify_on_available = notify_on_available

    def apply_config(self, config):
        """Apply configuration from config dict.

        Args:
            config (dict): Configuration dictionary.
        """
        monitor_config = config.get("monitor", {})
        with self.lock:
            self.check_dates = list(
                monitor_config.get("check_dates", self.check_dates)
            )
            self.interval_seconds = int(
                monitor_config.get("interval_seconds", self.interval_seconds)
            )
            self.notify_on_available = bool(
                monitor_config.get("notify_on_available", self.notify_on_available)
            )

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
                "notify_on_available": self.notify_on_available,
                "last_checked_at": self.last_checked_at,
                "last_available_num": self.last_available_num,
                "last_available_list": list(self.last_available_list),
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
                check_dates = list(self.check_dates)
                notify_on_available = self.notify_on_available

            try:
                res_json = get_jsonAvailableDateAndTime()
                # Log raw response for analysis
                logger.info(res_json)
                
                # Use "all" to get all available dates for history/logging
                total_available_num, total_available_list = parse(res_json, ["all"])
                eai_code = res_json.get("eaiCode")
                checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Log the cycle summary for history parsing
                logger.info(f"Monitor cycle: {total_available_num} available dates: {total_available_list}")

                # Determine which dates trigger notification
                if "all" in check_dates:
                    notify_list = total_available_list
                else:
                    # Filter: only dates that are in check_dates
                    notify_list = [d for d in total_available_list if d in check_dates]

                with self.lock:
                    self.last_checked_at = checked_at
                    self.last_available_num = total_available_num
                    self.last_available_list = list(total_available_list)
                    self.last_eai_code = eai_code
                    self.last_error = None
                    self._append_history(
                        {
                            "checked_at": checked_at,
                            "available_num": total_available_num,
                            "available_list": list(total_available_list),
                            "eai_code": eai_code,
                            "error": None,
                        }
                    )

                if len(notify_list) > 0 and notify_on_available:
                    send_email(
                        "BOCHK appointment available",
                        "Available dates matching your criteria: {dates}".format(
                            dates=", ".join(notify_list)
                        ),
                    )
                    logger.info(f"Email notification sent for dates: {notify_list}")

            except Exception as exc:  # pragma: no cover - defensive logging
                checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                error_text = str(exc)
                with self.lock:
                    self.last_checked_at = checked_at
                    self.last_error = error_text
                    self._append_history(
                        {
                            "checked_at": checked_at,
                            "available_num": None,
                            "available_list": [],
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
        email_view = {
            "mail_host": email_config.get("mail_host", ""),
            "mail_user": email_config.get("mail_user", ""),
            "mail_pass": email_config.get("mail_pass", ""),
            "sender": email_config.get("sender", ""),
            "receivers": ",".join(email_config.get("receivers", [])),
        }
        return render_template("index.html", state=state, email=email_view)

    @app.route("/history")
    def history():
        """Display monitoring history in reverse chronological order."""
        # Read from logs to show full history
        full_history = read_history_from_logs()
        return render_template("history.html", history=full_history[::-1])

    @app.route("/config", methods=["POST"])
    def update_config():
        """Update monitor and email configuration from form submission."""
        monitor_all = request.form.get("monitor_all") == "on"
        check_dates_raw = request.form.get("check_dates", "")
        interval_raw = request.form.get("interval_seconds", "60")
        notify_on_available = request.form.get("notify_on_available") == "on"
        mail_host = request.form.get("mail_host", "")
        mail_port_raw = request.form.get("mail_port", "")
        mail_user = request.form.get("mail_user", "")
        mail_pass = request.form.get("mail_pass", "")
        sender = request.form.get("sender", "")
        receivers_raw = request.form.get("receivers", "")

        # Handle monitor_all mode
        # Priority: If user entered specific dates, use them. 
        # Otherwise if "Monitor All" is checked, use ["all"].
        check_dates = parse_dates_input(check_dates_raw)
        
        if not check_dates and monitor_all:
             check_dates = ["all"]

        interval_seconds = parse_interval_input(interval_raw)
        receivers = parse_dates_input(receivers_raw)

        # Parse mail_port (None if empty, otherwise int)
        mail_port = None
        if mail_port_raw and mail_port_raw.strip().isdigit():
            mail_port = int(mail_port_raw.strip())

        config = load_config()
        config["monitor"] = {
            "check_dates": check_dates,
            "interval_seconds": interval_seconds,
            "notify_on_available": notify_on_available,
        }
        config["email"] = {
            "mail_host": mail_host.strip(),
            "mail_port": mail_port,
            "mail_user": mail_user.strip(),
            "mail_pass": mail_pass.strip(),
            "sender": sender.strip(),
            "receivers": receivers,
        }
        save_config(config)

        monitor_state.update_config(
            check_dates, interval_seconds, notify_on_available
        )
        flash("配置已保存", "success")
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
        today = datetime.now()
        dates = []
        for i in range(7):
            future_date = today + timedelta(days=i)
            date_str = future_date.strftime("%Y%m%d")
            dates.append(date_str)
        return jsonify({"dates": dates})

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


def parse_dates_input(value):
    """Parse comma/newline-separated date input into list.

    Args:
        value (str): Raw input string with comma or newline separators.

    Returns:
        list: Cleaned list of non-empty items.
    """
    items = [item.strip() for item in value.replace("\n", ",").split(",")]
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

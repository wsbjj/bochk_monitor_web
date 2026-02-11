import threading
import time
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, url_for

from Send_email import send_email
from config_store import load_config, save_config
from log import logger
from main import get_jsonAvailableDateAndTime, parse

app = Flask(__name__)
app.secret_key = "bochk-monitor"


class MonitorState:
    def __init__(self, config):
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
        with self.lock:
            if self.running:
                return
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

    def stop(self):
        with self.lock:
            self.running = False

    def update_config(self, check_dates, interval_seconds, notify_on_available):
        with self.lock:
            self.check_dates = check_dates
            self.interval_seconds = interval_seconds
            self.notify_on_available = notify_on_available

    def apply_config(self, config):
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
        while True:
            with self.lock:
                if not self.running:
                    break
                interval_seconds = self.interval_seconds
                check_dates = list(self.check_dates)
                notify_on_available = self.notify_on_available

            try:
                res_json = get_jsonAvailableDateAndTime()
                available_num, available_list = parse(res_json, check_dates)
                eai_code = res_json.get("eaiCode")
                checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                with self.lock:
                    self.last_checked_at = checked_at
                    self.last_available_num = available_num
                    self.last_available_list = list(available_list)
                    self.last_eai_code = eai_code
                    self.last_error = None
                    self._append_history(
                        {
                            "checked_at": checked_at,
                            "available_num": available_num,
                            "available_list": list(available_list),
                            "eai_code": eai_code,
                            "error": None,
                        }
                    )

                if available_num > 0 and notify_on_available:
                    send_email(
                        "BOCHK appointment available",
                        "Available dates: {dates}".format(
                            dates=", ".join(available_list)
                        ),
                    )
                    logger.info("Email notification sent")
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
                logger.error(error_text)

            time.sleep(interval_seconds)

    def _append_history(self, entry):
        self.history.append(entry)
        if len(self.history) > self.history_limit:
            self.history = self.history[-self.history_limit :]


monitor_state = MonitorState(load_config())



@app.route("/")
def index():
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
    state = monitor_state.snapshot()
    return render_template("history.html", history=state["history"][::-1])


@app.route("/config", methods=["POST"])
def update_config():
    check_dates_raw = request.form.get("check_dates", "")
    interval_raw = request.form.get("interval_seconds", "60")
    notify_on_available = request.form.get("notify_on_available") == "on"
    mail_host = request.form.get("mail_host", "")
    mail_user = request.form.get("mail_user", "")
    mail_pass = request.form.get("mail_pass", "")
    sender = request.form.get("sender", "")
    receivers_raw = request.form.get("receivers", "")

    check_dates = parse_dates_input(check_dates_raw)
    interval_seconds = parse_interval_input(interval_raw)
    receivers = parse_dates_input(receivers_raw)

    config = load_config()
    config["monitor"] = {
        "check_dates": check_dates,
        "interval_seconds": interval_seconds,
        "notify_on_available": notify_on_available,
    }
    config["email"] = {
        "mail_host": mail_host.strip(),
        "mail_user": mail_user.strip(),
        "mail_pass": mail_pass.strip(),
        "sender": sender.strip(),
        "receivers": receivers,
    }
    save_config(config)

    monitor_state.update_config(check_dates, interval_seconds, notify_on_available)
    flash("配置已保存", "success")
    return redirect(url_for("index"))


@app.route("/test-email", methods=["POST"])
def test_email():
    ok = send_email("测试邮件", "这是一封测试邮件。")
    if ok:
      flash("测试邮件发送成功", "success")
    else:
      flash("测试邮件发送失败，请检查邮箱配置", "error")
    return redirect(url_for("index"))


@app.route("/start", methods=["POST"])
def start_monitor():
    monitor_state.start()
    return redirect(url_for("index"))


@app.route("/stop", methods=["POST"])
def stop_monitor():
    monitor_state.stop()
    return redirect(url_for("index"))


def parse_dates_input(value):
    items = [item.strip() for item in value.replace("\n", ",").split(",")]
    return [item for item in items if item]


def parse_interval_input(value):
    try:
        interval_seconds = int(value)
    except ValueError:
        return 60
    return max(10, interval_seconds)


if __name__ == "__main__":
    monitor_state.start()
    app.run(host="127.0.0.1", port=5000, debug=False)

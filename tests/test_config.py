"""Tests for config persistence: Web UI saves must survive refresh on Railway."""
import json
import os
import tempfile
import unittest
from unittest import mock

from src.config import (
    get_data_dir,
    get_persistence_info,
    load_config,
    save_config,
)


ENV_KEYS = [
    "DATA_DIR",
    "RAILWAY_VOLUME_MOUNT_PATH",
    "MAIL_HOST",
    "MAIL_PORT",
    "MAIL_USER",
    "MAIL_PASS",
    "SENDER",
    "RECEIVERS",
    "MONITOR_ALL_DATES",
    "MONITOR_CHECK_DATES",
    "MONITOR_INTERVAL_SECONDS",
    "MONITOR_NOTIFY_ON_AVAILABLE",
]


class ConfigPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env_patch = mock.patch.dict(
            os.environ,
            {
                "DATA_DIR": self.tmp.name,
                "MAIL_HOST": "smtp.qq.com",
                "MAIL_PORT": "465",
                "MAIL_USER": "env-user@qq.com",
                "MAIL_PASS": "env-pass",
                "SENDER": "env-user@qq.com",
                "RECEIVERS": "env-receiver@qq.com",
                "MONITOR_ALL_DATES": "true",
                "MONITOR_INTERVAL_SECONDS": "120",
                "MONITOR_NOTIFY_ON_AVAILABLE": "true",
            },
            clear=False,
        )
        self.env_patch.start()
        for key in ("RAILWAY_VOLUME_MOUNT_PATH", "MONITOR_CHECK_DATES"):
            os.environ.pop(key, None)

    def tearDown(self):
        self.env_patch.stop()
        self.tmp.cleanup()

    def _write_file_config(self, payload):
        path = os.path.join(self.tmp.name, "config.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)

    def test_env_used_when_no_config_file(self):
        config = load_config()
        self.assertEqual(config["email"]["mail_host"], "smtp.qq.com")
        self.assertEqual(config["email"]["mail_user"], "env-user@qq.com")
        self.assertEqual(config["email"]["receivers"], ["env-receiver@qq.com"])
        self.assertEqual(config["watchers"][0]["email"], "env-receiver@qq.com")
        self.assertEqual(config["watchers"][0]["dates"], [])
        self.assertEqual(config["watchers"][0]["districts"], [])
        self.assertEqual(config["monitor"]["check_dates"], ["all"])
        self.assertEqual(config["monitor"]["interval_seconds"], 120)

    def test_saved_file_overrides_environment_email(self):
        self._write_file_config(
            {
                "monitor": {
                    "check_dates": ["20260903"],
                    "interval_seconds": 60,
                    "notify_on_available": True,
                },
                "email": {
                    "mail_host": "smtp.163.com",
                    "mail_port": None,
                    "mail_user": "junjie18319266271@163.com",
                    "mail_pass": "file-pass",
                    "sender": "junjie18319266271@163.com",
                    "receivers": ["2801011889@qq.com"],
                },
            }
        )

        config = load_config()

        self.assertEqual(config["email"]["mail_host"], "smtp.163.com")
        self.assertEqual(config["email"]["mail_user"], "junjie18319266271@163.com")
        self.assertEqual(config["email"]["sender"], "junjie18319266271@163.com")
        self.assertEqual(config["email"]["receivers"], ["2801011889@qq.com"])
        self.assertEqual(config["email"]["mail_pass"], "file-pass")
        self.assertEqual(config["email"]["mail_port"], None)
        self.assertEqual(config["monitor"]["check_dates"], ["20260903"])
        self.assertEqual(config["monitor"]["interval_seconds"], 60)
        self.assertEqual(config["watchers"][0]["email"], "2801011889@qq.com")
        self.assertEqual(config["watchers"][0]["dates"], ["20260903"])
        self.assertEqual(config["watchers"][0]["districts"], [])
        self.assertEqual(config["watchers"][0]["branch_codes"], [])

    def test_save_then_load_keeps_web_values_despite_env(self):
        saved = {
            "monitor": {
                "check_dates": ["20260910"],
                "interval_seconds": 45,
                "notify_on_available": False,
            },
            "email": {
                "mail_host": "smtp.gmail.com",
                "mail_port": 587,
                "mail_user": "web@gmail.com",
                "mail_pass": "web-pass",
                "sender": "web@gmail.com",
                "receivers": ["alert@example.com"],
            },
        }

        save_config(saved)
        loaded = load_config()

        self.assertEqual(loaded["email"]["mail_host"], "smtp.gmail.com")
        self.assertEqual(loaded["email"]["mail_user"], "web@gmail.com")
        self.assertEqual(loaded["email"]["mail_port"], 587)
        self.assertEqual(loaded["email"]["receivers"], ["alert@example.com"])
        self.assertEqual(loaded["monitor"]["interval_seconds"], 45)
        self.assertFalse(loaded["monitor"]["notify_on_available"])
        self.assertEqual(loaded["watchers"][0]["email"], "alert@example.com")
        self.assertEqual(loaded["watchers"][0]["dates"], ["20260910"])

    def test_get_data_dir_uses_data_dir_env(self):
        self.assertEqual(get_data_dir(), self.tmp.name)

    def test_get_data_dir_uses_railway_volume_mount(self):
        os.environ.pop("DATA_DIR", None)
        mount = os.path.join(self.tmp.name, "volume")
        os.makedirs(mount, exist_ok=True)
        os.environ["RAILWAY_VOLUME_MOUNT_PATH"] = mount
        self.assertEqual(get_data_dir(), mount)

    def test_persistence_info_reports_file_source_when_saved(self):
        save_config(
            {
                "monitor": {"check_dates": ["all"], "interval_seconds": 60, "notify_on_available": True},
                "email": {
                    "mail_host": "smtp.163.com",
                    "mail_user": "a@163.com",
                    "mail_pass": "x",
                    "sender": "a@163.com",
                    "receivers": ["b@qq.com"],
                },
            }
        )
        info = get_persistence_info()
        self.assertTrue(info["config_exists"])
        self.assertEqual(info["source"], "file")
        self.assertEqual(info["data_dir"], self.tmp.name)
        self.assertTrue(info["config_path"].endswith("config.json"))
        self.assertTrue(info["persistent"])

    def test_corrupt_file_keeps_last_good_instead_of_env(self):
        saved = {
            "monitor": {
                "check_dates": ["20260910"],
                "interval_seconds": 45,
                "notify_on_available": False,
            },
            "email": {
                "mail_host": "smtp.gmail.com",
                "mail_port": 587,
                "mail_user": "web@gmail.com",
                "mail_pass": "web-pass",
                "sender": "web@gmail.com",
                "receivers": ["alert@example.com"],
            },
        }
        save_config(saved)
        self.assertEqual(load_config()["email"]["mail_user"], "web@gmail.com")

        path = os.path.join(self.tmp.name, "config.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{not-json")

        loaded = load_config()
        self.assertEqual(loaded["email"]["mail_user"], "env-user@qq.com")
        info = get_persistence_info()
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(info["source"], "file")

    def test_save_is_atomic_and_readable(self):
        save_config(
            {
                "monitor": {"check_dates": ["all"], "interval_seconds": 60, "notify_on_available": True},
                "email": {
                    "mail_host": "smtp.163.com",
                    "mail_port": None,
                    "mail_user": "a@163.com",
                    "mail_pass": "x",
                    "sender": "a@163.com",
                    "receivers": ["b@qq.com"],
                },
            }
        )
        path = os.path.join(self.tmp.name, "config.json")
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertEqual(payload.get("email", {}).get("mail_port"), None)
        leftover = [
            name for name in os.listdir(self.tmp.name)
            if name.startswith(".config.") and name.endswith(".tmp")
        ]
        self.assertEqual(leftover, [])

    def test_prefers_candidate_dir_that_already_has_config(self):
        os.environ.pop("DATA_DIR", None)
        empty_mount = os.path.join(self.tmp.name, "empty-mount")
        filled_dir = os.path.join(self.tmp.name, "filled")
        os.makedirs(empty_mount, exist_ok=True)
        os.makedirs(filled_dir, exist_ok=True)
        with open(os.path.join(filled_dir, "config.json"), "w", encoding="utf-8") as handle:
            json.dump({"email": {"mail_user": "from-old-volume@163.com"}}, handle)
        os.environ["DATA_DIR"] = empty_mount
        os.environ["RAILWAY_VOLUME_MOUNT_PATH"] = filled_dir
        self.assertEqual(get_data_dir(), empty_mount)


class ConfigFormRoundtripTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env_patch = mock.patch.dict(
            os.environ,
            {
                "DATA_DIR": self.tmp.name,
                "ADMIN_USERNAME": "admin",
                "ADMIN_PASSWORD": "secret",
                "FLASK_SECRET_KEY": "test-secret",
                "MAIL_HOST": "smtp.qq.com",
                "MAIL_USER": "env-user@qq.com",
                "MAIL_PASS": "env-pass",
                "SENDER": "env-user@qq.com",
                "RECEIVERS": "env-receiver@qq.com",
            },
            clear=False,
        )
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.tmp.cleanup()

    def test_post_config_then_get_shows_saved_email(self):
        from src.app import create_app

        app, _state = create_app()
        client = app.test_client()
        auth = ("admin", "secret")

        response = client.post(
            "/config",
            data={
                "interval_seconds": "60",
                "notify_on_available": "on",
                "mail_host": "smtp.163.com",
                "mail_port": "",
                "mail_user": "junjie18319266271@163.com",
                "mail_pass": "web-auth-code",
                "sender": "junjie18319266271@163.com",
                "watchers_json": json.dumps(
                    [
                        {
                            "email": "2801011889@qq.com",
                            "dates": ["20260903"],
                            "districts": ["_yuen_long_district_F"],
                            "branch_codes": [],
                        }
                    ]
                ),
            },
            auth=auth,
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("关注人列表", body)
        self.assertIn("监控方式", body)
        self.assertIn("2801011889@qq.com", body)
        self.assertIn("_yuen_long_district_F", body)
        self.assertNotIn("env-user@qq.com", body)
        self.assertIn("smtp.163.com", body)

        reload_response = client.get("/", auth=auth)
        reload_body = reload_response.get_data(as_text=True)
        self.assertIn("junjie18319266271@163.com", reload_body)
        self.assertIn("2801011889@qq.com", reload_body)
        self.assertNotIn("env-user@qq.com", reload_body)

    def test_invalid_watchers_json_does_not_wipe_saved_people(self):
        from src.app import create_app

        app, _state = create_app()
        client = app.test_client()
        auth = ("admin", "secret")
        client.post(
            "/config",
            data={
                "interval_seconds": "60",
                "notify_on_available": "on",
                "mail_host": "smtp.163.com",
                "mail_user": "junjie18319266271@163.com",
                "mail_pass": "web-auth-code",
                "sender": "junjie18319266271@163.com",
                "watchers_json": json.dumps(
                    [
                        {
                            "email": "keep@qq.com",
                            "dates": ["20260903"],
                            "districts": [],
                            "branch_codes": [],
                        }
                    ]
                ),
            },
            auth=auth,
        )
        response = client.post(
            "/config",
            data={
                "interval_seconds": "60",
                "notify_on_available": "on",
                "mail_host": "smtp.163.com",
                "mail_user": "junjie18319266271@163.com",
                "mail_pass": "web-auth-code",
                "sender": "junjie18319266271@163.com",
                "watchers_json": "{not-json",
            },
            auth=auth,
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("关注人配置无效", response.get_data(as_text=True))
        loaded = load_config()
        self.assertEqual(loaded["watchers"][0]["email"], "keep@qq.com")


if __name__ == "__main__":
    unittest.main()

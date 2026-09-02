"""Tests for watcher migration, matching, and per-recipient email."""
import os
import tempfile
import unittest
from unittest import mock

from src.monitor import parse_available_dates, parse_branch_list, parse_district_list
from src.send_email import send_email
from src.watchers import match_watcher, normalize_watchers


class WatcherMigrationTests(unittest.TestCase):
    def test_legacy_receivers_and_check_dates_become_watchers(self):
        config = normalize_watchers(
            {
                "monitor": {
                    "check_dates": ["20260903", "20260910"],
                    "interval_seconds": 60,
                    "notify_on_available": True,
                },
                "email": {
                    "receivers": ["a@qq.com", "b@qq.com"],
                },
            }
        )
        self.assertEqual(
            config["watchers"],
            [
                {
                    "email": "a@qq.com",
                    "dates": ["20260903", "20260910"],
                    "districts": [],
                    "branch_codes": [],
                },
                {
                    "email": "b@qq.com",
                    "dates": ["20260903", "20260910"],
                    "districts": [],
                    "branch_codes": [],
                },
            ],
        )
        self.assertEqual(config["email"]["receivers"], ["a@qq.com", "b@qq.com"])

    def test_monitor_all_migrates_to_empty_dates(self):
        config = normalize_watchers(
            {
                "monitor": {"check_dates": ["all"]},
                "email": {"receivers": ["a@qq.com"]},
            }
        )
        self.assertEqual(config["watchers"][0]["dates"], [])

    def test_string_receivers_split_on_comma_not_characters(self):
        config = normalize_watchers(
            {
                "monitor": {"check_dates": ["20260903"]},
                "email": {"receivers": "a@qq.com,b@qq.com"},
            }
        )
        self.assertEqual(
            [item["email"] for item in config["watchers"]],
            ["a@qq.com", "b@qq.com"],
        )

    def test_explicit_watchers_not_overwritten_by_receivers(self):
        config = normalize_watchers(
            {
                "monitor": {"check_dates": ["20260903"]},
                "email": {"receivers": ["old@qq.com"]},
                "watchers": [
                    {
                        "email": "new@qq.com",
                        "dates": ["20260910"],
                        "districts": ["_yuen_long_district_F"],
                        "branch_codes": [],
                    }
                ],
            }
        )
        self.assertEqual(len(config["watchers"]), 1)
        self.assertEqual(config["watchers"][0]["email"], "new@qq.com")
        self.assertEqual(config["email"]["receivers"], ["new@qq.com"])


class WatcherMatchTests(unittest.TestCase):
    def test_date_only_match(self):
        watcher = {
            "email": "a@qq.com",
            "dates": ["20260903"],
            "districts": [],
            "branch_codes": [],
        }
        hits = match_watcher(
            watcher,
            ["20260903", "20260904"],
            {},
        )
        self.assertEqual([hit["date"] for hit in hits], ["20260903"])
        self.assertIsNone(hits[0]["district"])

    def test_district_any_branch_match(self):
        watcher = {
            "email": "a@qq.com",
            "dates": [],
            "districts": ["_yuen_long_district_F"],
            "branch_codes": [],
        }
        hits = match_watcher(
            watcher,
            ["20260999"],
            {
                "_yuen_long_district_F": [
                    {
                        "code": "YL01",
                        "name": "元朗分行",
                        "district_name": "元朗区",
                        "dates": ["20260903"],
                    }
                ]
            },
        )
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["date"], "20260903")
        self.assertEqual(hits[0]["district"], "_yuen_long_district_F")
        self.assertEqual(hits[0]["branch_name"], "元朗分行")

    def test_district_and_branch_filter(self):
        watcher = {
            "email": "b@qq.com",
            "dates": ["20260910"],
            "districts": ["_tsuen_wan_district_F"],
            "branch_codes": ["TW01"],
        }
        availability = {
            "_tsuen_wan_district_F": [
                {
                    "code": "TW01",
                    "name": "荃湾分行",
                    "district_name": "荃湾区",
                    "dates": ["20260910", "20260911"],
                },
                {
                    "code": "TW02",
                    "name": "其它分行",
                    "district_name": "荃湾区",
                    "dates": ["20260910"],
                },
            ]
        }
        hits = match_watcher(watcher, ["20260910"], availability)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["branch_code"], "TW01")
        self.assertEqual(hits[0]["date"], "20260910")


class BochkParseTests(unittest.TestCase):
    def test_parse_district_list_keeps_f_suffix(self):
        items = parse_district_list(
            {
                "branchDistrictList": [
                    {"value": "", "messageCn": "请选择"},
                    {
                        "value": "_yuen_long_district_F",
                        "messageCn": "元朗区",
                        "message": "Yuen Long",
                    },
                ]
            }
        )
        self.assertEqual(
            items,
            [{"value": "_yuen_long_district_F", "name": "元朗区"}],
        )

    def test_parse_branch_list_skips_placeholder(self):
        items = parse_branch_list(
            {
                "availableBranchList": [
                    {"value": "", "messageCn": "请选择"},
                    {"value": "YL01", "messageCn": "元朗分行"},
                ]
            }
        )
        self.assertEqual(items, [{"code": "YL01", "name": "元朗分行"}])

    def test_parse_available_dates_from_quota_and_beans(self):
        dates = parse_available_dates(
            {
                "dateQuota": {"20260903": "A", "20260904": "F"},
                "bookableDetailBeans": [{"appDate": "10/09/2026"}],
            }
        )
        self.assertEqual(dates, ["20260903", "20260910"])


class SendEmailRecipientTests(unittest.TestCase):
    @mock.patch("src.send_email.smtplib.SMTP_SSL")
    @mock.patch("src.send_email.load_config")
    def test_to_sends_only_to_specified_person(self, mock_load, mock_smtp):
        mock_load.return_value = {
            "email": {
                "mail_host": "smtp.163.com",
                "mail_port": 465,
                "mail_user": "a@163.com",
                "mail_pass": "pass",
                "sender": "a@163.com",
                "receivers": ["one@qq.com", "two@qq.com"],
            }
        }
        smtp_client = mock.MagicMock()
        mock_smtp.return_value = smtp_client

        ok = send_email("中银香港可预约", "有号", to=["only@qq.com"])

        self.assertTrue(ok)
        args = smtp_client.sendmail.call_args[0]
        self.assertEqual(args[0], "a@163.com")
        self.assertEqual(args[1], ["only@qq.com"])
        self.assertNotIn("one@qq.com", args[1])
        self.assertNotIn("two@qq.com", args[1])
        self.assertIn("To: only@qq.com", args[2])
        self.assertNotIn("two@qq.com", args[2])


class CollectAvailabilityTests(unittest.TestCase):
    @mock.patch("src.monitor.get_branch_available_dates")
    @mock.patch("src.monitor.get_branches")
    @mock.patch("src.monitor.get_districts")
    @mock.patch("src.monitor._fill_via_brs_by_dt")
    def test_shared_district_queried_once_and_skips_fallback(
        self, mock_fill, mock_districts, mock_branches, mock_dates
    ):
        mock_districts.return_value = [
            {"value": "_yuen_long_district_F", "name": "元朗区"}
        ]
        mock_branches.return_value = [{"code": "YL01", "name": "元朗分行"}]
        mock_dates.return_value = ["20260903"]
        watchers = [
            {
                "email": "a@qq.com",
                "dates": ["20260903"],
                "districts": ["_yuen_long_district_F"],
                "branch_codes": [],
            },
            {
                "email": "b@qq.com",
                "dates": ["20260903"],
                "districts": ["_yuen_long_district_F"],
                "branch_codes": [],
            },
        ]
        from src.monitor import collect_district_availability

        result = collect_district_availability(watchers, ["20260903"])
        mock_branches.assert_called_once_with("_yuen_long_district_F")
        mock_dates.assert_called_once_with("YL01")
        mock_fill.assert_not_called()
        self.assertEqual(result["_yuen_long_district_F"][0]["dates"], ["20260903"])


class NotifyWatchersTests(unittest.TestCase):
    @mock.patch("src.monitor.send_email")
    def test_one_email_per_person_merges_hits(self, mock_send):
        mock_send.return_value = True
        watchers = [
            {
                "email": "a@qq.com",
                "dates": ["20260903", "20260904"],
                "districts": [],
                "branch_codes": [],
            },
            {
                "email": "b@qq.com",
                "dates": ["20260999"],
                "districts": [],
                "branch_codes": [],
            },
        ]
        from src.monitor import notify_watchers

        sent = notify_watchers(
            watchers, ["20260903", "20260904"], {}, notify=True
        )
        self.assertEqual(sent, ["a@qq.com"])
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args.kwargs["to"], ["a@qq.com"])
        body = mock_send.call_args.args[1]
        self.assertIn("20260903", body)
        self.assertIn("20260904", body)

    @mock.patch("src.monitor.send_email")
    def test_duplicate_email_cards_send_once(self, mock_send):
        mock_send.return_value = True
        watchers = [
            {
                "email": "a@qq.com",
                "dates": ["20260903"],
                "districts": [],
                "branch_codes": [],
            },
            {
                "email": "a@qq.com",
                "dates": ["20260904"],
                "districts": [],
                "branch_codes": [],
            },
        ]
        from src.monitor import notify_watchers

        sent = notify_watchers(
            watchers, ["20260903", "20260904"], {}, notify=True
        )
        self.assertEqual(sent, ["a@qq.com"])
        self.assertEqual(mock_send.call_count, 1)


class ApiRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env_patch = mock.patch.dict(
            os.environ,
            {
                "ADMIN_USERNAME": "admin",
                "ADMIN_PASSWORD": "secret",
                "FLASK_SECRET_KEY": "test-secret",
                "DATA_DIR": self.tmp.name,
            },
            clear=False,
        )
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.tmp.cleanup()

    @mock.patch("src.app.get_districts")
    def test_api_districts(self, mock_districts):
        mock_districts.return_value = [
            {"value": "_yuen_long_district_F", "name": "元朗区"}
        ]
        from src.app import create_app

        app, _state = create_app()
        response = app.test_client().get("/api/districts", auth=("admin", "secret"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["districts"][0]["value"],
            "_yuen_long_district_F",
        )

    @mock.patch("src.app.get_branches")
    def test_api_branches(self, mock_branches):
        mock_branches.return_value = [{"code": "YL01", "name": "元朗分行"}]
        from src.app import create_app

        app, _state = create_app()
        response = app.test_client().get(
            "/api/branches?district=_yuen_long_district_F",
            auth=("admin", "secret"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["branches"][0]["code"], "YL01")
        mock_branches.assert_called_once_with("_yuen_long_district_F")

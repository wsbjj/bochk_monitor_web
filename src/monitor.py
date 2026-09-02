"""
BOCHK appointment monitoring module.
Core logic for checking appointment availability and sending notifications.
"""
import threading
from urllib.parse import urlencode

import requests

from .config import load_config
from .districts import FALLBACK_DISTRICTS, district_name
from .logger import logger
from .send_email import send_email
from .utils import sleep_display
from .watchers import (
    clean_watcher,
    format_branch_remarks,
    format_hits,
    match_watcher,
    unique_districts,
)


BOCHK_BASE = "https://transaction.bochk.com/whk/form/openAccount/"
BOCHK_API_URL = BOCHK_BASE + "jsonAvailableDateAndTime.action"
SUBMIT_REFERER = BOCHK_BASE + "submit.action"
CONTINUE_REFERER = BOCHK_BASE + "continueInput.action"
TIMESLOTS = ["P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08"]

BOCHK_HEADERS = {
    "Host": "transaction.bochk.com",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Origin": "https://transaction.bochk.com",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36 "
        "NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) "
        "WindowsWechat(0x63060012)"
    ),
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": CONTINUE_REFERER,
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
}

_thread_local = threading.local()
_district_cache = {"items": None}
_branch_detail_cache = {}
_cache_lock = threading.Lock()


def _get_session():
    """Return a per-thread requests session (Session is not thread-safe)."""
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        _thread_local.session = session
    return session


def _warmup_session():
    """Hit the form landing page once per thread so JSON calls can reuse cookies."""
    session = _get_session()
    if getattr(session, "_bochk_warmed", False):
        return
    try:
        response = session.get(
            BOCHK_BASE + "input.action?lang=zh_CN",
            headers={"User-Agent": BOCHK_HEADERS["User-Agent"]},
            timeout=15,
        )
        session._bochk_warmed = response.status_code == 200
    except requests.RequestException as exc:
        logger.warning("BOCHK warmup failed: %s", exc)
        session._bochk_warmed = False


def _post_json(action, payload, referer=None):
    """POST a form-urlencoded BOCHK action and return JSON, or {} on failure."""
    headers = dict(BOCHK_HEADERS)
    if referer:
        headers["Referer"] = referer
    url = BOCHK_BASE + action
    try:
        response = _get_session().post(url, headers=headers, data=payload, timeout=15)
    except requests.RequestException as exc:
        logger.warning("%s request failed: %s", action, exc)
        return {}
    if response.status_code != 200:
        logger.warning("%s HTTP %s", action, response.status_code)
        return {}
    text = (response.text or "").strip()
    if not text.startswith("{") and not text.startswith("["):
        logger.warning("%s returned non-JSON body", action)
        return {}
    try:
        data = response.json()
    except ValueError:
        logger.warning("%s JSON parse failed", action)
        return {}
    return data if isinstance(data, dict) else {}


def _get_json(action, params, referer=None):
    """GET a BOCHK JSON action and return a dict, or {} on failure."""
    headers = dict(BOCHK_HEADERS)
    headers.pop("Content-Type", None)
    if referer:
        headers["Referer"] = referer
    url = BOCHK_BASE + action
    try:
        response = _get_session().get(url, headers=headers, params=params, timeout=15)
    except requests.RequestException as exc:
        logger.warning("%s GET failed: %s", action, exc)
        return {}
    if response.status_code != 200:
        logger.warning("%s HTTP %s", action, response.status_code)
        return {}
    text = (response.text or "").strip()
    if not text.startswith("{") and not text.startswith("["):
        logger.warning("%s returned non-JSON body", action)
        return {}
    try:
        data = response.json()
    except ValueError:
        logger.warning("%s JSON parse failed", action)
        return {}
    return data if isinstance(data, dict) else {}


def get_jsonAvailableDateAndTime():
    """Fetch appointment availability data from BOCHK API."""
    payload = "bean.appDate="
    response = requests.request(
        "POST", BOCHK_API_URL, headers=BOCHK_HEADERS, data=payload, timeout=15
    )
    return response.json()


def parse_available_dates(res_json):
    """Extract YYYYMMDD dates that are not fully booked (F)."""
    if not isinstance(res_json, dict):
        return []
    dates = []
    date_quota = res_json.get("dateQuota") or {}
    if isinstance(date_quota, dict):
        for key, value in date_quota.items():
            normalized = normalize_date(key)
            if normalized and value != "F" and normalized not in dates:
                dates.append(normalized)
    date_time_quota = res_json.get("dateTimeQuota")
    if isinstance(date_time_quota, dict):
        for key, value in date_time_quota.items():
            if not value or value == "F":
                continue
            normalized = normalize_date(key)
            if normalized and normalized not in dates:
                dates.append(normalized)
    bean_lists = (
        res_json.get("bookableDetailBeans")
        or res_json.get("brabchDetailBeanList")
        or []
    )
    if isinstance(bean_lists, list):
        for bean in bean_lists:
            if not isinstance(bean, dict):
                continue
            raw = bean.get("appDate") or bean.get("date") or bean.get("availableDate")
            normalized = normalize_date(raw)
            if normalized and normalized not in dates:
                dates.append(normalized)
    return dates


def parse(res_json, check_dates):
    """Parse API response and find available dates."""
    available_date_list = parse_available_dates(res_json)
    if "all" in (check_dates or []):
        return len(available_date_list), available_date_list
    wanted = set(check_dates or [])
    filtered = [date for date in available_date_list if date in wanted]
    return len(filtered), filtered


def parse_district_list(res_json):
    """Parse branchDistrictList, keeping official values including `_F`."""
    items = []
    raw = (res_json or {}).get("branchDistrictList") or []
    if not isinstance(raw, list):
        return items
    for item in raw:
        if not isinstance(item, dict):
            continue
        value = str(item.get("value") or "").strip()
        if not value:
            continue
        name = item.get("messageCn") or item.get("message") or value
        items.append({"value": value, "name": str(name)})
    return items


def parse_branch_list(res_json):
    """Parse availableBranchList / branch list fields, skipping placeholders."""
    items = []
    raw = (
        (res_json or {}).get("availableBranchList")
        or (res_json or {}).get("branchList")
        or (res_json or {}).get("brabchDetailBeanList")
        or []
    )
    if not isinstance(raw, list):
        return items
    for item in raw:
        if not isinstance(item, dict):
            continue
        code = str(item.get("value") or item.get("branchCode") or "").strip()
        if not code:
            continue
        name = str(
            item.get("messageCn") or item.get("message") or item.get("branchName") or code
        )
        if name in ("请选择", "請選擇"):
            continue
        items.append({"code": code, "name": name})
    return items


def parse_branch_detail(res_json):
    """Parse jsonBranchDetail.action (nameCn, addressCn, telNo, code)."""
    if not isinstance(res_json, dict):
        return {}
    code = str(res_json.get("code") or res_json.get("branchCode") or "").strip()
    name = str(
        res_json.get("nameCn")
        or res_json.get("nameTw")
        or res_json.get("nameEn")
        or ""
    ).strip()
    address = str(
        res_json.get("addressCn")
        or res_json.get("addressTw")
        or res_json.get("addressEn")
        or ""
    ).strip()
    tel = str(res_json.get("telNo") or "").strip()
    district_code = str(res_json.get("districtCode") or "").strip()
    if not (code or name):
        return {}
    return {
        "code": code,
        "name": name,
        "address": address,
        "tel": tel,
        "district_code": district_code,
    }


def normalize_date(value):
    """Normalize BOCHK date strings to YYYYMMDD."""
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        return text
    parts = text.replace("-", "/").split("/")
    if len(parts) == 3:
        if len(parts[2]) == 4 and parts[0].isdigit() and parts[1].isdigit():
            day, month, year = parts
            return "{year}{month}{day}".format(
                year=year, month=month.zfill(2), day=day.zfill(2)
            )
        if len(parts[0]) == 4 and parts[1].isdigit() and parts[2].isdigit():
            year, month, day = parts
            return "{year}{month}{day}".format(
                year=year, month=month.zfill(2), day=day.zfill(2)
            )
    return ""


def yyyymmdd_to_dmy(date_str):
    """Convert YYYYMMDD to DD/MM/YYYY used by jsonAvailableBrsByDT."""
    if len(date_str) == 8 and date_str.isdigit():
        return "{0}/{1}/{2}".format(date_str[6:8], date_str[4:6], date_str[0:4])
    return date_str


def peek_districts():
    """Return cached districts or the static fallback without hitting the network."""
    with _cache_lock:
        if _district_cache["items"] is not None:
            return list(_district_cache["items"])
    return [dict(item) for item in FALLBACK_DISTRICTS]


def get_districts(force=False):
    """Return district list; cache in-process. Fallback to known HK districts."""
    with _cache_lock:
        if _district_cache["items"] is not None and not force:
            return list(_district_cache["items"])
    _warmup_session()
    payload = "bean.precondition=B"
    data = _post_json("jsonBrAvailableDT.action", payload, referer=SUBMIT_REFERER)
    items = parse_district_list(data)
    if not items:
        logger.warning("jsonBrAvailableDT district list empty, retrying once")
        data = _post_json("jsonBrAvailableDT.action", payload, referer=SUBMIT_REFERER)
        items = parse_district_list(data)
    if not items:
        logger.warning("Using fallback district list")
        items = [dict(item) for item in FALLBACK_DISTRICTS]
    with _cache_lock:
        _district_cache["items"] = items
    return list(items)


def get_branches(district):
    """Return branches for one district via jsonAvailableBrsByE.action."""
    if not district:
        return []
    _warmup_session()
    payload = urlencode({"bean.district": district, "bean.precondition": "B"})
    data = _post_json("jsonAvailableBrsByE.action", payload, referer=SUBMIT_REFERER)
    return parse_branch_list(data)


def get_branch_available_dates(branch_code):
    """Return bookable dates for one branch via jsonBrAvailableDT.action."""
    if not branch_code:
        return []
    _warmup_session()
    payload = urlencode({"bean.branchCode": branch_code, "bean.precondition": "B"})
    data = _post_json("jsonBrAvailableDT.action", payload, referer=SUBMIT_REFERER)
    return parse_available_dates(data)


def get_branch_detail(branch_code):
    """GET jsonBranchDetail.action and cache nameCn/address/tel by branch code."""
    code = str(branch_code or "").strip()
    if not code:
        return {}
    with _cache_lock:
        cached = _branch_detail_cache.get(code)
        if cached is not None:
            return dict(cached)
    _warmup_session()
    data = _get_json(
        "jsonBranchDetail.action",
        {"bean.branchCode": code},
        referer=CONTINUE_REFERER,
    )
    detail = parse_branch_detail(data)
    if not detail.get("code"):
        detail = dict(detail)
        detail["code"] = code
    if detail.get("name"):
        with _cache_lock:
            _branch_detail_cache[code] = detail
    return dict(detail)


def json_available_brs_by_dt(date_yyyymmdd, timeslot, district):
    """Branches available for a date + timeslot in a district."""
    payload = urlencode(
        {
            "bean.appDate": yyyymmdd_to_dmy(date_yyyymmdd),
            "bean.appTime": timeslot,
            "bean.district": district,
            "bean.precondition": "D",
        }
    )
    return _post_json("jsonAvailableBrsByDT.action", payload, referer=SUBMIT_REFERER)


def _branch_name_from_lists(code, district_branches):
    for branches in district_branches.values():
        for branch in branches:
            if branch.get("code") == code:
                return branch.get("name") or code
    return code


def _district_for_branch(code, watcher_districts, district_branches):
    for district in watcher_districts:
        for branch in district_branches.get(district) or []:
            if branch.get("code") == code:
                return district
    return watcher_districts[0] if watcher_districts else ""


def _fill_via_brs_by_dt(district, candidate_dates, display_name):
    """Fallback: walk timeslots of known dates to discover bookable branches."""
    branches_by_code = {}
    for date in candidate_dates:
        for slot in TIMESLOTS:
            data = json_available_brs_by_dt(date, slot, district)
            for branch in parse_branch_list(data):
                record = branches_by_code.setdefault(
                    branch["code"],
                    {
                        "code": branch["code"],
                        "name": branch["name"],
                        "district": district,
                        "district_name": display_name,
                        "dates": [],
                    },
                )
                if date not in record["dates"]:
                    record["dates"].append(date)
    return list(branches_by_code.values())


def _fallback_dates_for_district(watchers, district, candidate_dates):
    """Dates to probe via jsonAvailableBrsByDT: watcher dates intersect global slots."""
    wanted = []
    watch_any = False
    for watcher in watchers:
        cleaned = clean_watcher(watcher)
        if district not in cleaned["districts"]:
            continue
        if not cleaned["dates"]:
            watch_any = True
        for date in cleaned["dates"]:
            if date not in wanted:
                wanted.append(date)
    pool = list(candidate_dates or [])
    if watch_any:
        return pool
    if pool:
        return [date for date in wanted if date in set(pool)]
    return wanted


def _districts_needing_timeslot_fallback(needed_districts, query_codes, dates_by_code):
    """Only walk timeslots for districts with no branch dates at all."""
    codes_by_district = {}
    for code, meta in query_codes.items():
        district = meta.get("district")
        if district:
            codes_by_district.setdefault(district, []).append(code)
    fallback_districts = []
    for district in needed_districts:
        codes = codes_by_district.get(district) or []
        if not codes or all(not dates_by_code.get(code) for code in codes):
            fallback_districts.append(district)
    return fallback_districts


def collect_district_availability(watchers, candidate_dates):
    """Query unique districts/branches once per cycle.

    Returns district value -> list of {code, name, district_name, dates}.
    """
    needed_districts = unique_districts(watchers)
    if not needed_districts:
        return {}

    names = {item["value"]: item["name"] for item in get_districts()}
    district_branches = {}
    for district in needed_districts:
        district_branches[district] = get_branches(district)

    query_codes = {}
    for watcher in watchers:
        cleaned = clean_watcher(watcher)
        if not cleaned["districts"]:
            continue
        if cleaned["branch_codes"]:
            for code in cleaned["branch_codes"]:
                district = _district_for_branch(
                    code, cleaned["districts"], district_branches
                )
                query_codes[code] = {
                    "code": code,
                    "name": _branch_name_from_lists(code, district_branches),
                    "district": district,
                    "district_name": names.get(district, district_name(district)),
                }
            continue
        for district in cleaned["districts"]:
            for branch in district_branches.get(district) or []:
                query_codes[branch["code"]] = {
                    "code": branch["code"],
                    "name": branch["name"],
                    "district": district,
                    "district_name": names.get(district, district_name(district)),
                }

    dates_by_code = {}
    for code in query_codes:
        dates_by_code[code] = get_branch_available_dates(code)

    for district in _districts_needing_timeslot_fallback(
        needed_districts, query_codes, dates_by_code
    ):
        dates = _fallback_dates_for_district(watchers, district, candidate_dates)
        if not dates:
            continue
        display = names.get(district, district_name(district))
        for entry in _fill_via_brs_by_dt(district, dates, display):
            existing = dates_by_code.get(entry["code"]) or []
            merged = list(existing)
            for date in entry["dates"]:
                if date not in merged:
                    merged.append(date)
            dates_by_code[entry["code"]] = merged
            if entry["code"] not in query_codes:
                query_codes[entry["code"]] = {
                    "code": entry["code"],
                    "name": entry["name"],
                    "district": district,
                    "district_name": display,
                }

    result = {district: [] for district in needed_districts}
    for code, meta in query_codes.items():
        district = meta["district"]
        if district not in result:
            result[district] = []
        result[district].append(
            {
                "code": code,
                "name": meta["name"],
                "district_name": meta["district_name"],
                "dates": dates_by_code.get(code) or [],
            }
        )
    return result


def enrich_availability_with_details(district_availability):
    """Fill official nameCn/address/tel via jsonBranchDetail, returning a new map."""
    result = {}
    for district, entries in (district_availability or {}).items():
        updated = []
        for entry in entries or []:
            new_entry = dict(entry)
            if new_entry.get("dates") and new_entry.get("code"):
                detail = get_branch_detail(new_entry.get("code") or "")
                if detail.get("name"):
                    new_entry["name"] = detail["name"]
                if detail.get("address"):
                    new_entry["address"] = detail["address"]
                if detail.get("tel"):
                    new_entry["tel"] = detail["tel"]
            updated.append(new_entry)
        result[district] = updated
    return result


def flatten_available_slots(district_availability):
    """Turn district availability into one row per branch+date."""
    slots = []
    for district, entries in (district_availability or {}).items():
        for entry in entries or []:
            for date in entry.get("dates") or []:
                slots.append(
                    {
                        "date": date,
                        "code": entry.get("code") or "",
                        "name": entry.get("name") or entry.get("code") or "",
                        "district": district,
                        "district_name": entry.get("district_name") or "",
                        "address": entry.get("address") or "",
                        "tel": entry.get("tel") or "",
                    }
                )
    return slots


def cycle_available_count(date_count, slots):
    """Count branch+date slots when present, otherwise the global date count."""
    if slots:
        return len(slots)
    return int(date_count or 0)


def log_monitor_cycle(available_num, available_list, slots):
    """Write one cycle summary to console and the rotating log file."""
    remarks = format_branch_remarks(slots) or "-"
    logger.info(
        "Monitor cycle: %s available dates: %s branches: %s",
        cycle_available_count(available_num, slots),
        available_list,
        remarks,
    )
    return remarks


def notify_watchers(watchers, available_dates, district_availability, notify=True):
    """Match each watcher independently and send at most one email per address."""
    sent = []
    if not notify:
        return sent
    hits_by_email = {}
    for watcher in watchers:
        cleaned = clean_watcher(watcher)
        if not cleaned["email"]:
            continue
        hits = match_watcher(cleaned, available_dates, district_availability)
        if not hits:
            continue
        hits_by_email.setdefault(cleaned["email"], []).extend(hits)
    for email, hits in hits_by_email.items():
        ok = send_email(
            "中银香港可预约",
            format_hits(hits),
            to=[email],
        )
        if ok:
            sent.append(email)
            logger.info(
                "Notification sent to %s for %s",
                email,
                format_branch_remarks(hits) or [hit.get("date") for hit in hits],
            )
    return sent


def run_monitor_cycle(config=None):
    """Run one poll: global dates + deduped region queries + per-watcher mail."""
    config = config if config is not None else load_config()
    watchers = list(config.get("watchers") or [])
    notify = bool((config.get("monitor") or {}).get("notify_on_available", True))
    res_json = get_jsonAvailableDateAndTime()
    available_num, available_list = parse(res_json, ["all"])
    district_availability = enrich_availability_with_details(
        collect_district_availability(watchers, available_list)
    )
    slots = flatten_available_slots(district_availability)
    log_monitor_cycle(available_num, available_list, slots)
    notify_watchers(watchers, available_list, district_availability, notify=notify)
    return cycle_available_count(available_num, slots), available_list, slots


def run_monitor(check_dates):
    """Backward-compatible single cycle using legacy check_dates as any-date filter."""
    config = load_config()
    watchers = list(config.get("watchers") or [])
    if not watchers and check_dates:
        receivers = (config.get("email") or {}).get("receivers") or []
        dates = [] if "all" in check_dates else list(check_dates)
        watchers = [
            {
                "email": email,
                "dates": dates,
                "districts": [],
                "branch_codes": [],
            }
            for email in receivers
            if email
        ]
        config = dict(config)
        config["watchers"] = watchers
    run_monitor_cycle(config)


def main():
    """Main entry point for standalone monitor (no web UI)."""
    logger.info("Starting BOCHK appointment monitor (no web UI mode)")
    retry_count = 0
    max_retries = 3
    interval_seconds = 60

    while True:
        try:
            config = load_config()
            interval_seconds = config.get("monitor", {}).get("interval_seconds", 60)
            watchers = config.get("watchers") or []
            if not watchers:
                logger.warning("No watchers configured, retrying in 60 seconds...")
                sleep_display(60)
                continue

            run_monitor_cycle(config)
            retry_count = 0
        except Exception as exc:
            logger.error("Error during monitoring cycle: %s", exc)
            retry_count += 1
            if retry_count >= max_retries:
                logger.error("Max retries (%s) exceeded, restarting...", max_retries)
                retry_count = 0

        sleep_display(interval_seconds)


if __name__ == "__main__":
    main()

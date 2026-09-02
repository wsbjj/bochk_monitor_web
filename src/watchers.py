"""Watcher config migration and availability matching."""

EMPTY_WATCHER = {
    "email": "",
    "dates": [],
    "districts": [],
    "branch_codes": [],
}


def _as_str_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        items = [item.strip() for item in value.replace("\n", ",").split(",")]
        return [item for item in items if item]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def clean_watcher(raw):
    """Return a normalized watcher dict."""
    if not isinstance(raw, dict):
        return dict(EMPTY_WATCHER)
    email = str(raw.get("email") or "").strip()
    dates = _as_str_list(raw.get("dates"))
    if dates == ["all"]:
        dates = []
    districts = _as_str_list(raw.get("districts"))
    branch_codes = _as_str_list(raw.get("branch_codes") or raw.get("branches"))
    return {
        "email": email,
        "dates": dates,
        "districts": districts,
        "branch_codes": branch_codes,
    }


def _legacy_receivers(config):
    return _as_str_list((config.get("email") or {}).get("receivers"))


def _has_explicit_watchers(config):
    raw = config.get("watchers")
    if not isinstance(raw, list):
        return False
    return any(clean_watcher(item)["email"] for item in raw)


def normalize_watchers(config):
    """Ensure config has watchers; migrate legacy receivers + check_dates."""
    if not isinstance(config, dict):
        return {"watchers": []}
    cleaned = []
    if _has_explicit_watchers(config):
        for item in config.get("watchers") or []:
            watcher = clean_watcher(item)
            if watcher["email"]:
                cleaned.append(watcher)
    else:
        dates = list((config.get("monitor") or {}).get("check_dates") or [])
        if dates == ["all"]:
            dates = []
        for email in _legacy_receivers(config):
            cleaned.append(
                {
                    "email": email,
                    "dates": list(dates),
                    "districts": [],
                    "branch_codes": [],
                }
            )
    config["watchers"] = cleaned
    email_config = dict(config.get("email") or {})
    email_config["receivers"] = [watcher["email"] for watcher in cleaned]
    config["email"] = email_config
    return config


def _matching_dates(watcher_dates, candidate_dates):
    if not watcher_dates:
        return list(candidate_dates)
    wanted = set(watcher_dates)
    return [date for date in candidate_dates if date in wanted]


def _hits_from_availability(watcher_dates, district_availability, branch_filter=None):
    """Expand district availability into hit dicts, optionally filtered by branch."""
    hits = []
    for district, entries in (district_availability or {}).items():
        for entry in entries or []:
            code = entry.get("code") or ""
            if branch_filter and code not in branch_filter:
                continue
            for date in _matching_dates(watcher_dates, entry.get("dates") or []):
                hits.append(
                    {
                        "date": date,
                        "district": district,
                        "district_name": entry.get("district_name") or district,
                        "branch_code": code or None,
                        "branch_name": entry.get("name") or None,
                        "address": entry.get("address") or None,
                        "tel": entry.get("tel") or None,
                    }
                )
    return hits


def match_watcher(watcher, available_dates, district_availability):
    """Return hit dicts for one watcher.

    district_availability maps district value -> list of
    {code, name, district_name, dates}.
    """
    watcher = clean_watcher(watcher)
    hits = []
    districts = watcher["districts"]
    branch_filter = set(watcher["branch_codes"])

    if not districts:
        expanded = _hits_from_availability(
            watcher["dates"], district_availability, branch_filter=None
        )
        if expanded:
            return expanded
        for date in _matching_dates(watcher["dates"], available_dates):
            hits.append(
                {
                    "date": date,
                    "district": None,
                    "district_name": None,
                    "branch_code": None,
                    "branch_name": None,
                }
            )
        return hits

    for district in districts:
        entries = district_availability.get(district) or []
        hits.extend(
            _hits_from_availability(
                watcher["dates"],
                {district: entries},
                branch_filter=branch_filter,
            )
        )
    return hits


def format_hits(hits):
    """Build a readable email body from hit dicts."""
    if not hits:
        return "中银香港暂无匹配预约。"
    lines = ["中银香港可预约", ""]
    for index, hit in enumerate(hits, 1):
        if len(hits) > 1:
            lines.append("【{0}】".format(index))
        if hit.get("date"):
            lines.append("日期：{0}".format(hit["date"]))
        branch_name = hit.get("branch_name") or ""
        branch_code = hit.get("branch_code") or ""
        if branch_name and branch_code:
            lines.append("分行：{0}（{1}）".format(branch_name, branch_code))
        elif branch_name or branch_code:
            lines.append("分行：{0}".format(branch_name or branch_code))
        if hit.get("district_name") or hit.get("district"):
            lines.append("行政区：{0}".format(hit.get("district_name") or hit.get("district")))
        if hit.get("address"):
            lines.append("地址：{0}".format(hit["address"]))
        if hit.get("tel"):
            lines.append("电话：{0}".format(hit["tel"]))
        lines.append("")
    return "\n".join(lines).strip()


def format_branch_remarks(slots):
    """Compact '西贡分行(617)/20260903' labels for logs and history remarks."""
    parts = []
    for slot in slots or []:
        name = slot.get("name") or slot.get("branch_name") or ""
        code = slot.get("code") or slot.get("branch_code") or ""
        date = slot.get("date") or ""
        if name and code:
            label = "{0}({1})".format(name, code)
        elif name or code:
            label = name or code
        elif date:
            label = date
        else:
            continue
        if date and (name or code):
            label = "{0}/{1}".format(label, date)
        if label not in parts:
            parts.append(label)
    return ", ".join(parts)


def unique_districts(watchers):
    values = []
    seen = set()
    for watcher in watchers:
        for district in clean_watcher(watcher)["districts"]:
            if district not in seen:
                seen.add(district)
                values.append(district)
    return values

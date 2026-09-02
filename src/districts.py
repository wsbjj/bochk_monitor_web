"""Fallback district list from BOCHK jsonBrAvailableDT.action (branch-first)."""

# Values keep the official `_F` suffix used by the "select branch first" flow.
FALLBACK_DISTRICTS = [
    {"value": "_central_western_district_F", "name": "中西区"},
    {"value": "_eastern_district_F", "name": "东区"},
    {"value": "_island_district_F", "name": "离岛区"},
    {"value": "_kowloon_city_district_F", "name": "九龙城区"},
    {"value": "_kwai_tsing_district_F", "name": "葵青区"},
    {"value": "_kwun_tong_district_F", "name": "观塘区"},
    {"value": "_north_district_F", "name": "北区"},
    {"value": "_sai_kung_district_F", "name": "西贡区"},
    {"value": "_sha_tin_district_F", "name": "沙田区"},
    {"value": "_sham_shui_po_district_F", "name": "深水埗区"},
    {"value": "_southern_district_F", "name": "南区"},
    {"value": "_tai_po_district_F", "name": "大埔区"},
    {"value": "_tsuen_wan_district_F", "name": "荃湾区"},
    {"value": "_tuen_mun_district_F", "name": "屯门区"},
    {"value": "_wan_chai_district_F", "name": "湾仔区"},
    {"value": "_wong_tai_sin_district_F", "name": "黄大仙区"},
    {"value": "_yau_tsim_mong_district_F", "name": "油尖旺区"},
    {"value": "_yuen_long_district_F", "name": "元朗区"},
]


def district_name(value, districts=None):
    """Return display name for a district value."""
    items = districts if districts is not None else FALLBACK_DISTRICTS
    for item in items:
        if item.get("value") == value:
            return item.get("name") or value
    return value or ""

"""Generate synthetic Albertsons routing sample data for FOUR scenarios.

Outputs (per scenario):
  sample_data/<scenario>/orders.csv
  sample_data/<scenario>/locations.xlsx
  sample_data/<scenario>/constraints.xlsx

Scenarios:
  standard_week   — balanced; ordinary Monday dispatch (the original demo set).
  heavy_volume    — orders ~2x cube/weight; expected to trigger CUBE_NEAR/OVER, splits, lower utilization warnings.
  tight_windows   — store delivery windows compressed to 4-hour slots; expected to trigger WINDOW_AT_RISK + DELIVERY_LATE.
  long_haul_mix   — order weight skewed toward MT/WY destinations + tighter HOS; expected to trigger LAYOVER_REQUIRED + LCB_OFF_INTERSTATE.

Also keeps the legacy flat layout (sample_data/sample_orders.csv, etc.) for backward
compatibility with the existing /api/optimize-from-samples behavior — the legacy
files mirror the standard_week scenario.

Deterministic via fixed RNG seeds per scenario.
"""
from __future__ import annotations

import copy
import csv
import random
from datetime import time
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sample_data"
OUT.mkdir(parents=True, exist_ok=True)

BASE_SEED = 20260512


# ---------------------------------------------------------------------------
# Locations (DC + ~32 stores + 2 backhaul/vendor) — shared across scenarios
# ---------------------------------------------------------------------------
LOCATIONS: list[dict] = [
    # DC (origin)
    {"location_code": "SLC-DC", "location_name": "Salt Lake City Distribution Center",
     "location_type": "DC", "address": "5859 W Wright Brothers Dr", "city": "Salt Lake City",
     "state": "UT", "zip": "84116", "latitude": 40.7608, "longitude": -111.8910,
     "delivery_window_open": "00:00", "delivery_window_close": "23:59",
     "delivery_days": "MON,TUE,WED,THU,FRI,SAT,SUN",
     "dock_doors": 40, "max_trailer_length_ft": 53},

    # Montana long-haul
    {"location_code": "SAF-MT-KAL", "location_name": "Safeway Kalispell",
     "location_type": "STORE", "address": "1402 US-93 S", "city": "Kalispell",
     "state": "MT", "zip": "59901", "latitude": 48.1920, "longitude": -114.3168,
     "delivery_window_open": "06:00", "delivery_window_close": "20:00",
     "delivery_days": "MON,TUE,WED,THU,FRI",
     "dock_doors": 2, "max_trailer_length_ft": 53},
    {"location_code": "SAF-MT-POL", "location_name": "Safeway Polson",
     "location_type": "STORE", "address": "111 Ridgewater Dr", "city": "Polson",
     "state": "MT", "zip": "59860", "latitude": 47.6936, "longitude": -114.1631,
     "delivery_window_open": "06:00", "delivery_window_close": "20:00",
     "delivery_days": "MON,WED,FRI",
     "dock_doors": 2, "max_trailer_length_ft": 53},
    {"location_code": "ALB-MT-MISA", "location_name": "Albertsons Missoula A",
     "location_type": "STORE", "address": "2900 Brooks St", "city": "Missoula",
     "state": "MT", "zip": "59801", "latitude": 46.8721, "longitude": -114.0000,
     "delivery_window_open": "06:00", "delivery_window_close": "20:00",
     "delivery_days": "MON,TUE,WED,THU,FRI,SAT",
     "dock_doors": 3, "max_trailer_length_ft": 53},
    {"location_code": "ALB-MT-MISB", "location_name": "Albertsons Missoula B",
     "location_type": "STORE", "address": "1400 W Broadway", "city": "Missoula",
     "state": "MT", "zip": "59802", "latitude": 46.8600, "longitude": -113.9800,
     "delivery_window_open": "06:00", "delivery_window_close": "20:00",
     "delivery_days": "MON,WED,FRI",
     "dock_doors": 2, "max_trailer_length_ft": 53},
    {"location_code": "ALB-MT-WPT", "location_name": "Albertsons Wolf Point",
     "location_type": "STORE", "address": "200 US-2 E", "city": "Wolf Point",
     "state": "MT", "zip": "59201", "latitude": 48.0906, "longitude": -105.6413,
     "delivery_window_open": "06:00", "delivery_window_close": "20:00",
     "delivery_days": "TUE,FRI",
     "dock_doors": 1, "max_trailer_length_ft": 48},
    {"location_code": "ALB-MT-MAL", "location_name": "Albertsons Malta",
     "location_type": "STORE", "address": "300 S 1st St E", "city": "Malta",
     "state": "MT", "zip": "59538", "latitude": 48.3559, "longitude": -107.8742,
     "delivery_window_open": "06:00", "delivery_window_close": "20:00",
     "delivery_days": "TUE,FRI",
     "dock_doors": 1, "max_trailer_length_ft": 48},

    # Utah (10)
    {"location_code": "SAF-UT-OGD", "location_name": "Safeway Ogden",
     "location_type": "STORE", "address": "415 Washington Blvd", "city": "Ogden",
     "state": "UT", "zip": "84404", "latitude": 41.2230, "longitude": -111.9738,
     "delivery_window_open": "06:00", "delivery_window_close": "14:00",
     "delivery_days": "MON,TUE,WED,THU,FRI,SAT", "dock_doors": 3, "max_trailer_length_ft": 53},
    {"location_code": "SAF-UT-PRO", "location_name": "Safeway Provo",
     "location_type": "STORE", "address": "1227 N State St", "city": "Provo",
     "state": "UT", "zip": "84604", "latitude": 40.2338, "longitude": -111.6585,
     "delivery_window_open": "07:00", "delivery_window_close": "15:00",
     "delivery_days": "MON,TUE,WED,THU,FRI,SAT", "dock_doors": 3, "max_trailer_length_ft": 53},
    {"location_code": "ALB-UT-LOG", "location_name": "Albertsons Logan",
     "location_type": "STORE", "address": "75 N Main St", "city": "Logan",
     "state": "UT", "zip": "84321", "latitude": 41.7370, "longitude": -111.8338,
     "delivery_window_open": "06:00", "delivery_window_close": "14:00",
     "delivery_days": "MON,WED,FRI", "dock_doors": 2, "max_trailer_length_ft": 53},
    {"location_code": "ALB-UT-PCT", "location_name": "Albertsons Park City",
     "location_type": "STORE", "address": "1500 Snow Creek Dr", "city": "Park City",
     "state": "UT", "zip": "84060", "latitude": 40.6461, "longitude": -111.4980,
     "delivery_window_open": "05:00", "delivery_window_close": "12:00",
     "delivery_days": "MON,TUE,WED,THU,FRI", "dock_doors": 2, "max_trailer_length_ft": 48},
    {"location_code": "SAF-UT-LAY", "location_name": "Safeway Layton",
     "location_type": "STORE", "address": "1075 W Antelope Dr", "city": "Layton",
     "state": "UT", "zip": "84041", "latitude": 41.0602, "longitude": -111.9710,
     "delivery_window_open": "06:00", "delivery_window_close": "18:00",
     "delivery_days": "MON,TUE,WED,THU,FRI,SAT", "dock_doors": 3, "max_trailer_length_ft": 53},
    {"location_code": "ALB-UT-TOO", "location_name": "Albertsons Tooele",
     "location_type": "STORE", "address": "30 S Main St", "city": "Tooele",
     "state": "UT", "zip": "84074", "latitude": 40.5308, "longitude": -112.2983,
     "delivery_window_open": "07:00", "delivery_window_close": "15:00",
     "delivery_days": "MON,WED,FRI", "dock_doors": 2, "max_trailer_length_ft": 53},
    {"location_code": "SAF-UT-STG", "location_name": "Safeway St George",
     "location_type": "STORE", "address": "915 W Sunset Blvd", "city": "St George",
     "state": "UT", "zip": "84770", "latitude": 37.0965, "longitude": -113.5684,
     "delivery_window_open": "06:00", "delivery_window_close": "18:00",
     "delivery_days": "TUE,THU", "dock_doors": 3, "max_trailer_length_ft": 53},
    {"location_code": "ALB-UT-CDR", "location_name": "Albertsons Cedar City",
     "location_type": "STORE", "address": "905 S Main St", "city": "Cedar City",
     "state": "UT", "zip": "84720", "latitude": 37.6775, "longitude": -113.0619,
     "delivery_window_open": "06:00", "delivery_window_close": "18:00",
     "delivery_days": "TUE,THU", "dock_doors": 2, "max_trailer_length_ft": 53},
    {"location_code": "ALB-UT-VRN", "location_name": "Albertsons Vernal",
     "location_type": "STORE", "address": "1080 W Hwy 40", "city": "Vernal",
     "state": "UT", "zip": "84078", "latitude": 40.4555, "longitude": -109.5287,
     "delivery_window_open": "06:00", "delivery_window_close": "16:00",
     "delivery_days": "MON,WED,FRI", "dock_doors": 2, "max_trailer_length_ft": 48},
    {"location_code": "ALB-UT-PRC", "location_name": "Albertsons Price",
     "location_type": "STORE", "address": "415 E Main St", "city": "Price",
     "state": "UT", "zip": "84501", "latitude": 39.5994, "longitude": -110.8107,
     "delivery_window_open": "07:00", "delivery_window_close": "15:00",
     "delivery_days": "TUE,FRI", "dock_doors": 1, "max_trailer_length_ft": 48},

    # Idaho (5)
    {"location_code": "ALB-ID-POC", "location_name": "Albertsons Pocatello",
     "location_type": "STORE", "address": "800 Yellowstone Ave", "city": "Pocatello",
     "state": "ID", "zip": "83201", "latitude": 42.8713, "longitude": -112.4455,
     "delivery_window_open": "06:00", "delivery_window_close": "16:00",
     "delivery_days": "MON,WED,FRI", "dock_doors": 2, "max_trailer_length_ft": 53},
    {"location_code": "ALB-ID-IDF", "location_name": "Albertsons Idaho Falls",
     "location_type": "STORE", "address": "560 W Broadway St", "city": "Idaho Falls",
     "state": "ID", "zip": "83402", "latitude": 43.4917, "longitude": -112.0339,
     "delivery_window_open": "06:00", "delivery_window_close": "16:00",
     "delivery_days": "MON,TUE,WED,THU,FRI", "dock_doors": 3, "max_trailer_length_ft": 53},
    {"location_code": "ALB-ID-TWN", "location_name": "Albertsons Twin Falls",
     "location_type": "STORE", "address": "215 Blue Lakes Blvd N", "city": "Twin Falls",
     "state": "ID", "zip": "83301", "latitude": 42.5558, "longitude": -114.4701,
     "delivery_window_open": "06:00", "delivery_window_close": "18:00",
     "delivery_days": "MON,WED,FRI", "dock_doors": 2, "max_trailer_length_ft": 53},
    {"location_code": "ALB-ID-BOI", "location_name": "Albertsons Boise",
     "location_type": "STORE", "address": "1219 S Broadway Ave", "city": "Boise",
     "state": "ID", "zip": "83706", "latitude": 43.6150, "longitude": -116.2023,
     "delivery_window_open": "06:00", "delivery_window_close": "18:00",
     "delivery_days": "MON,TUE,WED,THU,FRI,SAT", "dock_doors": 4, "max_trailer_length_ft": 53},
    {"location_code": "ALB-ID-REX", "location_name": "Albertsons Rexburg",
     "location_type": "STORE", "address": "57 S 2nd W", "city": "Rexburg",
     "state": "ID", "zip": "83440", "latitude": 43.8260, "longitude": -111.7897,
     "delivery_window_open": "06:00", "delivery_window_close": "16:00",
     "delivery_days": "TUE,THU", "dock_doors": 2, "max_trailer_length_ft": 53},

    # Wyoming (3)
    {"location_code": "SAF-WY-RKS", "location_name": "Safeway Rock Springs",
     "location_type": "STORE", "address": "201 Westland Way", "city": "Rock Springs",
     "state": "WY", "zip": "82901", "latitude": 41.5875, "longitude": -109.2029,
     "delivery_window_open": "06:00", "delivery_window_close": "16:00",
     "delivery_days": "MON,WED,FRI", "dock_doors": 2, "max_trailer_length_ft": 53},
    {"location_code": "ALB-WY-EVN", "location_name": "Albertsons Evanston",
     "location_type": "STORE", "address": "75 Independence Dr", "city": "Evanston",
     "state": "WY", "zip": "82930", "latitude": 41.2683, "longitude": -110.9632,
     "delivery_window_open": "06:00", "delivery_window_close": "16:00",
     "delivery_days": "TUE,THU", "dock_doors": 1, "max_trailer_length_ft": 48},
    {"location_code": "ALB-WY-JKS", "location_name": "Albertsons Jackson",
     "location_type": "STORE", "address": "105 Buffalo Way", "city": "Jackson",
     "state": "WY", "zip": "83001", "latitude": 43.4799, "longitude": -110.7624,
     "delivery_window_open": "06:00", "delivery_window_close": "20:00",
     "delivery_days": "MON,WED,FRI", "dock_doors": 2, "max_trailer_length_ft": 48},

    # Colorado (3)
    {"location_code": "SAF-CO-GJT", "location_name": "Safeway Grand Junction",
     "location_type": "STORE", "address": "681 Horizon Dr", "city": "Grand Junction",
     "state": "CO", "zip": "81506", "latitude": 39.0639, "longitude": -108.5506,
     "delivery_window_open": "06:00", "delivery_window_close": "16:00",
     "delivery_days": "MON,WED,FRI", "dock_doors": 3, "max_trailer_length_ft": 53},
    {"location_code": "SAF-CO-STM", "location_name": "Safeway Steamboat Springs",
     "location_type": "STORE", "address": "1825 Central Park Dr", "city": "Steamboat Springs",
     "state": "CO", "zip": "80487", "latitude": 40.4850, "longitude": -106.8317,
     "delivery_window_open": "06:00", "delivery_window_close": "20:00",
     "delivery_days": "TUE,FRI", "dock_doors": 2, "max_trailer_length_ft": 48},
    {"location_code": "ALB-CO-CRG", "location_name": "Albertsons Craig",
     "location_type": "STORE", "address": "1111 W Victory Way", "city": "Craig",
     "state": "CO", "zip": "81625", "latitude": 40.5152, "longitude": -107.5464,
     "delivery_window_open": "06:00", "delivery_window_close": "18:00",
     "delivery_days": "WED,SAT", "dock_doors": 1, "max_trailer_length_ft": 48},

    # Backhaul / vendor (2)
    {"location_code": "VND-UT-PRD", "location_name": "Wasatch Produce Vendor",
     "location_type": "VENDOR", "address": "850 S 5600 W", "city": "Salt Lake City",
     "state": "UT", "zip": "84104", "latitude": 40.7290, "longitude": -112.0260,
     "delivery_window_open": "05:00", "delivery_window_close": "11:00",
     "delivery_days": "MON,TUE,WED,THU,FRI", "dock_doors": 4, "max_trailer_length_ft": 53},
    {"location_code": "BHL-ID-TWN", "location_name": "Twin Falls Backhaul Yard",
     "location_type": "BACKHAUL", "address": "1500 Pole Line Rd", "city": "Twin Falls",
     "state": "ID", "zip": "83301", "latitude": 42.5800, "longitude": -114.4500,
     "delivery_window_open": "05:00", "delivery_window_close": "20:00",
     "delivery_days": "MON,TUE,WED,THU,FRI,SAT", "dock_doors": 2, "max_trailer_length_ft": 53},
]

STORE_CODES = [loc["location_code"] for loc in LOCATIONS if loc["location_type"] == "STORE"]
LONG_HAUL_CODES = [c for c in STORE_CODES if "MT-" in c or "WY-" in c]


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
COMMODITY_TO_TEMP = {
    "DRY":          "AMBIENT",
    "FROZEN":       "FREEZER_0F",
    "REFRIGERATED": "COOLER_34_38F",
    "PRODUCE":      "COOLER_34_38F",
}


def _make_order(rng: random.Random, idx: int, location_code: str, commodity: str,
                weight_mult: float = 1.0, cube_mult: float = 1.0,
                force_crossdock: bool | None = None) -> dict:
    weight = int(rng.randint(500, 12000) * weight_mult)
    cube = int(rng.randint(80, 800) * cube_mult)
    cases = rng.randint(20, 300)
    is_crossdock = force_crossdock if force_crossdock is not None else rng.random() < 0.30
    return {
        "order_id":               f"PO-20260512-{idx:03d}",
        "location_code":          location_code,
        "commodity_group":        commodity,
        "temperature_group":      COMMODITY_TO_TEMP[commodity],
        "weight_lbs":             weight,
        "cube":                   cube,
        "cases":                  cases,
        "is_crossdock":           "TRUE" if is_crossdock else "FALSE",
        "order_source":           "VENDOR_CSV" if is_crossdock else "COSMOS",
        "order_date":             "2026-05-11",
        "required_delivery_date": "2026-05-12",
    }


def _gen_orders_standard(rng: random.Random, n_target: int = 70) -> list[dict]:
    orders: list[dict] = []
    idx = 1
    for code in STORE_CODES:
        n = rng.choices([1, 2, 3], weights=[35, 50, 15])[0]
        commodities = rng.sample(list(COMMODITY_TO_TEMP), k=min(n, 4))
        for commodity in commodities:
            orders.append(_make_order(rng, idx, code, commodity,
                                      weight_mult=0.65, cube_mult=0.65))
            idx += 1
    for code in ["ALB-ID-BOI", "SAF-UT-OGD", "ALB-MT-MISA"]:
        for _ in range(2):
            orders.append(_make_order(rng, idx, code, rng.choice(list(COMMODITY_TO_TEMP)),
                                      weight_mult=0.7, cube_mult=0.7,
                                      force_crossdock=True))
            idx += 1
    while len(orders) < n_target:
        orders.append(_make_order(rng, idx, rng.choice(STORE_CODES),
                                   rng.choice(list(COMMODITY_TO_TEMP)),
                                   weight_mult=0.65, cube_mult=0.65))
        idx += 1
    return orders


def _gen_orders_heavy(rng: random.Random, n_target: int = 110) -> list[dict]:
    """Heavier per-order cube + weight; expect splits and cube/weight near-cap warnings."""
    orders: list[dict] = []
    idx = 1
    # Each store: 2-5 large orders.
    for code in STORE_CODES:
        n = rng.choices([2, 3, 4, 5], weights=[15, 30, 35, 20])[0]
        commodities = rng.sample(list(COMMODITY_TO_TEMP), k=min(n, 4)) + \
                      rng.choices(list(COMMODITY_TO_TEMP), k=max(0, n - 4))
        for commodity in commodities:
            orders.append(_make_order(rng, idx, code, commodity,
                                      weight_mult=1.7, cube_mult=1.6))
            idx += 1
    # Force a few mega-orders to a couple stores so we trigger split detection.
    for code in ("ALB-ID-BOI", "SAF-UT-OGD", "ALB-MT-MISA"):
        for _ in range(2):
            orders.append(_make_order(rng, idx, code, "DRY", weight_mult=2.4, cube_mult=2.4))
            idx += 1
            orders.append(_make_order(rng, idx, code, "REFRIGERATED", weight_mult=2.0, cube_mult=2.0))
            idx += 1
    while len(orders) < n_target:
        orders.append(_make_order(rng, idx, rng.choice(STORE_CODES),
                                   rng.choice(list(COMMODITY_TO_TEMP)),
                                   weight_mult=1.5, cube_mult=1.4))
        idx += 1
    return orders


def _gen_orders_tight(rng: random.Random, n_target: int = 100) -> list[dict]:
    """Same volumes as standard; window adjustments live in the locations file."""
    return _gen_orders_standard(rng, n_target)


def _gen_orders_long_haul(rng: random.Random, n_target: int = 90) -> list[dict]:
    """Skew demand toward MT/WY (long haul); expect LAYOVER_REQUIRED and LCB_OFF_INTERSTATE."""
    orders: list[dict] = []
    idx = 1
    # Heavy load on long-haul stores
    for code in LONG_HAUL_CODES:
        for _ in range(3):
            orders.append(_make_order(rng, idx, code,
                                      rng.choice(list(COMMODITY_TO_TEMP)),
                                      weight_mult=1.4, cube_mult=1.3))
            idx += 1
    # Lighter coverage on remaining stores
    for code in STORE_CODES:
        if code in LONG_HAUL_CODES:
            continue
        for _ in range(rng.randint(1, 2)):
            orders.append(_make_order(rng, idx, code, rng.choice(list(COMMODITY_TO_TEMP))))
            idx += 1
    while len(orders) < n_target:
        orders.append(_make_order(rng, idx, rng.choice(STORE_CODES),
                                   rng.choice(list(COMMODITY_TO_TEMP))))
        idx += 1
    return orders


# ---------------------------------------------------------------------------
# Per-scenario location adjustments
# ---------------------------------------------------------------------------
def _locations_standard() -> list[dict]:
    return [dict(loc) for loc in LOCATIONS]


def _locations_tight_windows() -> list[dict]:
    """Compress every store's delivery window to 4 hours starting at original open.
    DC + vendor + backhaul are unchanged."""
    out = []
    for loc in LOCATIONS:
        new = dict(loc)
        if loc["location_type"] == "STORE":
            open_str = loc["delivery_window_open"]
            h, m = map(int, open_str.split(":"))
            close_h = min(23, h + 4)
            new["delivery_window_close"] = f"{close_h:02d}:{m:02d}"
        out.append(new)
    return out


def _locations_long_haul() -> list[dict]:
    """Long-haul stores keep 06:00–20:00. Other stores unchanged. (No structural change.)"""
    return [dict(loc) for loc in LOCATIONS]


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------
TRAILER_TYPES = [
    {"trailer_config": "40-40_COMBO", "description": "Two 40-foot trailers (doubles)",
     "max_weight_lbs": 66000, "max_cube_1stop": 3020, "max_stops": 6},
    {"trailer_config": "45-45_COMBO", "description": "Two 45-foot trailers",
     "max_weight_lbs": 72000, "max_cube_1stop": 3200, "max_stops": 5},
    {"trailer_config": "48-28_COMBO", "description": "48-foot + 28-foot pup",
     "max_weight_lbs": 68000, "max_cube_1stop": 2800, "max_stops": 4},
    {"trailer_config": "SINGLE_53", "description": "Single 53-foot trailer",
     "max_weight_lbs": 80000, "max_cube_1stop": 3400, "max_stops": 8},
]
CUBE_DEGRADATION = [
    {"trailer_config": "40-40_COMBO",
     "stops_1": 3020, "stops_2": 2980, "stops_3": 2940, "stops_4": 2900,
     "stops_5": 2860, "stops_6": 2820, "stops_7": None, "stops_8": None},
    {"trailer_config": "45-45_COMBO",
     "stops_1": 3200, "stops_2": 3160, "stops_3": 3120, "stops_4": 3080,
     "stops_5": 3040, "stops_6": None, "stops_7": None, "stops_8": None},
    {"trailer_config": "48-28_COMBO",
     "stops_1": 2800, "stops_2": 2760, "stops_3": 2720, "stops_4": 2680,
     "stops_5": None, "stops_6": None, "stops_7": None, "stops_8": None},
    {"trailer_config": "SINGLE_53",
     "stops_1": 3400, "stops_2": 3360, "stops_3": 3320, "stops_4": 3280,
     "stops_5": 3240, "stops_6": 3200, "stops_7": 3160, "stops_8": 3120},
]
ROAD_RESTRICTIONS = [
    {"state": "MT", "trailer_config": "40-40_COMBO", "restriction_type": "INTERSTATE_ONLY",
     "restriction_detail": "Max 2 miles off interstate"},
    {"state": "MT", "trailer_config": "45-45_COMBO", "restriction_type": "INTERSTATE_ONLY",
     "restriction_detail": "Max 2 miles off interstate"},
    {"state": "MT", "trailer_config": "48-28_COMBO", "restriction_type": "UNRESTRICTED",
     "restriction_detail": "No restrictions"},
    {"state": "MT", "trailer_config": "SINGLE_53", "restriction_type": "UNRESTRICTED",
     "restriction_detail": "No restrictions"},
    {"state": "CO", "trailer_config": "ALL", "restriction_type": "UNRESTRICTED",
     "restriction_detail": "No restrictions"},
    {"state": "ID", "trailer_config": "40-40_COMBO", "restriction_type": "HIGHWAY_RESTRICTION",
     "restriction_detail": "No doubles on Highway 21 south of Boise"},
    {"state": "ID", "trailer_config": "45-45_COMBO", "restriction_type": "HIGHWAY_RESTRICTION",
     "restriction_detail": "No doubles on Highway 21 south of Boise"},
    {"state": "UT", "trailer_config": "ALL", "restriction_type": "UNRESTRICTED",
     "restriction_detail": "No restrictions"},
    {"state": "WY", "trailer_config": "40-40_COMBO", "restriction_type": "WEIGHT_LIMIT",
     "restriction_detail": "Max 60000 lbs on state routes"},
    {"state": "WY", "trailer_config": "SINGLE_53", "restriction_type": "UNRESTRICTED",
     "restriction_detail": "No restrictions"},
    {"state": "NV", "trailer_config": "40-40_COMBO", "restriction_type": "INTERSTATE_ONLY",
     "restriction_detail": "Max 5 miles off interstate"},
]
COST_PROXIES_DEFAULT = [
    {"cost_type": "per_mile",              "value": 4.00,   "unit": "USD"},
    {"cost_type": "per_stop",              "value": 30.00,  "unit": "USD"},
    {"cost_type": "overtime_hour",         "value": 45.00,  "unit": "USD"},
    {"cost_type": "late_delivery_penalty", "value": 500.00, "unit": "USD"},
    {"cost_type": "driver_hourly_rate",    "value": 28.00,  "unit": "USD"},
    {"cost_type": "max_driver_hours",      "value": 11.0,   "unit": "hours"},
]
COST_PROXIES_LONG_HAUL = [
    {"cost_type": "per_mile",              "value": 4.00,   "unit": "USD"},
    {"cost_type": "per_stop",              "value": 30.00,  "unit": "USD"},
    {"cost_type": "overtime_hour",         "value": 45.00,  "unit": "USD"},
    {"cost_type": "late_delivery_penalty", "value": 500.00, "unit": "USD"},
    {"cost_type": "driver_hourly_rate",    "value": 28.00,  "unit": "USD"},
    {"cost_type": "max_driver_hours",      "value": 10.0,   "unit": "hours"},  # tighter HOS to trigger LAYOVER warnings
]


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------
def _write_workbook(path: Path, sheets: dict[str, list[dict]]) -> None:
    wb = Workbook()
    default = wb.active
    wb.remove(default)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        if not rows:
            continue
        headers = list(rows[0].keys())
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h) for h in headers])
    wb.save(path)


def _write_orders_csv(path: Path, orders: list[dict]) -> None:
    headers = list(orders[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(orders)


# ---------------------------------------------------------------------------
# Scenario runners
# ---------------------------------------------------------------------------
SCENARIOS = {
    "standard_week": {
        "label": "Standard Week",
        "description": "Balanced ordinary Monday dispatch — most routes on time, low exception count.",
        "orders": _gen_orders_standard,
        "locations": _locations_standard,
        "constraints": COST_PROXIES_DEFAULT,
    },
    "heavy_volume": {
        "label": "Heavy Volume",
        "description": "Roughly 2× per-order weight + cube. Triggers cube/weight near-cap warnings and forces splits.",
        "orders": _gen_orders_heavy,
        "locations": _locations_standard,
        "constraints": COST_PROXIES_DEFAULT,
    },
    "tight_windows": {
        "label": "Tight Windows",
        "description": "Every store's delivery window compressed to 4 hours. Triggers WINDOW_AT_RISK and DELIVERY_LATE.",
        "orders": _gen_orders_tight,
        "locations": _locations_tight_windows,
        "constraints": COST_PROXIES_DEFAULT,
    },
    "long_haul_mix": {
        "label": "Long-haul Mix",
        "description": "Demand skewed to MT/WY long-haul stores + tighter 10-hour HOS cap. Triggers LAYOVER and LCB_OFF_INTERSTATE.",
        "orders": _gen_orders_long_haul,
        "locations": _locations_long_haul,
        "constraints": COST_PROXIES_LONG_HAUL,
    },
}


def _emit_scenario(key: str, spec: dict) -> None:
    rng = random.Random(BASE_SEED + sum(ord(c) for c in key))
    orders = spec["orders"](rng)
    locations = spec["locations"]()
    constraints = spec["constraints"]

    folder = OUT / key
    folder.mkdir(parents=True, exist_ok=True)
    _write_orders_csv(folder / "orders.csv", orders)
    _write_workbook(folder / "locations.xlsx", {"locations": locations})
    _write_workbook(folder / "constraints.xlsx", {
        "trailer_types":            TRAILER_TYPES,
        "cube_degradation":         CUBE_DEGRADATION,
        "state_road_restrictions":  ROAD_RESTRICTIONS,
        "cost_proxies":             constraints,
    })
    print(f"  [{key}] {len(orders)} orders, {len(locations)} locations -> {folder}")


def _emit_legacy_files(standard_orders: list[dict]) -> None:
    """Keep the original sample_data/sample_*.* layout in place so nothing breaks."""
    _write_orders_csv(OUT / "sample_orders.csv", standard_orders)
    _write_workbook(OUT / "sample_locations.xlsx", {"locations": LOCATIONS})
    _write_workbook(OUT / "sample_constraints.xlsx", {
        "trailer_types":            TRAILER_TYPES,
        "cube_degradation":         CUBE_DEGRADATION,
        "state_road_restrictions":  ROAD_RESTRICTIONS,
        "cost_proxies":             COST_PROXIES_DEFAULT,
    })
    print(f"  [legacy] sample_orders.csv, sample_locations.xlsx, sample_constraints.xlsx")


def main() -> None:
    print("Generating scenario datasets:")
    standard_orders = None
    for key, spec in SCENARIOS.items():
        _emit_scenario(key, spec)
        if key == "standard_week":
            # also capture the standard orders for legacy emission below
            rng = random.Random(BASE_SEED + sum(ord(c) for c in key))
            standard_orders = spec["orders"](rng)
    if standard_orders:
        _emit_legacy_files(standard_orders)

    # Consistency check across all scenarios.
    loc_codes = {loc["location_code"] for loc in LOCATIONS}
    for key in SCENARIOS:
        with (OUT / key / "orders.csv").open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            missing = {row["location_code"] for row in reader} - loc_codes
            assert not missing, f"[{key}] orders reference unknown locations: {missing}"

    print(f"OK. {len(SCENARIOS)} scenarios + legacy files written to {OUT}")


if __name__ == "__main__":
    main()

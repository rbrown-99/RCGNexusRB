"""Generate synthetic Albertsons routing sample data.

Outputs:
  sample_data/sample_orders.csv
  sample_data/sample_locations.xlsx
  sample_data/sample_constraints.xlsx

Deterministic via fixed RNG seed.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sample_data"
OUT.mkdir(parents=True, exist_ok=True)

SEED = 20260512
random.seed(SEED)

# ---------------------------------------------------------------------------
# Locations (DC + ~32 stores + 2 backhaul/vendor)
# ---------------------------------------------------------------------------
# Coordinates per the project prompt.
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


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
COMMODITY_TO_TEMP = {
    "DRY":          "AMBIENT",
    "FROZEN":       "FREEZER_0F",
    "REFRIGERATED": "COOLER_34_38F",
    "PRODUCE":      "COOLER_34_38F",
}

def _gen_orders(n_target: int = 100) -> list[dict]:
    orders: list[dict] = []
    order_idx = 1
    # Ensure every store gets at least one order; many get 2-4 across commodities.
    for code in STORE_CODES:
        n = random.choices([1, 2, 3, 4], weights=[15, 35, 35, 15])[0]
        commodities = random.sample(list(COMMODITY_TO_TEMP.keys()), k=min(n, 4))
        for commodity in commodities:
            orders.append(_make_order(order_idx, code, commodity))
            order_idx += 1

    # Add cross-dock-heavy orders to a couple of larger stores to test cross-dock handling.
    crossdock_targets = ["ALB-ID-BOI", "SAF-UT-OGD", "ALB-MT-MISA"]
    for code in crossdock_targets:
        for _ in range(3):
            orders.append(_make_order(order_idx, code, random.choice(list(COMMODITY_TO_TEMP)),
                                      force_crossdock=True))
            order_idx += 1

    # Pad with random extras until we hit target count.
    while len(orders) < n_target:
        orders.append(_make_order(order_idx, random.choice(STORE_CODES),
                                   random.choice(list(COMMODITY_TO_TEMP))))
        order_idx += 1

    return orders


def _make_order(idx: int, location_code: str, commodity: str,
                force_crossdock: bool | None = None) -> dict:
    weight = random.randint(500, 12000)
    cube = random.randint(80, 800)
    cases = random.randint(20, 300)
    is_crossdock = force_crossdock if force_crossdock is not None else random.random() < 0.30
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


# ---------------------------------------------------------------------------
# Constraints workbook
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

COST_PROXIES = [
    {"cost_type": "per_mile",              "value": 4.00,   "unit": "USD"},
    {"cost_type": "per_stop",              "value": 30.00,  "unit": "USD"},
    {"cost_type": "overtime_hour",         "value": 45.00,  "unit": "USD"},
    {"cost_type": "late_delivery_penalty", "value": 500.00, "unit": "USD"},
    {"cost_type": "driver_hourly_rate",    "value": 28.00,  "unit": "USD"},
    {"cost_type": "max_driver_hours",      "value": 11.0,   "unit": "hours"},
]


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------
def _write_workbook(path: Path, sheets: dict[str, list[dict]]) -> None:
    wb = Workbook()
    # remove the default sheet
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


def main() -> None:
    orders = _gen_orders(100)
    _write_orders_csv(OUT / "sample_orders.csv", orders)
    _write_workbook(OUT / "sample_locations.xlsx", {"locations": LOCATIONS})
    _write_workbook(OUT / "sample_constraints.xlsx", {
        "trailer_types":            TRAILER_TYPES,
        "cube_degradation":         CUBE_DEGRADATION,
        "state_road_restrictions":  ROAD_RESTRICTIONS,
        "cost_proxies":             COST_PROXIES,
    })

    # quick consistency check
    loc_codes = {loc["location_code"] for loc in LOCATIONS}
    missing = {o["location_code"] for o in orders} - loc_codes
    assert not missing, f"orders reference unknown locations: {missing}"

    print(f"Wrote {len(orders)} orders, {len(LOCATIONS)} locations, "
          f"{len(TRAILER_TYPES)} trailer types, {len(ROAD_RESTRICTIONS)} road restrictions.")


if __name__ == "__main__":
    main()

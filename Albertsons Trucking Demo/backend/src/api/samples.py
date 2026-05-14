"""Serve the bundled sample data files so business users can download them.

Supports both the legacy flat layout (sample_orders.csv etc) and the per-scenario
folders (sample_data/<scenario>/{orders.csv,locations.xlsx,constraints.xlsx}).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings

router = APIRouter(prefix="/api/samples", tags=["samples"])


# logical name → (legacy flat filename, scenario-folder filename, mime, friendly download name)
_SAMPLES: dict[str, tuple[str, str, str, str]] = {
    "orders": (
        "sample_orders.csv", "orders.csv",
        "text/csv",
        "albertsons_orders.csv",
    ),
    "locations": (
        "sample_locations.xlsx", "locations.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "albertsons_locations.xlsx",
    ),
    "constraints": (
        "sample_constraints.xlsx", "constraints.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "albertsons_constraints.xlsx",
    ),
}

# Public scenario catalog. Mirrors scripts/generate_sample_data.py SCENARIOS.
SCENARIOS = {
    "standard_week": {
        "label": "Standard Week",
        "blurb": "Balanced ordinary Monday dispatch — most routes on time, low exception count.",
        "highlights": ["Default baseline", "Few exceptions", "Healthy savings vs naive"],
    },
    "heavy_volume": {
        "label": "Heavy Volume",
        "blurb": "Roughly 2× per-order weight + cube. Triggers cube/weight near-cap warnings and forces splits.",
        "highlights": ["CUBE_NEAR_CAPACITY", "WEIGHT_NEAR_CAPACITY", "Splits on hot stores"],
    },
    "tight_windows": {
        "label": "Tight Windows",
        "blurb": "Every store's delivery window compressed to 4 hours. Triggers WINDOW_AT_RISK and DELIVERY_LATE.",
        "highlights": ["WINDOW_AT_RISK", "DELIVERY_LATE", "Sequencing pressure"],
    },
    "long_haul_mix": {
        "label": "Long-haul Mix",
        "blurb": "Demand skewed to MT/WY long-haul stores + tighter 10-hour HOS cap. Triggers LAYOVER and LCB_OFF_INTERSTATE.",
        "highlights": ["LAYOVER_REQUIRED", "LCB_OFF_INTERSTATE", "Long inter-stop hops"],
    },
}


def _resolve_dir() -> Path:
    cand = Path(settings.sample_data_dir)
    if not cand.is_absolute():
        # resolve relative to repo root (backend/.. = repo root)
        cand = (Path(__file__).resolve().parents[2] / settings.sample_data_dir).resolve()
    if cand.exists():
        return cand
    # container fallback baked in by the Dockerfile
    fallback = Path("/sample_data")
    if fallback.exists():
        return fallback
    raise HTTPException(status_code=500, detail=f"sample_data directory not found at {cand} or /sample_data")


@router.get("/")
def list_samples():
    """Return scenario catalog + legacy flat sample list."""
    return {
        "scenarios": [
            {"key": k, **v} for k, v in SCENARIOS.items()
        ],
        "samples": [
            {
                "name": key,
                "filename": meta[3],
                "mime": meta[2],
                "url": f"/api/samples/{key}",
            }
            for key, meta in _SAMPLES.items()
        ],
    }


@router.get("/{name}")
def download_sample(name: str, scenario: str | None = None):
    if name not in _SAMPLES:
        raise HTTPException(status_code=404, detail=f"Unknown sample '{name}'. Try one of: {list(_SAMPLES)}")
    legacy_rel, scenario_rel, mime, dl_name = _SAMPLES[name]
    base = _resolve_dir()
    if scenario:
        if scenario not in SCENARIOS:
            raise HTTPException(status_code=404, detail=f"Unknown scenario {scenario!r}. Try one of: {list(SCENARIOS)}")
        full = base / scenario / scenario_rel
        dl_name = f"{scenario}_{dl_name}"
    else:
        full = base / legacy_rel
    if not full.exists():
        raise HTTPException(status_code=404, detail=f"Sample file missing on server: {full}")
    return FileResponse(path=str(full), media_type=mime, filename=dl_name)

"""Serve the bundled sample data files so business users can download them."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings

router = APIRouter(prefix="/api/samples", tags=["samples"])


# logical name → (relative filename, mime, friendly download name)
_SAMPLES: dict[str, tuple[str, str, str]] = {
    "orders": (
        "sample_orders.csv",
        "text/csv",
        "albertsons_sample_orders.csv",
    ),
    "locations": (
        "sample_locations.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "albertsons_sample_locations.xlsx",
    ),
    "constraints": (
        "sample_constraints.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "albertsons_sample_constraints.xlsx",
    ),
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
    """Return the list of downloadable sample files."""
    return {
        "samples": [
            {
                "name": key,
                "filename": meta[2],
                "mime": meta[1],
                "url": f"/api/samples/{key}",
            }
            for key, meta in _SAMPLES.items()
        ]
    }


@router.get("/{name}")
def download_sample(name: str):
    if name not in _SAMPLES:
        raise HTTPException(status_code=404, detail=f"Unknown sample '{name}'. Try one of: {list(_SAMPLES)}")
    rel, mime, dl_name = _SAMPLES[name]
    full = _resolve_dir() / rel
    if not full.exists():
        raise HTTPException(status_code=404, detail=f"Sample file missing on server: {full}")
    return FileResponse(path=str(full), media_type=mime, filename=dl_name)

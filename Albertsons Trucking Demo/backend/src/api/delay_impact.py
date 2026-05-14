"""POST /api/delay-impact/{session_id} — project a delay through a route.

Given a route_id and delay_minutes, shift every stop's arrival forward by that
amount and report which stops fall outside their delivery window. Does NOT
re-solve; just propagates and reports. Answers Q9 ("if Trip XXX is held 2 hours,
which stores miss?").

Body:
  {
    "route_id": "R03-...",
    "delay_minutes": 120
  }

Response:
  {
    "session_id": "...",
    "route_id": "...",
    "delay_minutes": 120,
    "original_arrivals": [{"location_code": "...", "arrival_min": 540, "window_close_min": 1080}, ...],
    "projected_arrivals": [{"location_code": "...", "arrival_min": 660, "window_close_min": 1080, "late_by_min": 0}, ...],
    "newly_late_stops": ["ALB-MT-MISA", ...],
    "still_on_time_count": 6,
    "summary": "2 stops will miss their window; 6 still on time."
  }
"""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from ..state import store

router = APIRouter(prefix="/api", tags=["delay_impact"])


def _hhmm(minutes: float) -> str:
    m = int(round(minutes)) % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def _window_close_min(loc) -> int:
    return loc.delivery_window_close.hour * 60 + loc.delivery_window_close.minute


@router.post("/delay-impact/{session_id}")
async def delay_impact(session_id: str, body: dict = Body(default_factory=dict)):
    try:
        sess = store.get(session_id)
    except KeyError:
        raise HTTPException(404, "unknown session")

    result = sess.get("result")
    if not result:
        raise HTTPException(400, "session has no result; run /api/optimize first")

    route_id = body.get("route_id")
    if not route_id:
        raise HTTPException(400, "route_id is required")
    try:
        delay = int(body.get("delay_minutes", 0))
    except (TypeError, ValueError):
        raise HTTPException(400, "delay_minutes must be an integer")
    if delay < 0:
        raise HTTPException(400, "delay_minutes cannot be negative")

    route = next((r for r in result.routes if r.route_id == route_id), None)
    if not route:
        raise HTTPException(404, f"route {route_id} not found in session {session_id}")

    locations_by_code = {l.location_code: l for l in sess["locations"]}

    # The solver records arrival_minutes_from_start as elapsed wall-clock from
    # depot departure. To compare against a delivery window we need to anchor
    # to the depot open time. We assume same-day morning dispatch: depot opens
    # at the earliest store window open (or 06:00 default).
    depot_start_min = 6 * 60  # default 06:00

    original = []
    projected = []
    newly_late: list[str] = []
    still_on_time = 0

    for s in route.stops:
        loc = locations_by_code.get(s.location_code)
        win_close = _window_close_min(loc) if loc else 24 * 60 - 1
        win_open = (loc.delivery_window_open.hour * 60 + loc.delivery_window_open.minute) if loc else 0
        original_arrival_clock = depot_start_min + s.arrival_minutes_from_start
        projected_arrival_clock = depot_start_min + s.arrival_minutes_from_start + delay
        original.append({
            "location_code": s.location_code,
            "location_name": s.location_name,
            "arrival_clock": _hhmm(original_arrival_clock),
            "arrival_min": int(original_arrival_clock),
            "window_open_min": win_open,
            "window_close_min": win_close,
            "on_time": original_arrival_clock <= win_close,
        })
        late_by = max(0, int(projected_arrival_clock - win_close))
        projected_late = projected_arrival_clock > win_close
        was_late = original_arrival_clock > win_close
        projected.append({
            "location_code": s.location_code,
            "location_name": s.location_name,
            "arrival_clock": _hhmm(projected_arrival_clock),
            "arrival_min": int(projected_arrival_clock),
            "window_close_min": win_close,
            "late_by_min": late_by,
            "on_time": not projected_late,
        })
        if projected_late:
            if not was_late:
                newly_late.append(s.location_code)
        else:
            still_on_time += 1

    summary_parts = []
    if newly_late:
        summary_parts.append(f"{len(newly_late)} stop(s) will newly miss their window: {', '.join(newly_late)}")
    summary_parts.append(f"{still_on_time} stop(s) still on time")
    summary = "; ".join(summary_parts) + "."

    return {
        "session_id": session_id,
        "route_id": route_id,
        "delay_minutes": delay,
        "original_arrivals": original,
        "projected_arrivals": projected,
        "newly_late_stops": newly_late,
        "still_on_time_count": still_on_time,
        "summary": summary,
    }

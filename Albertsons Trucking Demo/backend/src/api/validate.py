"""POST /api/validate — re-validate a session's routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..solver import validate_routes
from ..state import store

router = APIRouter(prefix="/api", tags=["validate"])


@router.post("/validate/{session_id}")
async def validate_endpoint(session_id: str):
    try:
        sess = store.get(session_id)
    except KeyError:
        raise HTTPException(404, "unknown session")
    if not sess.get("result"):
        raise HTTPException(400, "session has no result yet — run /api/optimize first")

    findings = validate_routes(sess["result"].routes, sess["locations"], sess["bundle"])
    return {
        "session_id": session_id,
        "violations": [f.model_dump() for f in findings if f.severity == "VIOLATION"],
        "warnings":   [f.model_dump() for f in findings if f.severity == "WARNING"],
        "info":       [f.model_dump() for f in findings if f.severity == "INFO"],
    }

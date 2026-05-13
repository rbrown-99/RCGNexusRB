"""FastAPI app entry."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    compare_router,
    explain_router,
    optimize_router,
    parse_router,
    reoptimize_router,
    samples_router,
    validate_router,
)
from .config import settings

app = FastAPI(
    title="Albertsons Truck Routing API",
    description="Optimization backend for the cold-chain VRP demo.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"ok": True, "service": "albertsons-routing-api"}


for router in (parse_router, optimize_router, validate_router,
               reoptimize_router, compare_router, explain_router,
               samples_router):
    app.include_router(router)

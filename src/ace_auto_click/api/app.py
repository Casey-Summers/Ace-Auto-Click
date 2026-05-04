from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ace_auto_click.api.models import ProductName
from ace_auto_click.api.routes import router, shutdown, startup
from ace_auto_click.api.sequence_service import to_action_step as _to_action_step
from ace_auto_click.api.settings_service import load_app_settings as _load_app_settings


def create_app() -> FastAPI:
    next_app = FastAPI(title=ProductName, version="0.1.0")
    next_app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:1420", "http://127.0.0.1:1420"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    next_app.include_router(router)
    next_app.add_event_handler("startup", startup)
    next_app.add_event_handler("shutdown", shutdown)
    return next_app


app = create_app()

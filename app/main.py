from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import APP_VERSION, Settings
from app.data_store import DataStore
from app.errors import install_error_handlers
from app.routers import analysis, catalog


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()

    @asynccontextmanager
    async def lifespan(app):
        app.state.store = DataStore(settings.data_dir)
        app.state.settings = settings
        yield

    app = FastAPI(title="Agro Field", version=APP_VERSION, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware, allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
    )
    install_error_handlers(app)
    app.include_router(catalog.router)
    app.include_router(analysis.router)
    return app


app = create_app()

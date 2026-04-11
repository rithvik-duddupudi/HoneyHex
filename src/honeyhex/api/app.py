from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from honeyhex.api.routes import router
from honeyhex.registry.db import init_db, session_scope
from honeyhex.registry.service import ensure_swarm


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    with session_scope() as session:
        ensure_swarm(session, "default")
    yield


def create_app() -> FastAPI:
    application = FastAPI(title="HoneyHex Registry", version="1", lifespan=lifespan)
    application.include_router(router, prefix="/api/v1")
    return application


app = create_app()

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request

from src.agents.handlers import router as agents_router


def create_app() -> FastAPI:
    application = FastAPI(title="ForkFlux API")

    @application.middleware("http")
    async def middleware(request: Request, call_next: Any) -> Any:
        request.state.trace_id = str(uuid4())
        response = await call_next(request)
        return response

    @application.get("/api/v1/health", status_code=204)
    def health() -> None:
        return None

    application.include_router(agents_router, prefix="/v1")

    return application


app = create_app()

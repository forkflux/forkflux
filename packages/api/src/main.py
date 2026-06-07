from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.agents.handlers import router as agents_router
from src.exceptions import BaseValidationError
from src.jobs.handlers import router as jobs_router


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
    application.include_router(jobs_router, prefix="/v1")

    return application


app = create_app()


@app.exception_handler(BaseValidationError)
async def custom_validation_exception_handler(request: Request, exc: BaseValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": [
                {"loc": ["body", exc.field_name], "msg": exc.msg, "type": exc.code, "input": exc.value, "ctx": {}}
            ]
        },
    )

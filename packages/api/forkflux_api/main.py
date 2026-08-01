from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse

from forkflux_api.agents.mcp_handlers import public_router as mcp_agents_public_router
from forkflux_api.agents.mcp_handlers import router as mcp_agents_router
from forkflux_api.agents.ui_handlers import router as ui_agents_router
from forkflux_api.exceptions import BaseValidationError
from forkflux_api.jobs.mcp_handlers import router as mcp_jobs_router
from forkflux_api.jobs.ui_handlers import router as ui_jobs_router
from forkflux_api.profile.ui_handlers import router as ui_profile_router

_STATIC_DIR = Path(__file__).parent / "static"


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

    # agents
    application.include_router(mcp_agents_router, prefix="/api/v1/mcp")
    application.include_router(mcp_agents_public_router, prefix="/api/v1/mcp")
    application.include_router(ui_agents_router, prefix="/api/v1/ui")
    # jobs
    application.include_router(mcp_jobs_router, prefix="/api/v1/mcp")
    application.include_router(ui_jobs_router, prefix="/api/v1/ui")
    # profile
    application.include_router(ui_profile_router, prefix="/api/v1/ui")

    # Serve the bundled dashboard (built from packages/dashboard) when the
    # static directory exists. Registered AFTER all API routes so that
    # /api/v1/* paths always take priority.
    if _STATIC_DIR.is_dir():

        @application.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str) -> FileResponse:
            # Never shadow API paths with the SPA fallback.
            if full_path.startswith("api/"):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
            # Serve a real static asset if it exists (JS, CSS, images, favicon).
            if full_path:
                file_path = _STATIC_DIR / full_path
                if file_path.is_file():
                    return FileResponse(file_path)
            # SPA fallback: return index.html for client-side routes.
            return FileResponse(_STATIC_DIR / "index.html")

    return application


app = create_app()


@app.exception_handler(BaseValidationError)
async def custom_validation_exception_handler(request: Request, exc: BaseValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": [
                {"loc": [exc.loc, exc.field_name], "msg": exc.msg, "type": exc.code, "input": exc.value, "ctx": {}}
            ]
        },
    )

from fastapi import FastAPI


def create_app() -> FastAPI:
    application = FastAPI(title="ForkFlux API")

    @application.get("/api/v1/health", status_code=204)
    def health() -> None:
        return None

    return application


app = create_app()

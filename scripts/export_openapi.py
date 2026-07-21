import json
from pathlib import Path

from packages.api.forkflux_api.main import app


def export_openapi():
    output_path = Path("docs/static/openapi.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    openapi_schema = app.openapi()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)

    print(f"✅ Done")


if __name__ == "__main__":
    export_openapi()

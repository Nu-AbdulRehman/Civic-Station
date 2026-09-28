"""Write the backend's OpenAPI schema to a file, without starting a server (FR-FE-012).

    cd frontend && npm run gen:types

The app factory connects to nothing at construction, so the URLs below are never dialled.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

settings = Settings(database_url="postgresql+asyncpg://unused/unused", redis_url="redis://unused")
schema = create_app(settings).openapi()
Path(sys.argv[1]).write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")

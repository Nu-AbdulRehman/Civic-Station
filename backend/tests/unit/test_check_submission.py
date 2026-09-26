"""scripts/check_submission.py: each check fails on a planted violation and passes when it is
removed (T-M2-014 done-when), and the real repository is clean."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_submission", ROOT / "scripts/check_submission.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_submission"] = module
    spec.loader.exec_module(module)
    return module


cs = _load()


def test_the_real_repository_is_clean() -> None:
    assert cs.check_backend_layers() == []
    assert cs.check_frontend_rules() == []


def plant(tmp_path: Path, relative: str, source: str) -> Path:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("relative", "source", "rule"),
    [
        (
            "app/repositories/x.py",
            "from app.services.complaints import ComplaintService\n",
            "layer",
        ),
        ("app/services/x.py", "from app.routes import complaints\n", "layer"),
        (
            "app/routes/x.py",
            "from app.repositories.complaints import ComplaintRepository\n",
            "routes-sql",
        ),
        ("app/routes/x.py", "from sqlalchemy import select\n", "sql"),
        ("app/services/x.py", "import sqlalchemy\n", "sql"),
        ("app/services/x.py", "from redis.asyncio import Redis\n", "vendor"),
        ("app/routes/x.py", "import httpx\n", "vendor"),
        ("app/domain/x.py", "from app.config import Settings\n", "layer"),
        ("app/providers/cache/x.py", "from app.services.stats import StatsService\n", "layer"),
        ("app/services/x.py", "import os\nURL = os.environ['DATABASE_URL']\n", "environ"),
        ("app/services/x.py", "import os\nURL = os.getenv('X')\n", "environ"),
        (
            "app/services/x.py",
            "from app.providers.triage.rules import RuleBasedTriage\n",
            "provider",
        ),
        ("app/main.py", "Base.metadata.create_all(engine)\n", "ddl"),
    ],
)
def test_backend_violation_is_caught_then_cleared(
    tmp_path: Path, relative: str, source: str, rule: str
) -> None:
    path = plant(tmp_path, relative, source)
    assert [f.rule for f in cs.check_backend_layers(tmp_path)] == [rule]
    path.write_text("VALUE = 1\n", encoding="utf-8")
    assert cs.check_backend_layers(tmp_path) == []


@pytest.mark.parametrize(
    "allowed",
    [
        ("app/repositories/x.py", "from sqlalchemy import select\n"),
        ("app/db/x.py", "from sqlalchemy.orm import DeclarativeBase\n"),
        ("alembic/versions/0002_x.py", "import sqlalchemy as sa\n"),
        ("seeds/complaints.py", "from sqlalchemy.dialects.postgresql import insert\n"),
        ("app/providers/cache/x.py", "from redis.asyncio import Redis\n"),
        (
            "app/providers/triage/factory.py",
            "from app.providers.triage.rules import RuleBasedTriage\n",
        ),
        ("app/config.py", "import os\nX = os.environ\n"),
        ("app/services/x.py", 'DOC = "never import sqlalchemy here"\n'),  # AST, not grep
    ],
)
def test_sanctioned_locations_pass(tmp_path: Path, allowed: tuple[str, str]) -> None:
    plant(tmp_path, *allowed)
    assert cs.check_backend_layers(tmp_path) == []


@pytest.mark.parametrize(
    "source",
    [
        'const STATUSES = ["open", "in_progress", "resolved", "rejected"];',
        "const CATS = ['water', 'roads'];",
        'const NEXT = { open: ["in_progress", "rejected"] };',
    ],
)
def test_frontend_second_source_of_truth_is_caught(tmp_path: Path, source: str) -> None:
    path = plant(tmp_path, "components/Thing.tsx", source + "\n")
    assert cs.check_frontend_rules(tmp_path)  # at least one finding names the duplicate
    path.write_text("import { statusValues } from '../api/types';\n", encoding="utf-8")
    assert cs.check_frontend_rules(tmp_path) == []


def test_generated_types_and_labels_are_exempt(tmp_path: Path) -> None:
    plant(tmp_path, "api/types.ts", 'export const statusValues = ["open", "in_progress"];\n')
    plant(tmp_path, "api/labels.ts", 'export const L = ["open", "resolved"];\n')
    assert cs.check_frontend_rules(tmp_path) == []

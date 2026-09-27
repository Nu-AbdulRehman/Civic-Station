"""Mechanical checks behind the architecture rubric and the §5.3 deductions (FR-DOC-007).

    python scripts/check_submission.py            # from the repository root; exit 1 on findings

A lint, not a grader. Standard library only, so it runs before any dependency is installed.
Layer checks walk the AST rather than grepping, because a grep cannot tell an import from a
string (NFR-ARCH-001). Each check is one function in CHECKS; the infrastructure detectors of
T-M8-014 (secrets in history, Compose, Kubernetes, CI `needs:`) are added the same way.
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    rule: str
    detail: str

    def __str__(self) -> str:
        where = self.path.relative_to(ROOT) if self.path.is_relative_to(ROOT) else self.path
        return f"{where}:{self.line}: [{self.rule}] {self.detail}"


# --- helpers ------------------------------------------------------------------------------------


def python_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.py")):
        if not {".venv", "__pycache__"} & set(path.parts):
            yield path


def module_name(path: Path, backend: Path) -> str:
    return ".".join(path.relative_to(backend).with_suffix("").parts)


def imports(tree: ast.AST) -> Iterator[tuple[str, int]]:
    """Every absolute module a file imports, with its line."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module, node.lineno


def within(module: str, *packages: str) -> bool:
    return any(module == p or module.startswith(p + ".") for p in packages)


def parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


# --- backend layer checks (T-M2-014, NFR-ARCH-001/002/004, FR-BE-011/016/020/022) ---

# (importer package, forbidden import prefixes, rule, why)
LAYER_RULES: list[tuple[str, tuple[str, ...], str, str]] = [
    ("app.repositories", ("app.services", "app.routes"), "layer", "repositories import upward"),
    ("app.services", ("app.routes",), "layer", "services import routes"),
    ("app.routes", ("app.repositories", "app.db"), "routes-sql",
     "routes reach the database directly (FR-BE-011)"),
    ("app.providers", ("app.services", "app.repositories", "app.routes"), "layer",
     "providers import application layers"),
]  # fmt: skip

# BR-DATA-003 exemptions: migrations (and the Alembic runner that executes them) and the seed.
# app/db holds the engine and ORM models (00-conventions §1), used only by repositories.
SQL_ALLOWED = ("app.repositories", "app.db", "alembic.env", "alembic.versions", "seeds.complaints")
VENDOR_SDKS = ("openai", "redis", "httpx", "httpx2")
CONCRETE_PROVIDERS = ("LLMTriage", "OllamaTriage", "RuleBasedTriage", "SimulatedTriage")


def check_backend_layers(backend: Path = ROOT / "backend") -> list[Finding]:
    findings: list[Finding] = []
    sources = [
        p
        for p in python_files(backend)
        if p.relative_to(backend).parts[0] in {"app", "alembic", "seeds"}
    ]
    for path in sources:
        module = module_name(path, backend)
        tree = parse(path)
        for imported, line in imports(tree):
            for owner, forbidden, rule, why in LAYER_RULES:
                if within(module, owner) and within(imported, *forbidden):
                    findings.append(Finding(path, line, rule, f"{why}: imports {imported}"))
            if (
                within(module, "app.domain")
                and within(imported, "app")
                and not within(imported, "app.domain")
            ):
                findings.append(Finding(path, line, "layer", f"domain imports {imported}"))
            if within(imported, "sqlalchemy") and not within(module, *SQL_ALLOWED):
                findings.append(Finding(path, line, "sql", "sqlalchemy imported outside SQL layer"))
            if within(imported, *VENDOR_SDKS) and not within(module, "app.providers"):
                if within(module, "app"):
                    findings.append(
                        Finding(path, line, "vendor", f"{imported} imported outside providers/")
                    )
        if within(module, "app"):
            findings += _environ_reads(path, module, tree)
            findings += _concrete_providers(path, module, tree)
            findings += _ddl(path, module)
    return findings


def _environ_reads(path: Path, module: str, tree: ast.AST) -> list[Finding]:
    if module == "app.config":
        return []
    return [
        Finding(path, node.lineno, "environ", "reads the environment outside app/config.py")
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
        and node.attr in {"environ", "getenv", "putenv"}
    ]


def _concrete_providers(path: Path, module: str, tree: ast.AST) -> list[Finding]:
    if within(module, "app.providers.triage"):
        return []
    names = {
        (node.id if isinstance(node, ast.Name) else node.attr, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Name, ast.Attribute))
    } | {
        (alias.name, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    return [
        Finding(path, line, "provider", f"concrete provider {name} named outside providers/triage")
        for name, line in sorted(names)
        if name in CONCRETE_PROVIDERS
    ]


_DDL = re.compile(r"\bcreate_all\b|\bCREATE\s+TABLE\b", re.IGNORECASE)


def _ddl(path: Path, module: str) -> list[Finding]:
    return [
        Finding(path, number, "ddl", "schema DDL outside alembic/versions (BR-DATA-001)")
        for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if _DDL.search(text)
    ]


# --- frontend: no second source of truth (BR-STATUS-005, BR-VOCAB-005, FR-FE-018) ---

_STATUS = r"[\"'](?:open|in_progress|resolved|rejected)[\"']"
_CATEGORY = r"[\"'](?:water|electricity|sanitation|roads|streetlights|other)[\"']"
_PRIORITY = r"[\"'](?:high|normal|low)[\"']"
_HAND_WRITTEN = [
    (re.compile(rf"\[\s*{v}\s*,\s*{v}"), f"hand-written {n} list")
    for v, n in ((_STATUS, "status"), (_CATEGORY, "category"), (_PRIORITY, "priority"))
] + [
    (re.compile(rf"\b(?:open|in_progress|resolved|rejected)\s*:\s*\[\s*{_STATUS}"),
     "status transition map"),
]  # fmt: skip
FRONTEND_EXEMPT = {"types.ts", "labels.ts"}  # generated types; display labels (FR-FE-018)


def check_frontend_rules(src: Path = ROOT / "frontend" / "src") -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(p for p in src.rglob("*") if p.suffix in {".ts", ".tsx"}):
        if path.name in FRONTEND_EXEMPT:
            continue
        for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for pattern, what in _HAND_WRITTEN:
                if pattern.search(text):
                    findings.append(Finding(path, number, "frontend-rule", what))
    return findings


CHECKS: list[Callable[[], list[Finding]]] = [check_backend_layers, check_frontend_rules]


def main() -> int:
    findings = [finding for check in CHECKS for finding in check()]
    for finding in findings:
        print(finding)
    print(f"check_submission: {len(CHECKS)} checks, {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

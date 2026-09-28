"""Mechanical checks behind the architecture rubric and the §5.3 deductions (FR-DOC-007).

    python scripts/check_submission.py            # from the repository root; exit 1 on findings

A lint, not a grader. Standard library only, so it runs before any dependency is installed.
Layer checks walk the AST rather than grepping, because a grep cannot tell an import from a
string (NFR-ARCH-001). Each check is one function in CHECKS: the layer and frontend checks
(T-M2-014), then one detector per §5.3 deduction (T-M8-014): secrets in the tree and in history,
Secret placeholders, image tags and `:latest`, `localhost`, the production Compose file, CI
`needs:`, and the postgres StatefulSet with resource requests and limits.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import subprocess
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


# --- §5.3 infrastructure detectors (T-M8-014, 09-M8 §10). Line-based on purpose: stdlib only, and
# every file they read is small, hand-written YAML or a Dockerfile. ---


def _tracked(root: Path) -> list[Path]:
    """Files git tracks (so .env and build output never count); every file if not a repository."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
        ).stdout.decode()
        return [root / p for p in out.split("\0") if p and (root / p).is_file()]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()


def _yaml_docs(path: Path) -> Iterator[tuple[int, list[str]]]:
    """(first line number, lines) for each `---`-separated document."""
    start, doc = 1, []
    for number, text in enumerate(_lines(path), 1):
        if text.strip() == "---":
            yield start, doc
            start, doc = number + 1, []
        else:
            doc.append(text)
    yield start, doc


def _kind_and_name(doc: list[str]) -> tuple[str, str]:
    kind = next((t.split(":", 1)[1].strip() for t in doc if t.startswith("kind:")), "")
    name = next((t.split(":", 1)[1].strip() for t in doc if re.match(r"^  name:", t)), "")
    return kind, name


def _load_secret_patterns() -> dict[str, re.Pattern[str]]:
    """The one pattern set, owned by scan_bundle.py (FR-FE-019)."""
    spec = importlib.util.spec_from_file_location("scan_bundle", ROOT / "scripts" / "scan_bundle.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict(module.SECRET_PATTERNS)


_PLACEHOLDER = re.compile(r"PLACEHOLDER_|\$\{|<[a-z-]+>|change[_-]?me", re.IGNORECASE)


def check_secrets(root: Path = ROOT) -> list[Finding]:
    """-20: a key, token or password in the tree or anywhere in history; a committed .env."""
    patterns = _load_secret_patterns()
    findings = [
        Finding(p, 1, "secret", "committed .env file")
        for p in _tracked(root)
        if p.name.startswith(".env") and p.name != ".env.example"
    ]
    for path in _tracked(root):
        for number, text in enumerate(_lines(path), 1):
            for name, pattern in patterns.items():
                match = pattern.search(text)
                # Report where, never the value (scan_bundle.py's rule).
                if match and not _PLACEHOLDER.search(match.group(0)):
                    findings.append(Finding(path, number, "secret", f"{name} in the tree"))
    try:
        history = subprocess.run(
            ["git", "log", "-p", "--all", "--format=commit %H"],
            cwd=root, capture_output=True, check=True,
        ).stdout.decode(errors="ignore")
        env_files = subprocess.run(
            ["git", "log", "--all", "--name-only", "--format="],
            cwd=root, capture_output=True, check=True,
        ).stdout.decode(errors="ignore")
    except (OSError, subprocess.CalledProcessError):
        return findings
    commit = "?"
    for text in history.splitlines():
        if text.startswith("commit "):
            commit = text[7:19]
        elif text.startswith("+") and not text.startswith("+++"):
            for name, pattern in patterns.items():
                match = pattern.search(text)
                if match and not _PLACEHOLDER.search(match.group(0)):
                    findings.append(Finding(root, 0, "secret", f"{name} in history, commit {commit}"))
    for name in sorted(set(env_files.split())):
        if Path(name).name.startswith(".env") and Path(name).name != ".env.example":
            findings.append(Finding(root, 0, "secret", f"{name} was committed at some point"))
    return findings  # fmt: skip


def check_k8s_secrets(root: Path = ROOT) -> list[Finding]:
    """-15: a committed Secret manifest must carry placeholders only (FR-K8S-005)."""
    findings: list[Finding] = []
    for path in sorted((root / "k8s").rglob("*.yaml")):
        for start, doc in _yaml_docs(path):
            if _kind_and_name(doc)[0] != "Secret":
                continue
            in_data = False
            for offset, text in enumerate(doc):
                if re.match(r"^(stringData|data):", text):
                    in_data = True
                elif in_data and re.match(r"^\S", text):
                    in_data = False
                elif in_data and ":" in text and not text.strip().startswith("#"):
                    value = text.split(":", 1)[1].strip().strip("\"'")
                    if value and not value.startswith("PLACEHOLDER_"):
                        findings.append(Finding(path, start + offset, "k8s-secret",
                                                "Secret value is not a PLACEHOLDER_"))
    return findings


_FROM = re.compile(r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?", re.IGNORECASE)
_IMAGE = re.compile(r"^\s*-?\s*image:\s*[\"']?([^\s\"'#]+)")


def _untagged(image: str) -> bool:
    last = image.rsplit("/", 1)[-1]
    return "@" not in last and ":" not in last


def check_image_tags(root: Path = ROOT) -> list[Finding]:
    """-8 / -8: every base image and deployed image has an explicit tag, and none is :latest."""
    findings: list[Finding] = []
    for path in sorted(root.glob("*/Dockerfile")) + sorted(root.glob("Dockerfile")):
        stages: set[str] = set()
        for number, text in enumerate(_lines(path), 1):
            if m := _FROM.match(text):
                image, alias = m.group(1), m.group(2)
                if image not in stages and (_untagged(image) or image.endswith(":latest")):
                    findings.append(Finding(path, number, "image-tag", f"FROM {image} is not pinned"))
                if alias:
                    stages.add(alias)
    overlays = [p.read_text(encoding="utf-8") for p in (root / "k8s" / "overlays").glob("*/kustomization.yaml")]
    files = sorted(root.glob("compose*.yaml")) + sorted((root / "k8s").rglob("*.yaml"))
    for path in files:
        for number, text in enumerate(_lines(path), 1):
            if ":latest" in text and not text.lstrip().startswith("#"):
                findings.append(Finding(path, number, "latest", ":latest in deployed configuration"))
            if re.search(r"newTag:\s*[\"']?latest\b", text):
                findings.append(Finding(path, number, "latest", "overlay sets newTag: latest"))
            m = _IMAGE.match(text)
            if not m or not _untagged(m.group(1)):
                continue
            image = m.group(1)
            # A base image may be untagged only if every overlay pins it (T-M7-011).
            pinned = overlays and all(
                re.search(rf"name:\s*{re.escape(image)}\s*\n(?:\s+\S.*\n){{0,2}}?\s+newTag:", o)
                for o in overlays
            )
            if "k8s/base" not in path.as_posix() or not pinned:
                findings.append(Finding(path, number, "image-tag", f"image {image} has no tag"))
    return findings  # fmt: skip


_LOCALHOST = re.compile(r"(?:https?://)?(?:localhost|127\.0\.0\.1)(?::\d+)?")


def check_localhost(root: Path = ROOT) -> list[Finding]:
    """-8: no service-to-service localhost (FR-FE-016, BR-SEC-004), with its exclusions.

    Excluded: `vite.config.ts` and `.env.example` dev defaults, lines marked `# localhost-ok`, the
    browser-facing `civic-station.localhost` (AD-029), a Dockerfile HEALTHCHECK probing its own
    container (BR-SEC-004), and `backend/tests/`, which runs on the host or CI runner and is never
    containerised configuration.
    """
    findings: list[Finding] = []
    for path in _tracked(root):
        rel = path.relative_to(root).as_posix()
        in_scope = rel.startswith(("frontend/", "backend/", "k8s/")) or re.fullmatch(
            r"compose[^/]*\.ya?ml", rel
        )
        if (
            not in_scope
            or path.name in {"vite.config.ts", ".env.example"}
            or rel.startswith("backend/tests/")
            or path.suffix in {".png", ".json", ".lock"}
        ):
            continue
        lines = _lines(path)
        for number, text in enumerate(lines, 1):
            stripped = text.replace("civic-station.localhost", "")
            if not _LOCALHOST.search(stripped) or "localhost-ok" in text:
                continue
            previous = lines[number - 2] if number > 1 else ""
            if path.name == "Dockerfile" and "HEALTHCHECK" in text + previous:
                continue
            findings.append(Finding(path, number, "localhost", "service-to-service localhost"))
    return findings


def _blocks(lines: list[str], indent: int) -> Iterator[tuple[str, int, list[str]]]:
    """(key, line number, body) for each mapping key at exactly `indent` spaces."""
    key, start, body = "", 0, []
    for number, text in enumerate(lines, 1):
        m = re.match(rf"^ {{{indent}}}([A-Za-z0-9_-]+):", text)
        if m:
            if key:
                yield key, start, body
            key, start, body = m.group(1), number, []
        elif key and text.strip() and len(text) - len(text.lstrip()) < indent:
            yield key, start, body
            key, body = "", []
        elif key:
            body.append(text)
    if key:
        yield key, start, body


def check_compose_prod(root: Path = ROOT) -> list[Finding]:
    """-8: compose.prod.yaml publishes no database/cache port and builds nothing (BR-SEC-005)."""
    path = root / "compose.prod.yaml"
    if not path.is_file():
        return []
    lines = _lines(path)
    findings = [
        Finding(path, n, "compose-prod", "build: in the production Compose file")
        for n, t in enumerate(lines, 1)
        if re.match(r"^\s+build:", t)
    ]
    services = next((b for k, _, b in _blocks(lines, 0) if k == "services"), [])
    for name, _, body in _blocks(services, 2):
        if name in {"database", "cache"} and any(re.match(r"^\s{4}ports:", t) for t in body):
            findings.append(Finding(path, 1, "compose-prod", f"{name} publishes a port"))
    return findings


_PUBLISH = re.compile(r"docker push|publish-images|gh release|kubectl apply|deploy-k8s|docker login")


def check_workflow_needs(root: Path = ROOT) -> list[Finding]:
    """-8: every job that publishes or deploys is gated by needs: (BR-DEL-001)."""
    findings: list[Finding] = []
    for path in sorted((root / ".github" / "workflows").glob("*.y*ml")):
        jobs = next((b for k, _, b in _blocks(_lines(path), 0) if k == "jobs"), [])
        for name, _, body in _blocks(jobs, 2):
            text = "\n".join(body)
            if _PUBLISH.search(text) and not re.search(r"^\s{4}needs:", text, re.MULTILINE):
                findings.append(Finding(path, 1, "needs", f"job {name} publishes/deploys without needs:"))
    return findings  # fmt: skip


def check_k8s_workloads(root: Path = ROOT) -> list[Finding]:
    """-8: postgres is a StatefulSet with volumeClaimTemplates; every workload declares resource
    requests and limits (FR-K8S-002, FR-K8S-007)."""
    findings: list[Finding] = []
    statefulset = False
    for path in sorted((root / "k8s").rglob("*.yaml")):
        for start, doc in _yaml_docs(path):
            kind, name = _kind_and_name(doc)
            body = "\n".join(doc)
            if name == "postgres" and kind == "Deployment":
                findings.append(Finding(path, start, "postgres", "postgres is a Deployment"))
            if name == "postgres" and kind == "StatefulSet":
                statefulset = "volumeClaimTemplates:" in body
                if not statefulset:
                    findings.append(Finding(path, start, "postgres", "StatefulSet has no volumeClaimTemplates"))
            if kind in {"Deployment", "StatefulSet"}:
                images = len(re.findall(r"^\s+(?:- )?image:", body, re.MULTILINE))
                for part in ("requests:", "limits:"):
                    if body.count(part) < images:
                        findings.append(Finding(path, start, "resources", f"{name}: a container has no {part[:-1]}"))
    if (root / "k8s").is_dir() and not statefulset and not findings:
        findings.append(Finding(root / "k8s", 0, "postgres", "no postgres StatefulSet found"))
    return findings  # fmt: skip


CHECKS: list[Callable[[], list[Finding]]] = [
    check_backend_layers,
    check_frontend_rules,
    check_secrets,
    check_k8s_secrets,
    check_image_tags,
    check_localhost,
    check_compose_prod,
    check_workflow_needs,
    check_k8s_workloads,
]


def main() -> int:
    findings = [finding for check in CHECKS for finding in check()]
    for finding in findings:
        print(finding)
    print(f"check_submission: {len(CHECKS)} checks, {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

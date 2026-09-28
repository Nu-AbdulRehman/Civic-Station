"""scripts/check_submission.py §5.3 detectors (T-M8-014): each one fails on a planted violation
and passes once it is removed, and the real repository is clean under every check."""

import subprocess
from pathlib import Path

import pytest

from tests.unit.test_check_submission import cs, plant

# Built at runtime so this file never holds a secret-shaped literal of its own.
FAKE_KEY = "gsk_" + "A1b2C3d4" * 4


def test_every_check_is_clean_on_the_real_repository() -> None:
    for check in cs.CHECKS:
        assert check() == [], check.__name__


def test_secret_in_the_tree_and_a_committed_env_are_caught(tmp_path: Path) -> None:
    path = plant(tmp_path, "backend/app/x.py", f'KEY = "{FAKE_KEY}"\n')
    env = plant(tmp_path, ".env", "X=1\n")
    findings = cs.check_secrets(tmp_path)
    assert [f.rule for f in findings] == ["secret", "secret"]
    path.write_text('KEY = "PLACEHOLDER_groq_api_key"\n', encoding="utf-8")
    env.unlink()
    assert cs.check_secrets(tmp_path) == []


def test_secret_removed_from_the_tree_is_still_caught_in_history(tmp_path: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)  # noqa: S603, S607

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    path = plant(tmp_path, "config.py", f'KEY = "{FAKE_KEY}"\n')
    git("add", ".")
    git("commit", "-qm", "leak")
    path.write_text("KEY = None\n", encoding="utf-8")
    git("commit", "-qam", "remove")
    details = [f.detail for f in cs.check_secrets(tmp_path)]
    assert len(details) == 1
    assert "in history" in details[0]


MANIFEST = """apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
stringData:
  POSTGRES_PASSWORD: {value}
"""


def test_k8s_secret_with_a_real_value_is_caught(tmp_path: Path) -> None:
    path = plant(tmp_path, "k8s/base/secret.yaml", MANIFEST.format(value="hunter2hunter2"))
    assert [f.rule for f in cs.check_k8s_secrets(tmp_path)] == ["k8s-secret"]
    path.write_text(MANIFEST.format(value="PLACEHOLDER_postgres_password"), encoding="utf-8")
    assert cs.check_k8s_secrets(tmp_path) == []


@pytest.mark.parametrize(
    ("relative", "bad", "good"),
    [
        ("backend/Dockerfile", "FROM python\n", "FROM python:3.12.14-slim-bookworm\n"),
        ("backend/Dockerfile", "FROM node:latest AS build\n", "FROM node:22.23.3 AS build\n"),
        (
            "compose.yaml",
            "services:\n  cache:\n    image: redis\n",
            "services:\n  cache:\n    image: redis:7.4.11\n",
        ),
        (
            "k8s/overlays/prod/x.yaml",
            "      image: ghcr.io/o/app:latest\n",
            "      image: ghcr.io/o/app:abc123\n",
        ),
        (
            "k8s/overlays/prod/kustomization.yaml",
            "images:\n  - name: app\n    newTag: latest\n",
            "images:\n  - name: app\n    newTag: abc123\n",
        ),
    ],
)
def test_unpinned_or_latest_image_is_caught(
    tmp_path: Path, relative: str, bad: str, good: str
) -> None:
    path = plant(tmp_path, relative, bad)
    findings = cs.check_image_tags(tmp_path)
    assert findings
    assert {f.rule for f in findings} <= {"image-tag", "latest"}
    path.write_text(good, encoding="utf-8")
    assert cs.check_image_tags(tmp_path) == []


def test_untagged_base_image_passes_only_when_every_overlay_pins_it(tmp_path: Path) -> None:
    plant(tmp_path, "k8s/base/backend.yaml", "      image: civic-station-backend\n")
    plant(
        tmp_path,
        "k8s/overlays/dev/kustomization.yaml",
        "images:\n  - name: civic-station-backend\n    newTag: dev\n",
    )
    prod = plant(tmp_path, "k8s/overlays/prod/kustomization.yaml", "resources: [../../base]\n")
    assert [f.rule for f in cs.check_image_tags(tmp_path)] == ["image-tag"]
    prod.write_text(
        "images:\n  - name: civic-station-backend\n    newName: r/b\n    newTag: x\n",
        encoding="utf-8",
    )
    assert cs.check_image_tags(tmp_path) == []


@pytest.mark.parametrize(
    ("relative", "line"),
    [
        ("compose.yaml", "      REDIS_URL: redis://localhost:6379/0\n"),
        ("k8s/base/x.yaml", "      value: http://127.0.0.1:8000\n"),
        ("frontend/src/api/client.ts", 'const BASE = "http://localhost:8000";\n'),
        ("backend/app/config.py", 'URL = "redis://localhost:6379"\n'),
    ],
)
def test_service_to_service_localhost_is_caught(tmp_path: Path, relative: str, line: str) -> None:
    path = plant(tmp_path, relative, line)
    assert [f.rule for f in cs.check_localhost(tmp_path)] == ["localhost"]
    fixed = line.replace("localhost", "cache").replace("127.0.0.1", "backend")
    path.write_text(fixed, encoding="utf-8")
    assert cs.check_localhost(tmp_path) == []


@pytest.mark.parametrize(
    ("relative", "source"),
    [
        ("frontend/vite.config.ts", 'proxy: { "/api": "http://localhost:8000" },\n'),
        (".env.example", "X=http://localhost:5173\n"),
        ("k8s/base/ingress.yaml", "    - host: civic-station.localhost\n"),
        ("compose.yaml", "      X: http://localhost:1  # localhost-ok\n"),
        (
            "backend/Dockerfile",
            'HEALTHCHECK --interval=10s \\\n    CMD ["wget", "http://127.0.0.1:8000/"]\n',
        ),
        ("backend/tests/unit/test_x.py", 'DOWN = "redis://127.0.0.1:1/0"\n'),
    ],
)
def test_localhost_exclusions_pass(tmp_path: Path, relative: str, source: str) -> None:
    plant(tmp_path, relative, source)
    assert cs.check_localhost(tmp_path) == []


PROD = """services:
  database:
    image: postgres:16.15
{extra}
  frontend:
    image: x:1
    ports: ["8080:8080"]
"""


@pytest.mark.parametrize("extra", ['    ports: ["5432:5432"]', "    build: ./backend"])
def test_compose_prod_data_port_or_build_is_caught(tmp_path: Path, extra: str) -> None:
    path = plant(tmp_path, "compose.prod.yaml", PROD.format(extra=extra))
    assert [f.rule for f in cs.check_compose_prod(tmp_path)] == ["compose-prod"]
    path.write_text(PROD.format(extra=""), encoding="utf-8")
    assert cs.check_compose_prod(tmp_path) == []


WORKFLOW = """on: push
jobs:
  test:
    runs-on: ubuntu-24.04
    steps:
      - run: pytest
  build-push:
{needs}    runs-on: ubuntu-24.04
    steps:
      - run: docker push ghcr.io/o/app:sha
"""


def test_publish_job_without_needs_is_caught(tmp_path: Path) -> None:
    path = plant(tmp_path, ".github/workflows/cd.yml", WORKFLOW.format(needs=""))
    assert [f.rule for f in cs.check_workflow_needs(tmp_path)] == ["needs"]
    path.write_text(WORKFLOW.format(needs="    needs: test\n"), encoding="utf-8")
    assert cs.check_workflow_needs(tmp_path) == []


WORKLOAD = """apiVersion: apps/v1
kind: {kind}
metadata:
  name: postgres
spec:
  template:
    spec:
      containers:
        - name: postgres
          image: postgres:16.15
{resources}
{claims}
"""
RESOURCES = "          resources:\n            requests: {cpu: 1}\n            limits: {cpu: 1}"
CLAIMS = "  volumeClaimTemplates: []"


@pytest.mark.parametrize(
    ("kind", "resources", "claims", "rule"),
    [
        ("Deployment", RESOURCES, "", "postgres"),
        ("StatefulSet", RESOURCES, "", "postgres"),
        ("StatefulSet", "", CLAIMS, "resources"),
    ],
)
def test_postgres_workload_violations_are_caught(
    tmp_path: Path, kind: str, resources: str, claims: str, rule: str
) -> None:
    source = WORKLOAD.format(kind=kind, resources=resources, claims=claims)
    path = plant(tmp_path, "k8s/base/postgres.yaml", source)
    assert rule in {f.rule for f in cs.check_k8s_workloads(tmp_path)}
    fixed = WORKLOAD.format(kind="StatefulSet", resources=RESOURCES, claims=CLAIMS)
    path.write_text(fixed, encoding="utf-8")
    assert cs.check_k8s_workloads(tmp_path) == []

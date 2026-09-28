"""Fail if a built frontend bundle contains anything shaped like a secret (FR-FE-019, BR-SEC-002).

    python scripts/scan_bundle.py frontend/dist

Anything in a browser bundle is public; minification is not a defence. The pattern set is the
one FR-FE-019 names, and check_submission.py (T-M2-014) reuses SECRET_PATTERNS.
"""

import re
import sys
from pathlib import Path

SECRET_PATTERNS = {
    "Groq API key": re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    "Google API key": re.compile(r"AIza[A-Za-z0-9_-]{35}"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "credential literal": re.compile(
        r"(?i)(api[_-]?key|secret|token|password)[\"']?\s*[:=]\s*[\"'][^\"'\s]{16,}[\"']"
    ),
}


def scan(root: Path) -> list[str]:
    findings = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                # Report where, never the value itself: the scan must not leak what it finds.
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path}:{line}: {name}")
    return findings


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    if not root.is_dir():
        print(f"scan_bundle: {root} is not a directory (build first)", file=sys.stderr)
        return 2
    findings = scan(root)
    for finding in findings:
        print(finding, file=sys.stderr)
    print(f"scan_bundle: {len(findings)} finding(s) in {root}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

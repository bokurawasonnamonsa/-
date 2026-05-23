#!/usr/bin/env python3
"""Auto-allow production deploy/verify shell commands (no user click)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hook_util import emit, read_stdin_json, run_hook

ALLOW = re.compile(
    r"production_auto_pipeline|vps_deploy_with_password|VERIFY_PRODUCTION|"
    r"qa_production_check|pip install paramiko",
    re.I,
)


def main() -> int:
    payload = read_stdin_json()
    cmd = payload.get("command") or ""
    if ALLOW.search(cmd):
        emit({"permission": "allow"})
    else:
        emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(run_hook("beforeShellExecution", main))

#!/usr/bin/env python3
"""Deploy to VPS + HTTP verify. Called by Cursor hooks (no .bat clicks)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "config" / "production.json"
LOG_DIR = REPO / "logs"
STATUS_PATH = LOG_DIR / "production_pipeline_status.json"
SECRET = REPO / "vps_deploy_local.secret"
DEPLOY_PY = REPO / "vps_deploy_with_password.py"
VERIFY_PS1 = REPO / "VERIFY_PRODUCTION.ps1"


def _log(msg: str) -> None:
    print(msg, flush=True)


def _write_status(data: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    STATUS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _stop_local_tunnel() -> None:
    """Stop local cloudflared only. Never taskkill python.exe — kills this pipeline."""
    if os.name != "nt":
        return
    for exe in ("cloudflared.exe",):
        subprocess.run(["taskkill", "/IM", exe, "/F"], capture_output=True)


def _run(cmd: list[str], *, cwd: Path | None = None) -> int:
    _log("$ " + " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(cwd or REPO))
    return int(p.returncode)


def deploy() -> int:
    if not SECRET.is_file():
        _log("MISSING vps_deploy_local.secret")
        return 2
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "paramiko", "-q"],
            cwd=REPO,
            check=False,
        )
    except Exception:
        pass
    return _run([sys.executable, str(DEPLOY_PY)], cwd=REPO)


def verify_http() -> int:
    if not VERIFY_PS1.is_file():
        _log("MISSING VERIFY_PRODUCTION.ps1")
        return 2
    return _run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(VERIFY_PS1),
        ],
        cwd=REPO,
    )


def verify_drill_room_e2e() -> int:
    """本番WSで 作成→一覧→参加 を実際に実行（静的チェックだけでは不足）。"""
    qa = REPO / "scripts" / "qa_feature_check.py"
    if not qa.is_file():
        _log("MISSING qa_feature_check.py")
        return 2
    return _run([sys.executable, str(qa), "--scopes", "ws_drill"])


def verify_drill_browser() -> int:
    """本番を実ブラウザで操作（headed・スクリーンショット logs/browser_qa/）。"""
    script = REPO / "scripts" / "qa_drill_browser.py"
    if not script.is_file():
        _log("MISSING qa_drill_browser.py")
        return 2
    return _run([sys.executable, str(script)])


def main() -> int:
    mode = "full"
    if len(sys.argv) > 1:
        mode = sys.argv[1].lstrip("-")

    status: dict = {
        "mode": mode,
        "deploy_rc": None,
        "verify_rc": None,
        "drill_e2e_rc": None,
        "drill_browser_rc": None,
        "ok": False,
    }

    if mode in ("full", "deploy", "deploy-only"):
        _stop_local_tunnel()
        status["deploy_rc"] = deploy()
        if status["deploy_rc"] != 0:
            status["ok"] = False
            _write_status(status)
            return int(status["deploy_rc"])

    if mode in ("full", "verify", "verify-only"):
        time.sleep(3)
        status["verify_rc"] = verify_http()
        status["drill_e2e_rc"] = verify_drill_room_e2e()
        status["drill_browser_rc"] = verify_drill_browser()
        status["ok"] = (
            status["verify_rc"] == 0
            and status["drill_e2e_rc"] == 0
            and status["drill_browser_rc"] == 0
        )
        _write_status(status)
        if status["drill_e2e_rc"] != 0:
            _log("FAIL drill room WS E2E. See logs/qa_last_result.json")
        if status["drill_browser_rc"] != 0:
            _log("FAIL drill room browser QA. See logs/browser_qa/last_browser_qa.json")
        return 0 if status["ok"] else 1

    status["ok"] = True
    _write_status(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

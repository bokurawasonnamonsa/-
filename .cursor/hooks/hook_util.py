"""Shared helpers for Cursor command hooks (stdin JSON / stdout JSON)."""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STATE_DIR = Path(__file__).resolve().parent / "state"
try:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass

DEPLOY_MARKERS = {
    "main.py",
    "player.html",
    "staff.html",
    "support.html",
    "index.html",
    "voices.js",
    "sw.js",
    "vps_setup_utc_web.sh",
}


def read_stdin_json() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def log_hook_error(hook_name: str, exc: BaseException) -> None:
    try:
        line = (
            f"{datetime.now(timezone.utc).isoformat()} [{hook_name}] "
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}\n"
        )
        (STATE_DIR / "hook_errors.log").open("a", encoding="utf-8").write(line)
    except OSError:
        pass


def run_hook(hook_name: str, main_fn) -> int:
    """Run hook; on error emit {} and exit 0 (fail-open for Cursor UI)."""
    try:
        return int(main_fn())
    except Exception as exc:
        log_hook_error(hook_name, exc)
        emit({})
        return 0


def state_path(name: str) -> Path:
    return STATE_DIR / name


def load_json(name: str, default: dict | None = None) -> dict:
    p = state_path(name)
    if not p.is_file():
        return default or {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default or {}


def save_json(name: str, data: dict) -> None:
    state_path(name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def is_deployable_file(file_path: str) -> bool:
    try:
        rel = Path(file_path).resolve().relative_to(REPO.resolve())
    except ValueError:
        return False
    if rel.parts and rel.parts[0] in (".cursor", "logs", "_deploy_tmp", ".git"):
        return False
    return rel.name in DEPLOY_MARKERS or rel.suffix in (".py", ".html", ".js", ".sh")


def load_production_urls() -> dict:
    cfg = REPO / "config" / "production.json"
    if not cfg.is_file():
        return {"player_url": "https://3301-svs.jp/", "staff_url": "https://3301-svs.jp/staff_hq_3301"}
    return json.loads(cfg.read_text(encoding="utf-8"))


def _autosave_settings() -> dict:
    vscode = REPO / ".vscode" / "settings.json"
    mode, delay_ms = "afterDelay", 500
    if vscode.is_file():
        try:
            cfg = json.loads(vscode.read_text(encoding="utf-8"))
            mode = cfg.get("files.autoSave", mode)
            delay_ms = int(cfg.get("files.autoSaveDelay", delay_ms))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return {"mode": mode, "delay_ms": delay_ms, "enabled": mode not in ("off", "none")}


def update_workflow_status(phase: str, **extra: object) -> None:
    ws = load_json("workflow_status.json", {})
    ws["current_phase"] = phase
    ws["updated_at"] = datetime.now(timezone.utc).isoformat()
    ws["autosave"] = _autosave_settings()
    for key, val in extra.items():
        ws[key] = val
    save_json("workflow_status.json", ws)


def record_file_edit(file_path: str) -> None:
    try:
        rel = str(Path(file_path).resolve().relative_to(REPO.resolve()))
    except ValueError:
        rel = file_path
    ws = load_json("workflow_status.json", {})
    edits = ws.get("edited_files") or []
    if rel not in edits:
        edits.append(rel)
    ws["edited_files"] = edits
    ws["last_edit_at"] = datetime.now(timezone.utc).isoformat()
    ws["autosave"] = _autosave_settings()
    ws["autosave_note"] = (
        f"自動保存 {ws['autosave']['mode']} ({ws['autosave']['delay_ms']}ms) — "
        "編集後すぐにディスクへ書き込み予定"
        if ws["autosave"].get("enabled")
        else "自動保存オフ — 手動保存が必要"
    )
    update_workflow_status("afterFileEdit: デプロイ予約", **ws)

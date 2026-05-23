#!/usr/bin/env python3
"""占領割当 UI — 本番 player.html マーカー確認。"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

MARKERS = [
    "occupyDutyLine",
    "applyOccupyDutyFromMsg",
    "applyDutyTierToBlocks",
    "sortDisplayBlocksByDuty",
    "duty-role-badge",
    "duty-block-primary",
    "returnEndMs",
    "player-occupy-duty-",
]


def step(id_: str, name: str, ok: bool, note: str = "") -> dict:
    return {"id": id_, "name": name, "ok": ok, "note": note, "kind": "auto"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(REPO / "config" / "production.json"))
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    player_url = (cfg.get("player_url") or cfg.get("public_url") or "https://3301-svs.jp/").rstrip("/") + "/"
    steps: list[dict] = []
    try:
        req = urllib.request.Request(player_url, headers={"User-Agent": "utc-qa-occupy-duty/1"})
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read().decode("utf-8", errors="replace")
            steps.append(step("br_occupy_player_http", "player URL HTTP", r.status == 200, player_url))
    except Exception as e:
        steps.append(step("br_occupy_player_http", "player URL HTTP", False, str(e)[:160]))
        body = ""

    if body:
        missing = [m for m in MARKERS if m not in body]
        steps.append(
            step(
                "br_occupy_duty_markers",
                "占領割当UIマーカー一式",
                len(missing) == 0,
                "ok" if not missing else f"missing: {', '.join(missing)}",
            )
        )
    out = REPO / "logs" / "qa_occupy_duty_browser.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    ok_all = all(s.get("ok") for s in steps)
    out.write_text(
        json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "steps": steps, "ok": ok_all}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for s in steps:
        print(f"  [{'OK' if s.get('ok') else 'NG'}] {s['id']}: {s['name']} - {s.get('note', '')}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())

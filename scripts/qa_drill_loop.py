#!/usr/bin/env python3
"""
訓練ルーム作成→一覧→参加 を実サーバーで検証し、失敗時は非0終了。
ローカル: 別ターミナルで main.py 起動後、--local で実行。
本番: 引数なし（config/production.json の URL）。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true", help="http://127.0.0.1:8000 で検証")
    ap.add_argument("--full", action="store_true", help="qa_feature_check --full を実行")
    ap.add_argument("--max-attempts", type=int, default=3)
    args = ap.parse_args()

    base = "http://127.0.0.1:8000/" if args.local else ""
    cmd = [sys.executable, str(REPO / "scripts" / "qa_feature_check.py")]
    if args.full:
        cmd.append("--full")
    else:
        cmd.extend(["--scopes", "ws_drill,http,operator"])
    if base:
        cmd.extend(["--base-url", base])

    must_ok = (
        "ws_drill_create",
        "ws_drill_list_creator",
        "ws_drill_list_joiner",
        "ws_drill_join",
    )

    for attempt in range(1, args.max_attempts + 1):
        print(f"=== qa_drill_loop attempt {attempt}/{args.max_attempts} ===", flush=True)
        r = subprocess.run(cmd, cwd=str(REPO))
        if r.returncode == 0:
            print("PASS: drill room E2E", flush=True)
            return 0
        time.sleep(2)

    print("FAIL: drill room E2E after retries. Required steps:", ", ".join(must_ok), flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())

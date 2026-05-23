#!/usr/bin/env python3
"""
訓練ルームを実ブラウザで操作して確認する（headed・スクリーンショット保存）。
参謀が TEST ルーム作成 → 別タブで参加一覧に TEST が出るかを目視可能に検証。

使い方:
  python scripts/qa_drill_browser.py
  python scripts/qa_drill_browser.py --url https://3301-svs.jp/
  python scripts/qa_drill_browser.py --headless   # CI用（通常は headed）
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOG_DIR = REPO / "logs" / "browser_qa"
CONFIG = REPO / "config" / "production.json"


def load_url(arg: str) -> str:
    if arg:
        return arg.rstrip("/") + "/"
    if CONFIG.is_file():
        return json.loads(CONFIG.read_text(encoding="utf-8")).get("player_url", "https://3301-svs.jp/").rstrip("/") + "/"
    return "https://3301-svs.jp/"


def shot(page, name: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    p = LOG_DIR / f"{name}.png"
    page.screenshot(path=str(p), full_page=True)
    print(f"screenshot: {p}", flush=True)
    return p


def run(url: str, headed: bool) -> int:
    from playwright.sync_api import sync_playwright

    room_name = "TEST"
    room_code = "test" + uuid.uuid4().hex[:6]
    results: list[tuple[str, bool, str]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headed,
            slow_mo=400 if headed else 0,
            args=["--start-maximized"] if headed else [],
        )

        # --- 参謀: ルーム作成 ---
        ctx_a = browser.new_context(viewport={"width": 420, "height": 900})
        page_a = ctx_a.new_page()
        print(f"\n=== [A] 作成側  {url} ===", flush=True)
        page_a.goto(url, wait_until="networkidle", timeout=60000)
        shot(page_a, "01_top")

        page_a.click("#btnModeDrill")
        page_a.click("#btnEnv2device")
        page_a.wait_for_selector("#step2_5_alliance", state="visible", timeout=15000)
        shot(page_a, "02_drill_join_step")

        page_a.click("#drillTabCreate")
        page_a.fill("#drillAllianceNameInput", room_name)
        page_a.fill("#drillRoomKeyInput", room_code)
        shot(page_a, "03_create_filled")
        page_a.click("text=作成して入る")

        page_a.wait_for_function(
            """() => {
                const el = document.getElementById('drillStatusMsg');
                return el && el.textContent && el.textContent.includes('作成');
            }""",
            timeout=20000,
        )
        shot(page_a, "04_create_done")
        status_a = page_a.locator("#drillStatusMsg").inner_text()
        print(f"作成側ステータス: {status_a}", flush=True)
        results.append(("create_status", "作成" in status_a, status_a))

        page_a.click("#drillTabJoin")
        page_a.wait_for_timeout(2000)
        opts_a = page_a.eval_on_selector_all(
            "#drillRoomSelect option",
            "els => els.map(o => o.textContent)",
        )
        shot(page_a, "05_creator_sees_TEST_in_list")
        creator_sees = any(room_name in (t or "") for t in opts_a)
        results.append(("creator_list_has_TEST", creator_sees, ", ".join(opts_a[:8])))

        page_a.click("#btnStaff")
        page_a.wait_for_selector("#staffPlayerRoleArea", state="visible", timeout=10000)
        page_a.click("#btnStaffLeader1")
        page_a.wait_for_selector("#inputsArea", state="visible", timeout=10000)
        page_a.fill("#pName", "ブラウザ参謀")
        page_a.click("text=登録して開始")
        page_a.wait_for_selector("#display", state="visible", timeout=20000)
        page_a.wait_for_selector("text=参謀として参加中", timeout=20000)
        shot(page_a, "06_staff_main")
        results.append(("staff_screen", True, "参謀画面表示"))
        presence_a = page_a.locator("#alliancePresenceLine").inner_text()
        shot(page_a, "06b_staff_presence_line")
        results.append(("presence_line_visible", bool(presence_a.strip()), presence_a[:80]))
        results.append(
            (
                "presence_staff_named",
                "参謀" in presence_a and "ブラウザ参謀" in presence_a,
                presence_a[:80],
            )
        )

        # --- 参加者: ルーム参加タブ ---
        ctx_b = browser.new_context(viewport={"width": 420, "height": 900})
        page_b = ctx_b.new_page()
        print(f"\n=== [B] 参加側  {url} ===", flush=True)
        page_b.goto(url, wait_until="networkidle", timeout=60000)
        page_b.click("#btnModeDrill")
        page_b.click("#btnEnv2device")
        page_b.wait_for_selector("#step2_5_alliance", state="visible", timeout=15000)
        page_b.click("#drillTabJoin")
        page_b.wait_for_timeout(2500)
        shot(page_b, "10_join_tab")

        options = page_b.eval_on_selector_all(
            "#drillRoomSelect option",
            "els => els.map(o => ({v: o.value, t: o.textContent}))",
        )
        labels = [(o.get("t") or "").strip() for o in options if o.get("v")]
        print("ルーム一覧:", labels, flush=True)

        def label_clean(t: str) -> bool:
            return bool(t) and "#" not in t and "(" not in t and "人)" not in t

        clean_all = all(label_clean(t) for t in labels)
        exact_count = sum(1 for t in labels if t == room_name)
        has_test = exact_count >= 1
        results.append(("join_list_label_clean", clean_all, ", ".join(labels[:12])))
        results.append(
            (
                "join_list_exact_TEST",
                exact_count == 1,
                f"TEST件数={exact_count} labels={labels[:8]}",
            )
        )

        if has_test:
            for o in options:
                if (o.get("t") or "").strip() == room_name:
                    page_b.select_option("#drillRoomSelect", o["v"])
                    break
            page_b.fill("#drillJoinCodeInput", room_code)
            shot(page_b, "11_join_selected")
            page_b.click("text=選択ルームに参加")
            page_b.wait_for_function(
                """() => {
                    const el = document.getElementById('drillStatusMsg');
                    return el && el.textContent && el.textContent.includes('参加');
                }""",
                timeout=20000,
            )
            shot(page_b, "12_join_done")
            status_b = page_b.locator("#drillStatusMsg").inner_text()
            results.append(("join_ok", "参加" in status_b, status_b))
            page_b.click("#btnRider")
            page_b.click("text=登録して開始")
            page_b.wait_for_selector("#display", state="visible", timeout=20000)
            page_b.wait_for_timeout(2000)
            presence_b = page_b.locator("#alliancePresenceLine").inner_text()
            shot(page_b, "13_joiner_presence_line")
            joiner_sees_staff = "参謀" in presence_b and "ブラウザ参謀" in presence_b
            results.append(("joiner_presence_staff", joiner_sees_staff, presence_b[:100]))
        else:
            shot(page_b, "11_FAIL_no_TEST")
            results.append(("join_ok", False, "TESTが一覧に無い"))

        report = {
            "url": url,
            "room_name": room_name,
            "room_code": room_code,
            "results": [{"id": a, "ok": b, "note": c} for a, b, c in results],
            "pass": all(b for _, b, _ in results),
            "screenshots_dir": str(LOG_DIR),
        }
        out = LOG_DIR / "last_browser_qa.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\n=== 結果 ===", flush=True)
        for rid, ok, note in results:
            print(f"  [{'OK' if ok else 'NG'}] {rid}: {note}", flush=True)
        print(f"\nレポート: {out}", flush=True)
        if headed:
            print("ブラウザは10秒後に閉じます（スクリーンショットを確認してください）", flush=True)
            page_b.wait_for_timeout(10000)

        browser.close()
        return 0 if report["pass"] else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="")
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()
    try:
        return run(load_url(args.url), headed=not args.headless)
    except Exception as e:
        print(f"FAIL: {e}", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

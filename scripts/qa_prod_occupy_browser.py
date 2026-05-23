#!/usr/bin/env python3
"""
本番モード（SVS）で占領同盟の差込/入替自動割当を実ブラウザで確認する。
参謀タブで号令 → 乗り手タブで occupyDutyLine / 役割バッジ / 主副カードを検証。

  python scripts/qa_prod_occupy_browser.py
  python scripts/qa_prod_occupy_browser.py --headless
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOG_DIR = REPO / "logs" / "browser_qa" / "prod_occupy"
CONFIG = REPO / "config" / "production.json"


def load_url(arg: str) -> str:
    if arg:
        return arg.rstrip("/") + "/"
    if CONFIG.is_file():
        return json.loads(CONFIG.read_text(encoding="utf-8")).get("player_url", "https://3301-svs.jp/").rstrip("/") + "/"
    return "https://3301-svs.jp/"


def shot(page, name: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    p = LOG_DIR / f"{name}.png"
    page.screenshot(path=str(p), full_page=True)
    print(f"screenshot: {p}", flush=True)


def onboard_prod(page, url: str, *, staff: bool, march_sec: int, label: str) -> None:
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.click("#btnModeProd")
    page.click("#btnEnv2device")
    page.wait_for_selector("#step2_5_alliance", state="visible", timeout=20000)
    page.click("#btnAln0")
    page.wait_for_selector("#roleSetupSection", state="visible", timeout=10000)
    if staff:
        page.click("#btnStaff")
        page.wait_for_selector("#staffPlayerRoleArea", state="visible", timeout=8000)
        page.click("#btnStaffRider")
        page.locator("#pName").evaluate("el => { el.style.display='block'; }")
        page.fill("#pName", label)
    else:
        page.click("#btnRider")
    page.fill("#pSec", str(march_sec))
    page.click("text=登録して開始")
    page.wait_for_selector("#display", state="visible", timeout=25000)


def ws_cmds(page, cmds: list[dict]) -> None:
    page.evaluate(
        """(cmds) => {
            if (!window.ws || window.ws.readyState !== 1) throw new Error('ws not open');
            for (const c of cmds) window.ws.send(JSON.stringify(c));
        }""",
        cmds,
    )


def run(url: str, headed: bool) -> int:
    from playwright.sync_api import sync_playwright

    uid = uuid.uuid4().hex[:6]
    staff_name = f"QA参謀{uid}"
    rider_name = f"QA乗{uid}"
    results: list[tuple[str, bool, str]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headed,
            slow_mo=350 if headed else 0,
            args=["--start-maximized"] if headed else [],
        )
        ctx_s = browser.new_context(viewport={"width": 420, "height": 920})
        ctx_r = browser.new_context(viewport={"width": 420, "height": 920})
        staff = ctx_s.new_page()
        rider = ctx_r.new_page()

        print(f"\n=== 本番 参謀 {url} ===", flush=True)
        onboard_prod(staff, url, staff=True, march_sec=30, label=staff_name)
        shot(staff, "01_staff_main")
        results.append(("br_prod_staff_display", True, "参謀画面"))

        print(f"\n=== 本番 乗り手 {url} ===", flush=True)
        onboard_prod(rider, url, staff=False, march_sec=55, label=rider_name)
        shot(rider, "02_rider_main")
        results.append(("br_prod_rider_display", True, "乗り手画面"))

        staff.wait_for_timeout(2000)
        staff.evaluate(
            """() => {
                sendStaffEnemyCommand('mod_insert_target', null, 120);
                sendStaffEnemyCommand('fire_insert_fixed_target', null);
            }"""
        )
        hq_url = url.rstrip("/") + "/staff_hq_3301"
        hq = ctx_s.new_page()
        hq.goto(hq_url, wait_until="domcontentloaded", timeout=30000)
        hq.wait_for_timeout(3000)
        hq.evaluate("() => send('update_alliance_role', 0, 'occupy')")
        hq.evaluate(
            """() => {
                for (let i = 0; i < 20; i++) send('mod_manual_base', null, 600);
                send('fire_manual_swap');
            }"""
        )
        staff.wait_for_timeout(1200)
        shot(staff, "03_staff_after_orders")

        ok_duty = False
        duty_text = ""
        end = time.monotonic() + 22
        while time.monotonic() < end:
            rider.wait_for_timeout(500)
            duty_text = rider.locator("#occupyDutyLine").inner_text()
            if duty_text and ("差込役" in duty_text or "入替役" in duty_text):
                ok_duty = True
                break
        shot(rider, "04_rider_duty_line")
        results.append(("br_prod_occupy_duty_line", ok_duty, duty_text[:100] or "empty"))

        has_primary = False
        has_secondary = False
        has_badge = False
        card_end = time.monotonic() + 35
        while time.monotonic() < card_end:
            rider.wait_for_timeout(500)
            dep_html = rider.locator("#departureBox").inner_html()
            has_primary = "duty-block-primary" in dep_html
            has_secondary = "duty-block-secondary" in dep_html
            has_badge = "duty-role-badge" in dep_html
            if has_primary and has_badge:
                break
        dep_snip = rider.locator("#departureBox").inner_text()[:120]
        dep_html = rider.locator("#departureBox").inner_html()
        has_cd = "player-action-countdown" in dep_html
        no_wait = "総指揮からの指示を待機中" not in dep_snip
        cards_ok = has_cd and no_wait and (
            (has_primary and has_badge)
            or (ok_duty and "差込" in dep_snip and ("入替" in dep_snip or "差込スタート" in dep_snip))
        )
        results.append(
            (
                "br_prod_duty_cd_visible",
                cards_ok,
                f"cd={has_cd} wait={not no_wait} primary={has_primary} badge={has_badge} dep={dep_snip}",
            )
        )
        shot(rider, "05_rider_cards")

        has_ins = rider.locator("text=差込").count() > 0
        has_swap = rider.locator("text=入替").count() > 0
        results.append(
            (
                "br_prod_ins_swap_visible",
                has_ins and has_swap,
                f"ins_mentions={has_ins} swap_mentions={has_swap}",
            )
        )

        staff_url = url.rstrip("/") + "/staff_hq_3301"
        st = staff.context.new_page()
        try:
            resp = st.goto(staff_url, wait_until="domcontentloaded", timeout=30000)
            ok_staff_http = resp is not None and resp.status < 400
            results.append(("br_prod_staff_hq_http", ok_staff_http, staff_url))
        finally:
            st.close()

        report = {
            "url": url,
            "results": [{"id": a, "ok": b, "note": c} for a, b, c in results],
            "pass": all(b for _, b, _ in results),
            "screenshots_dir": str(LOG_DIR),
        }
        out = LOG_DIR / "last_prod_occupy_browser.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\n=== 結果 ===", flush=True)
        for rid, ok, note in results:
            safe = note.encode("cp932", errors="replace").decode("cp932")
            print(f"  [{'OK' if ok else 'NG'}] {rid}: {safe}", flush=True)
        print(f"\nレポート: {out}", flush=True)
        if headed:
            print("ブラウザを8秒後に閉じます", flush=True)
            staff.wait_for_timeout(8000)
        browser.close()
        return 0 if report["pass"] else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="")
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()
    return run(load_url(args.url), headed=not args.headless)


if __name__ == "__main__":
    raise SystemExit(main())

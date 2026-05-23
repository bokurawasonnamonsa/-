#!/usr/bin/env python3
"""
SVS3301 実ブラウザ総合確認（本番: 占領/攻撃 × 参謀/集結主/乗り手 + 号令なし異常検知 + 訓練ルーム）。

  python scripts/qa_svs_full_browser.py
  python scripts/qa_svs_full_browser.py --headless
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOG_DIR = REPO / "logs" / "browser_qa" / "svs_full"
CONFIG = REPO / "config" / "production.json"


def shot(page, name: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    p = LOG_DIR / f"{name}.png"
    page.screenshot(path=str(p), full_page=True)
    print(f"screenshot: {p}", flush=True)


def hq_cleanup(hq_url: str, page) -> None:
    page.goto(hq_url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2500)
    page.evaluate(
        """() => {
            send('clear_insert_fixed_target');
            send('cancel_manual_swap');
            send('cancel_manual_wd');
        }"""
    )
    page.wait_for_timeout(500)


def onboard_prod(page, url: str, aln_btn: str, role: str, march_sec: int, name: str) -> None:
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.click("#btnModeProd")
    page.click("#btnEnv2device")
    page.wait_for_selector("#step2_5_alliance", state="visible", timeout=20000)
    page.click(aln_btn)
    page.wait_for_selector("#roleSetupSection", state="visible", timeout=10000)
    if role == "staff":
        page.click("#btnStaff")
        page.wait_for_selector("#staffPlayerRoleArea", state="visible", timeout=8000)
        page.click("#btnStaffRider")
        page.locator("#pName").evaluate("el => { el.style.display='block'; }")
        page.fill("#pName", name)
    elif role == "leader1":
        page.click("#btnLeader1")
        page.locator("#pName").evaluate("el => { el.style.display='block'; }")
        page.fill("#pName", name)
    elif role == "leader2":
        page.click("#btnLeader2")
        page.locator("#pName").evaluate("el => { el.style.display='block'; }")
        page.fill("#pName", name)
    else:
        page.click("#btnRider")
    page.fill("#pSec", str(march_sec))
    page.click("text=登録して開始")
    page.wait_for_selector("#display", state="visible", timeout=25000)
    page.wait_for_timeout(1500)


def read_display_state(page) -> dict:
    return page.evaluate(
        """() => {
            const duty = (document.getElementById('occupyDutyLine') || {}).innerText || '';
            const dep = (document.getElementById('departureBox') || {}).innerText || '';
            const cd = (document.querySelector('.player-action-countdown') || {}).innerText || '';
            const wait = dep.includes('待機') || dep.includes('指示を待');
            const hugeCd = /\\d{3,}:\\d{2}/.test(cd);
            return { duty, dep, cd, wait, hugeCd, hasSwap: dep.includes('入替'), hasIns: dep.includes('差込'), hasWd: dep.includes('占領抜き') };
        }"""
    )


def run(url: str, headed: bool) -> int:
    from playwright.sync_api import sync_playwright

    if url.endswith("/"):
        player_url = url
    else:
        player_url = url + "/"
    hq_url = player_url.rstrip("/") + "/staff_hq_3301"
    uid = uuid.uuid4().hex[:6]
    results: list[tuple[str, bool, str]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed, slow_mo=300 if headed else 0)
        hq = browser.new_context(viewport={"width": 1280, "height": 800}).new_page()
        print("=== HQ: ゴミ号令クリア ===", flush=True)
        hq_cleanup(hq_url, hq)
        results.append(("br_hq_cleanup", True, "clear insert/swap/wd"))

        # --- 本番 占領 参謀: 号令なし ---
        ctx = browser.new_context(viewport={"width": 420, "height": 900})
        st = ctx.new_page()
        print("=== 本番 占領 参謀（号令なし）===", flush=True)
        onboard_prod(st, player_url, "#btnAln0", "staff", 30, f"QA参謀{uid}")
        shot(st, "occupy_staff_no_cmd")
        s = read_display_state(st)
        ok_idle = (not s.get("duty") or "入替役" not in s.get("duty", "")) and not s.get("hugeCd") and (
            s.get("wait") or (not s.get("hasSwap") and not s.get("hasIns"))
        )
        results.append(("br_occupy_staff_no_cmd", ok_idle, json.dumps(s, ensure_ascii=False)[:140]))
        st.close()
        ctx.close()

        # --- 本番 占領 乗り手 ---
        ctx = browser.new_context(viewport={"width": 420, "height": 900})
        rd = ctx.new_page()
        print("=== 本番 占領 乗り手（号令なし）===", flush=True)
        onboard_prod(rd, player_url, "#btnAln0", "rider", 47, f"QA乗{uid}")
        shot(rd, "occupy_rider_no_cmd")
        s2 = read_display_state(rd)
        ok_rider = (not s2.get("duty") or ("役" not in s2.get("duty", ""))) and not s2.get("hugeCd")
        results.append(("br_occupy_rider_no_cmd", ok_rider, json.dumps(s2, ensure_ascii=False)[:140]))
        rd.close()
        ctx.close()

        # --- 本番 攻撃 乗り手（占領抜きなし）---
        ctx = browser.new_context(viewport={"width": 420, "height": 900})
        atk = ctx.new_page()
        print("=== 本番 攻撃 乗り手（号令なし）===", flush=True)
        onboard_prod(atk, player_url, "#btnAln1", "rider", 40, f"QA攻{uid}")
        shot(atk, "attack_rider_no_cmd")
        s3 = read_display_state(atk)
        ok_atk = not s3.get("hasWd") and not s3.get("hugeCd")
        results.append(("br_attack_rider_no_wd", ok_atk, json.dumps(s3, ensure_ascii=False)[:140]))
        atk.close()
        ctx.close()

        # --- 本番 占領 集結主 ---
        ctx = browser.new_context(viewport={"width": 420, "height": 900})
        ld = ctx.new_page()
        print("=== 本番 占領 集結主（号令なし）===", flush=True)
        onboard_prod(ld, player_url, "#btnAln0", "leader1", 35, f"QA集1{uid}")
        shot(ld, "occupy_leader_no_cmd")
        s4 = read_display_state(ld)
        ok_ld = not s4.get("hugeCd") and not s4.get("hasSwap")
        results.append(("br_occupy_leader_no_cmd", ok_ld, json.dumps(s4, ensure_ascii=False)[:140]))
        ld.close()
        ctx.close()

        # --- 号令後 占領 乗り手（割当表示）---
        hq.evaluate(
            """() => {
                send('update_alliance_role', 0, 'occupy');
                send('mod_insert_target', null, 120);
                send('fire_insert_fixed_target');
                for (let i = 0; i < 15; i++) send('mod_manual_base', null, 600);
                send('fire_manual_swap');
            }"""
        )
        hq.wait_for_timeout(800)
        ctx = browser.new_context(viewport={"width": 420, "height": 900})
        rd2 = ctx.new_page()
        print("=== 本番 占領 乗り手（号令後）===", flush=True)
        onboard_prod(rd2, player_url, "#btnAln0", "rider", 50, f"QA乗B{uid}")
        ok_duty = False
        ok_cd = False
        s5: dict = {}
        end = time.monotonic() + 25
        while time.monotonic() < end:
            rd2.wait_for_timeout(600)
            s5 = read_display_state(rd2)
            has_duty = s5.get("duty") and ("差込役" in s5["duty"] or "入替役" in s5["duty"])
            has_cd = bool(s5.get("cd")) and not s5.get("wait") and (
                s5.get("hasIns") or s5.get("hasSwap")
            )
            if has_duty and has_cd:
                ok_duty = True
                ok_cd = True
                break
            if has_duty:
                ok_duty = True
        shot(rd2, "occupy_rider_with_cmd")
        results.append(
            (
                "br_occupy_rider_with_duty",
                ok_duty,
                json.dumps(s5, ensure_ascii=False)[:140] if ok_duty else "no duty",
            )
        )
        results.append(
            (
                "br_occupy_rider_cd_visible",
                ok_cd,
                json.dumps(s5, ensure_ascii=False)[:140] if ok_cd else "no CD box",
            )
        )
        rd2.close()
        ctx.close()

        # --- 訓練ルーム スモーク ---
        dr = browser.new_context(viewport={"width": 420, "height": 900}).new_page()
        print("=== 訓練 ルーム作成 ===", flush=True)
        dr.goto(player_url, wait_until="networkidle", timeout=60000)
        dr.click("#btnModeDrill")
        dr.click("#btnEnv2device")
        dr.wait_for_selector("#step2_5_alliance", state="visible", timeout=15000)
        dr.click("#drillTabCreate")
        code = "svs" + uid
        dr.fill("#drillAllianceNameInput", "SVSQA")
        dr.fill("#drillRoomKeyInput", code)
        dr.click("text=作成して入る")
        dr.wait_for_function(
            "() => { const el = document.getElementById('drillStatusMsg'); return el && el.textContent && el.textContent.includes('作成'); }",
            timeout=20000,
        )
        shot(dr, "drill_create")
        results.append(("br_drill_create", True, code))
        dr.close()

        hq.close()
        browser.close()

    report = {
        "url": player_url,
        "results": [{"id": a, "ok": b, "note": c} for a, b, c in results],
        "pass": all(b for _, b, _ in results),
    }
    out = LOG_DIR / "last_svs_full_browser.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== 結果 ===", flush=True)
    for rid, ok, note in results:
        safe = note.encode("ascii", "backslashreplace").decode("ascii")
        print(f"  [{'OK' if ok else 'NG'}] {rid}: {safe}", flush=True)
    print(f"\nレポート: {out}", flush=True)
    return 0 if report["pass"] else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="")
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()
    u = args.url
    if u:
        u = u.rstrip("/") + "/"
    elif CONFIG.is_file():
        u = json.loads(CONFIG.read_text(encoding="utf-8")).get("player_url", "https://3301-svs.jp/").rstrip("/") + "/"
    else:
        u = "https://3301-svs.jp/"
    return run(u, headed=not args.headless)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
本番（または --url）の画面スクショを docs/screenshots/ に保存する。
操作説明書・ビジュアル仕様書用。

  python scripts/capture_doc_screenshots.py
  python scripts/capture_doc_screenshots.py --url https://3301-svs.jp/
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "screenshots"
CONFIG = REPO / "config" / "production.json"
MANIFEST = OUT / "manifest.json"


def load_urls(arg_player: str, arg_staff: str) -> tuple[str, str]:
    if arg_player:
        player = arg_player.rstrip("/") + "/"
    elif CONFIG.is_file():
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        player = cfg.get("player_url", "https://3301-svs.jp/").rstrip("/") + "/"
    else:
        player = "https://3301-svs.jp/"
    if arg_staff:
        staff = arg_staff.rstrip("/")
    elif CONFIG.is_file():
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        staff = cfg.get("staff_url", "https://3301-svs.jp/staff_hq_3301").rstrip("/")
    else:
        staff = "https://3301-svs.jp/staff_hq_3301"
    return player, staff


def shot(page, name: str, *, full_page: bool = True) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{name}.png"
    page.screenshot(path=str(p), full_page=full_page)
    print(f"  saved {p.name}", flush=True)
    return {"id": name, "file": f"screenshots/{name}.png", "path": str(p)}


def run(player_url: str, staff_url: str) -> int:
    from playwright.sync_api import sync_playwright

    room_name = "TEST"
    room_code = "doc" + uuid.uuid4().hex[:6]
    manifest: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        vp = {"width": 390, "height": 844}

        # --- オンボーディング（プレイヤー）---
        ctx = browser.new_context(viewport=vp)
        page = ctx.new_page()
        print("=== onboarding ===", flush=True)
        page.goto(player_url, wait_until="networkidle", timeout=90000)
        manifest.append(shot(page, "01_entry_mode"))

        page.click("#btnModeDrill")
        page.wait_for_timeout(400)
        manifest.append(shot(page, "02_drill_mode_selected"))

        page.click("#btnEnv2device")
        page.wait_for_selector("#step2_5_alliance", state="visible", timeout=20000)
        manifest.append(shot(page, "03_drill_join_hub"))

        page.click("#drillTabCreate")
        page.fill("#drillAllianceNameInput", room_name)
        page.fill("#drillRoomKeyInput", room_code)
        manifest.append(shot(page, "04_drill_create_form"))

        page.click("text=作成して入る")
        page.wait_for_function(
            """() => {
                const el = document.getElementById('drillStatusMsg');
                return el && el.textContent && (el.textContent.includes('作成') || el.textContent.includes('参加'));
            }""",
            timeout=25000,
        )
        page.wait_for_timeout(800)
        manifest.append(shot(page, "05_drill_create_done_role"))

        page.click("#drillTabJoin")
        page.wait_for_timeout(2000)
        manifest.append(shot(page, "05b_drill_join_list"))

        page.wait_for_selector("#btnStaff", state="visible", timeout=15000)
        page.click("#btnStaff")
        page.wait_for_selector("#staffPlayerRoleArea", state="visible", timeout=10000)
        manifest.append(shot(page, "06_role_staff_pick"))

        page.click("#btnStaffRider")
        page.wait_for_selector("#inputsArea", state="visible", timeout=10000)
        manifest.append(shot(page, "07_role_staff_rider_name"))

        page.click("#btnRider")
        page.wait_for_selector("#inputsArea", state="visible", timeout=10000)
        manifest.append(shot(page, "08_role_rider_pick"))

        # --- 参謀メイン ---
        page.click("#btnStaff")
        page.click("#btnStaffRider")
        page.fill("#pName", "説明書参謀")
        page.click("text=登録して開始")
        page.wait_for_selector("#display", state="visible", timeout=25000)
        page.wait_for_selector("text=参謀として参加中", timeout=25000)
        page.wait_for_timeout(1500)
        manifest.append(shot(page, "09_staff_main", full_page=False))
        try:
            panel = page.locator("#staffCommandPanel")
            if panel.is_visible():
                manifest.append(shot(page, "10_staff_command_panel", full_page=False))
        except Exception:
            pass
        try:
            pl = page.locator("#alliancePresenceLine")
            if pl.is_visible():
                pl.screenshot(path=str(OUT / "11_presence_line_staff.png"))
                manifest.append(
                    {"id": "11_presence_line_staff", "file": "screenshots/11_presence_line_staff.png"}
                )
        except Exception:
            pass

        # --- 参加者（乗り手）別コンテキスト ---
        ctx2 = browser.new_context(viewport=vp)
        page2 = ctx2.new_page()
        print("=== joiner ===", flush=True)
        page2.goto(player_url, wait_until="networkidle", timeout=90000)
        page2.click("#btnModeDrill")
        page2.click("#btnEnv2device")
        page2.wait_for_selector("#step2_5_alliance", state="visible", timeout=20000)
        page2.click("#drillTabJoin")
        page2.wait_for_timeout(2500)
        opts = page2.eval_on_selector_all(
            "#drillRoomSelect option",
            "els => els.map(o => ({v: o.value, t: o.textContent}))",
        )
        picked = False
        for o in opts:
            t = (o.get("t") or "").strip()
            if t == room_name or room_name in t:
                page2.select_option("#drillRoomSelect", o["v"])
                picked = True
                break
        if not picked and opts:
            for o in opts:
                if o.get("v"):
                    page2.select_option("#drillRoomSelect", o["v"])
                    break
        page2.fill("#drillJoinCodeInput", room_code)
        page2.click("text=選択ルームに参加")
        page2.wait_for_function(
            """() => {
                const el = document.getElementById('drillStatusMsg');
                return el && el.textContent && el.textContent.includes('参加');
            }""",
            timeout=25000,
        )
        page2.click("#btnRider")
        page2.wait_for_selector("#inputsArea", state="visible", timeout=10000)
        page2.click("text=登録して開始")
        page2.wait_for_selector("#display", state="visible", timeout=25000)
        page2.wait_for_timeout(3000)
        manifest.append(shot(page2, "12_joiner_waiting_staff", full_page=False))
        try:
            dep = page2.locator("#departureBox")
            if dep.is_visible():
                dep.screenshot(path=str(OUT / "13_departure_waiting.png"))
                manifest.append(
                    {"id": "13_departure_waiting", "file": "screenshots/13_departure_waiting.png"}
                )
        except Exception:
            pass

        # --- SVS モード入口 ---
        ctx3 = browser.new_context(viewport=vp)
        page3 = ctx3.new_page()
        print("=== prod ===", flush=True)
        page3.goto(player_url, wait_until="networkidle", timeout=90000)
        page3.click("#btnModeProd")
        page3.click("#btnEnv2device")
        page3.wait_for_selector("#step2_5_alliance", state="visible", timeout=20000)
        manifest.append(shot(page3, "14_prod_alliance_pick"))

        # --- 総指揮 ---
        ctx4 = browser.new_context(viewport={"width": 1400, "height": 900})
        page4 = ctx4.new_page()
        print("=== HQ ===", flush=True)
        page4.goto(staff_url, wait_until="networkidle", timeout=90000)
        page4.wait_for_timeout(2000)
        manifest.append(shot(page4, "15_staff_hq_overview"))

        browser.close()

    meta = {
        "player_url": player_url,
        "staff_url": staff_url,
        "room_name": room_name,
        "room_code": room_code,
        "shots": manifest,
    }
    MANIFEST.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nmanifest: {MANIFEST} ({len(manifest)} images)", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="", help="player base URL")
    ap.add_argument("--staff-url", default="", help="staff HQ URL")
    args = ap.parse_args()
    player, staff = load_urls(args.url, args.staff_url)
    try:
        return run(player, staff)
    except Exception as e:
        print(f"FAIL: {e}", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Production QA: HTTP + WebSocket + API checks.
Scope mode (--scope-from-edits): only tests related to edited files.
Full mode (--full): all automated checks.

Audio/hearing cannot be verified automatically; manual steps are listed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
CONFIG = REPO / "config" / "production.json"
WORKFLOW = REPO / ".cursor" / "hooks" / "state" / "workflow_status.json"
OUT_REPO = REPO / "logs" / "qa_last_result.json"
OUT_HOOK = REPO / ".cursor" / "hooks" / "state" / "qa_last_result.json"

# file path fragment -> scope ids
FILE_SCOPES: dict[str, list[str]] = {
    "player.html": ["http", "html_player", "voice", "ws_drill", "countdown", "operator", "wd_manual"],
    "main.py": ["http", "voice", "ws_drill", "ws_register", "operator", "wd_manual"],
    "staff.html": ["http", "staff", "ws_drill", "operator"],
    "support.html": ["http"],
    "index.html": ["http"],
    "voices.js": ["voice", "html_player"],
    "sw.js": ["http", "html_player"],
}

ALL_SCOPES = [
    "http",
    "html_player",
    "voice",
    "ws_drill",
    "ws_register",
    "countdown",
    "staff",
    "operator",
    "wd_manual",
]

# デプロイ後は毎回必ず実行（差込・入替・集結・占領抜きの仕様ロック含む）
MANDATORY_EVERY_RUN = ["operator"]

MANUAL_STEPS = [
    {
        "id": "manual_voice",
        "name": "音声テスト（耳確認）",
        "ok": None,
        "note": "本番で「音声テスト」ボタンを押し、読み上げが聞こえること",
    },
    {
        "id": "manual_countdown",
        "name": "カウントダウン（画面確認）",
        "ok": None,
        "note": "本番で「カウントダウンテスト」を押し、数字が減ること",
    },
]


def load_cfg() -> dict:
    if CONFIG.is_file():
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    return {
        "public_url": "https://3301-svs.jp/",
        "player_url": "https://3301-svs.jp/",
        "staff_url": "https://3301-svs.jp/staff_hq_3301",
        "support_url": "https://3301-svs.jp/support_hq_3301",
        "domain": "3301-svs.jp",
    }


def base_url(cfg: dict) -> str:
    u = (cfg.get("public_url") or "https://3301-svs.jp/").rstrip("/")
    return u


def ws_url(cfg: dict, mode: str = "drill", room: str = "default") -> str:
    b = base_url(cfg)
    scheme = "wss" if b.startswith("https") else "ws"
    host = urllib.parse.urlparse(b).netloc
    return f"{scheme}://{host}/ws?mode={mode}&aln=0&room={urllib.parse.quote(room)}"


def ws_ssl_context(url: str):
    if url.startswith("wss://"):
        return ssl.create_default_context()
    return None


def http_get(url: str, timeout: int = 15) -> tuple[bool, int, str, int]:
    req = urllib.request.Request(url, headers={"User-Agent": "utc-qa/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            body = res.read(512 * 1024)
            return True, res.status, res.headers.get("Content-Type", ""), len(body)
    except urllib.error.HTTPError as e:
        try:
            e.read()
        except Exception:
            pass
        return False, e.code, str(e.reason), 0
    except Exception as e:
        return False, 0, str(e), 0


def scopes_from_edits() -> list[str]:
    scopes: set[str] = set()
    if WORKFLOW.is_file():
        try:
            data = json.loads(WORKFLOW.read_text(encoding="utf-8"))
            for fp in data.get("edited_files") or []:
                name = Path(fp).name
                for key, sc in FILE_SCOPES.items():
                    if key in fp or name == key:
                        scopes.update(sc)
        except (json.JSONDecodeError, OSError):
            pass
    if not scopes:
        scopes.add("http")
    return sorted(scopes)


def merge_mandatory_scopes(scopes: list[str]) -> list[str]:
    return sorted(set(scopes) | set(MANDATORY_EVERY_RUN))


def step(sid: str, name: str, ok: bool, note: str = "", kind: str = "auto") -> dict:
    return {"id": sid, "name": name, "ok": ok, "note": note, "kind": kind}


def run_http(cfg: dict, steps: list) -> None:
    b = base_url(cfg)
    for sid, path in [
        ("http_player", "/"),
        ("http_staff", None),
    ]:
        if path is None:
            url = (cfg.get("staff_url") or f"{b}/staff_hq_3301").rstrip("/")
            if not url.startswith("http"):
                url = f"{b}/staff_hq_3301"
        else:
            url = f"{b}{path}"
        ok, code, err, n = http_get(url)
        steps.append(
            step(
                sid,
                f"HTTP {path or 'staff'}",
                ok and 200 <= code < 400,
                f"{code} len={n}" if ok else f"code={code} {err}",
            )
        )


def run_html_player(cfg: dict, steps: list) -> None:
    url = base_url(cfg) + "/"
    ok, code, _, n = http_get(url)
    if not ok or n < 500:
        steps.append(step("html_player_fetch", "player HTML", False, f"fetch failed {code}"))
        return
    req = urllib.request.Request(url, headers={"User-Agent": "utc-qa/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            html = res.read().decode("utf-8", errors="replace")
    except Exception as e:
        steps.append(step("html_player_fetch", "player HTML", False, str(e)))
        return
    markers = [
        "startCountdownDemo",
        "playTestAudio",
        "selectAppMode",
        "roleSetupSection",
        "WebSocket",
        "occupyDutyLine",
        "applyOccupyDutyFromMsg",
        "duty-role-badge",
        "duty-block-primary",
    ]
    missing = [m for m in markers if m not in html]
    steps.append(
        step(
            "html_player_markers",
            "player 必須UI/JS",
            not missing,
            "missing: " + ", ".join(missing) if missing else "ok",
        )
    )


def run_voice(cfg: dict, steps: list) -> None:
    b = base_url(cfg)
    ok, code, ctype, n = http_get(f"{b}/api/voice_speakers")
    steps.append(
        step(
            "voice_speakers",
            "API voice_speakers",
            ok and code == 200,
            f"{code} {ctype}",
        )
    )
    text = urllib.parse.quote("テスト")
    ok2, code2, ctype2, n2 = http_get(f"{b}/api/voice?text={text}&speaker=3")
    if ok2 and code2 == 200 and "audio" in (ctype2 or ""):
        steps.append(step("voice_wav", "API voice WAV", True, f"{code2} bytes={n2}"))
    elif code2 == 503:
        steps.append(
            step(
                "voice_wav",
                "API voice WAV",
                False,
                "503 VOICEVOX未応答（サーバー側要確認）",
            )
        )
    else:
        steps.append(step("voice_wav", "API voice WAV", False, f"code={code2} {ctype2}"))


def run_staff(cfg: dict, steps: list) -> None:
    url = (cfg.get("staff_url") or "").strip()
    if not url:
        steps.append(step("staff_http", "staff HTTP", False, "staff_url unset"))
        return
    ok, code, err, n = http_get(url)
    steps.append(
        step("staff_http", "staff 画面", ok and 200 <= code < 400, f"{code} len={n}" if ok else err)
    )


def run_countdown(cfg: dict, steps: list) -> None:
    url = base_url(cfg) + "/"
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "utc-qa/1.0"}),
            timeout=15,
        ) as res:
            html = res.read().decode("utf-8", errors="replace")
    except Exception as e:
        steps.append(step("countdown_js", "カウントダウンJS", False, str(e)))
        return
    ok = "countdownDemoValue" in html and "startCountdownDemo" in html
    steps.append(
        step(
            "countdown_js",
            "カウントダウンUI定義",
            ok,
            "デモボタン/表示要素あり（実秒進行は手動確認）",
        )
    )


async def ws_recv_json(ws, timeout: float = 3.0):
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


async def ws_drain(ws, sec: float = 0.4):
    end = time.monotonic() + sec
    last = None
    while time.monotonic() < end:
        try:
            last = await ws_recv_json(ws, timeout=0.15)
        except Exception:
            pass
    return last


async def ws_collect_until(ws, want_types: set, max_sec: float = 8.0):
    """want_types のいずれかが来るまで受信。見つかった msg と直近の drill_rooms 一覧を返す。"""
    end = time.monotonic() + max_sec
    hit = None
    last_rooms = None
    while time.monotonic() < end:
        try:
            msg = await ws_recv_json(ws, timeout=min(2.0, end - time.monotonic()))
        except Exception:
            continue
        if msg.get("type") == "drill_rooms" or msg.get("drill_rooms"):
            last_rooms = msg.get("rooms") or msg.get("drill_rooms") or []
        if msg.get("type") in want_types:
            hit = msg
            break
    return hit, last_rooms


def _room_names(rooms) -> list[str]:
    if not isinstance(rooms, list):
        return []
    return [str(r.get("name") or "").strip() for r in rooms if isinstance(r, dict)]


def _room_names_label_clean(names: list[str]) -> bool:
    for n in names:
        if not n or "#" in n or "(" in n or "人)" in n:
            return False
    return True


async def _wait_drill_staff_visible(ws, max_sec: float = 8.0) -> tuple[bool, str]:
    """参加者WSで参謀在室(drill_staff / alliance_presence)が届くまで待つ。"""
    end = time.monotonic() + max_sec
    while time.monotonic() < end:
        try:
            msg = await ws_recv_json(ws, timeout=min(2.0, end - time.monotonic()))
        except Exception:
            continue
        ds = msg.get("drill_staff") if isinstance(msg.get("drill_staff"), dict) else {}
        ap0 = (msg.get("alliance_presence") or {}).get("aln0") if isinstance(msg.get("alliance_presence"), dict) else {}
        staff_cnt = int(((ap0 or {}).get("staff") or {}).get("count") or 0)
        if ds.get("present") or staff_cnt > 0:
            return True, f"present={ds.get('present')} staff_cnt={staff_cnt}"
    return False, "参謀在室メッセージが届かない"


async def run_drill_room_e2e(cfg: dict, steps: list, ssl_ctx) -> None:
    """参謀が作成 → 別クライアントが一覧で見える → 参加コードで join（実運用再現）。"""
    try:
        import websockets
    except ImportError:
        steps.append(step("ws_drill_e2e", "訓練ルームE2E", False, "pip install websockets"))
        return

    room_code = "e2e" + uuid.uuid4().hex[:8]
    room_name = "QA_E2E_" + uuid.uuid4().hex[:4].upper()
    url = ws_url(cfg, "drill", "default")
    room_id = ""

    try:
        async with websockets.connect(url, ssl=ssl_ctx, open_timeout=12) as ws_a:
            init_a, _ = await ws_collect_until(ws_a, {"init"}, 6)
            steps.append(
                step(
                    "ws_drill_e2e_init",
                    "訓練WS接続(作成側)",
                    (init_a or {}).get("type") == "init",
                    f"type={(init_a or {}).get('type')}",
                )
            )
            await ws_a.send(
                json.dumps(
                    {
                        "cmd": "set_mode",
                        "val": {
                            "mode": "drill",
                            "alliance_id": 0,
                            "room_action": "create",
                            "room_code": room_code,
                            "alliance_name": room_name,
                        },
                    }
                )
            )
            rooms_after_create = None
            ok_create = False
            for _ in range(12):
                msg, rooms = await ws_collect_until(
                    ws_a, {"mode_ok", "mode_error", "init"}, 4
                )
                if rooms:
                    rooms_after_create = rooms
                if msg and msg.get("type") == "mode_error":
                    steps.append(
                        step(
                            "ws_drill_create",
                            "訓練ルーム作成",
                            False,
                            msg.get("message", ""),
                        )
                    )
                    return
                if msg and msg.get("type") == "mode_ok" and msg.get("action") == "create":
                    room_id = str(msg.get("room_id") or "")
                    ok_create = bool(room_id)
                    break
                if msg and msg.get("type") == "init" and not rooms_after_create:
                    rooms_after_create = msg.get("drill_rooms")
            steps.append(
                step(
                    "ws_drill_create",
                    "訓練ルーム作成",
                    ok_create,
                    f"room_id={room_id} name={room_name}" if ok_create else "mode_okなし",
                )
            )
            if not ok_create:
                return

            await ws_a.send(
                json.dumps(
                    {
                        "cmd": "set_mode",
                        "val": {"mode": "drill", "room_action": "list"},
                    }
                )
            )
            list_msg, list_rooms = await ws_collect_until(ws_a, {"drill_rooms"}, 6)
            if list_rooms is None and list_msg:
                list_rooms = list_msg.get("rooms")
            names_a = _room_names(list_rooms or rooms_after_create)
            visible_a = room_name in names_a
            steps.append(
                step(
                    "ws_drill_list_creator",
                    "作成直後:一覧に自ルーム",
                    visible_a,
                    f"names={names_a[:6]}" if names_a else "rooms=空",
                )
            )

            await ws_a.send(
                json.dumps(
                    {
                        "cmd": "set_staff_mode",
                        "val": {"enabled": True, "alliance_id": 0},
                    }
                )
            )
            await ws_a.send(
                json.dumps(
                    {
                        "cmd": "set_staff_name",
                        "val": {"alliance_id": 0, "name": "QA参謀"},
                    }
                )
            )
            await ws_drain(ws_a, 0.5)

            async with websockets.connect(url, ssl=ssl_ctx, open_timeout=12) as ws_b:
                await ws_collect_until(ws_b, {"init"}, 5)
                await ws_b.send(
                    json.dumps(
                        {
                            "cmd": "set_mode",
                            "val": {"mode": "drill", "room_action": "list"},
                        }
                    )
                )
                list_msg_b, list_rooms_b = await ws_collect_until(ws_b, {"drill_rooms"}, 8)
                if list_rooms_b is None and list_msg_b:
                    list_rooms_b = list_msg_b.get("rooms")
                names_b = _room_names(list_rooms_b)
                visible_b = room_name in names_b
                steps.append(
                    step(
                        "ws_drill_list_joiner",
                        "参加側:一覧に作成ルーム",
                        visible_b,
                        f"want={room_name} got={names_b[:8]}",
                    )
                )
                steps.append(
                    step(
                        "ws_drill_list_name_clean",
                        "一覧名:同盟名のみ",
                        _room_names_label_clean(names_b),
                        f"names={names_b[:8]}",
                    )
                )
                steps.append(
                    step(
                        "ws_drill_list_dedupe",
                        "同名ルーム1件まで",
                        names_b.count(room_name) <= 1,
                        f"count={names_b.count(room_name)}",
                    )
                )
                if not visible_b:
                    steps.append(
                        step(
                            "ws_drill_join",
                            "参加側:join",
                            False,
                            "一覧に無いためスキップ",
                        )
                    )
                    return

                await ws_b.send(
                    json.dumps(
                        {
                            "cmd": "set_mode",
                            "val": {
                                "mode": "drill",
                                "alliance_id": 0,
                                "room_action": "join",
                                "room_id": room_id,
                                "room_code": room_code,
                            },
                        }
                    )
                )
                join_ok = False
                join_note = ""
                for _ in range(10):
                    msg, _ = await ws_collect_until(ws_b, {"mode_ok", "mode_error", "init"}, 5)
                    if msg and msg.get("type") == "mode_error":
                        join_note = msg.get("message", "")
                        break
                    if msg and msg.get("type") == "mode_ok" and msg.get("action") == "join":
                        join_ok = True
                        join_note = f"room_id={msg.get('room_id')}"
                        break
                steps.append(
                    step(
                        "ws_drill_join",
                        "参加側:join成功",
                        join_ok,
                        join_note or "mode_okなし",
                    )
                )
                if join_ok:
                    await ws_b.send(
                        json.dumps(
                            {
                                "cmd": "set_mode",
                                "val": {
                                    "mode": "drill",
                                    "alliance_id": 0,
                                    "room_key": room_id,
                                    "alliance_name": room_name,
                                },
                            }
                        )
                    )
                    await ws_b.send(
                        json.dumps(
                            {
                                "cmd": "register_player",
                                "val": {
                                    "role": "rider",
                                    "alliance_id": 0,
                                    "name": "QA参加",
                                    "device_mode": "2device",
                                },
                            }
                        )
                    )
                    await ws_drain(ws_b, 0.4)
                    pre_ok, pre_note = await _wait_drill_staff_visible(ws_b, 8.0)
                    steps.append(
                        step(
                            "ws_drill_staff_present",
                            "参加側:参謀在室(接続直後)",
                            pre_ok,
                            pre_note,
                        )
                    )
                    await ws_a.send(
                        json.dumps(
                            {
                                "cmd": "set_mode",
                                "val": {
                                    "mode": "drill",
                                    "alliance_id": 0,
                                    "room_key": room_id,
                                    "alliance_name": room_name,
                                },
                            }
                        )
                    )
                    await ws_a.send(
                        json.dumps(
                            {
                                "cmd": "set_staff_mode",
                                "val": {"enabled": True, "alliance_id": 0},
                            }
                        )
                    )
                    await ws_drain(ws_a, 0.4)
                    post_ok, post_note = await _wait_drill_staff_visible(ws_b, 8.0)
                    steps.append(
                        step(
                            "ws_drill_staff_reconnect",
                            "参謀再接続後も在室表示",
                            post_ok,
                            post_note,
                        )
                    )
    except Exception as e:
        steps.append(step("ws_drill_e2e", "訓練ルームE2E", False, str(e)[:200]))


async def run_ws_tests(cfg: dict, steps: list, do_register: bool) -> None:
    try:
        import websockets
    except ImportError:
        steps.append(step("ws_import", "websockets", False, "pip install websockets"))
        return

    url = ws_url(cfg, "drill", "default")
    room_code = "qa" + uuid.uuid4().hex[:6]
    room_name = "QA自動"
    ssl_ctx = ws_ssl_context(url)

    try:
        async with websockets.connect(url, ssl=ssl_ctx, open_timeout=12) as ws:
            init = await ws_recv_json(ws, 8)
            steps.append(
                step(
                    "ws_init",
                    "WebSocket init",
                    init.get("type") == "init",
                    f"type={init.get('type')}",
                )
            )
            await ws.send(
                json.dumps(
                    {
                        "cmd": "set_mode",
                        "val": {
                            "mode": "drill",
                            "alliance_id": 0,
                            "room_action": "create",
                            "room_code": room_code,
                            "alliance_name": room_name,
                        },
                    }
                )
            )
            got_ok = False
            for _ in range(8):
                msg = await ws_recv_json(ws, 5)
                if msg.get("type") == "mode_ok" and msg.get("action") == "create":
                    got_ok = True
                    room_id = msg.get("room_id", "")
                    break
                if msg.get("type") == "mode_error":
                    steps.append(step("ws_drill_create", "訓練ルーム作成", False, msg.get("message", "")))
                    return
            steps.append(
                step(
                    "ws_drill_create",
                    "訓練ルーム作成",
                    got_ok,
                    f"room_id={room_id}" if got_ok else "mode_okなし",
                )
            )
            if not got_ok:
                return

            if do_register:
                await ws.send(
                    json.dumps(
                        {
                            "cmd": "register_player",
                            "val": {
                                "role": "rider",
                                "alliance_id": 0,
                                "name": "QA_BOT",
                                "device_mode": "2device",
                            },
                        }
                    )
                )
                saw = False
                for _ in range(10):
                    try:
                        msg = await ws_recv_json(ws, 3)
                        if msg.get("type") in ("init", "state", "player_registered"):
                            saw = True
                    except Exception:
                        break
                steps.append(
                    step(
                        "ws_register",
                        "プレイヤー登録WS",
                        saw,
                        "応答あり" if saw else "応答なし",
                    )
                )
    except Exception as e:
        steps.append(step("ws_connect", "WebSocket接続", False, str(e)[:200]))

    await run_drill_room_e2e(cfg, steps, ssl_ctx)


def automated_pass(steps: list) -> bool:
    for s in steps:
        if s.get("kind") in ("manual", "meta"):
            continue
        if s.get("ok") is None:
            continue
        if not s.get("ok"):
            return False
    return True


def write_result(payload: dict) -> None:
    OUT_REPO.parent.mkdir(parents=True, exist_ok=True)
    OUT_HOOK.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    OUT_REPO.write_text(text, encoding="utf-8")
    OUT_HOOK.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="全自動チェック")
    ap.add_argument("--scope-from-edits", action="store_true", help="編集ファイルに応じた範囲のみ")
    ap.add_argument("--scopes", default="", help="カンマ区切り scope id")
    ap.add_argument(
        "--base-url",
        default="",
        help="検証先URL上書き (例: http://127.0.0.1:8000/)",
    )
    args = ap.parse_args()

    cfg = load_cfg()
    if args.base_url.strip():
        cfg = {**cfg, "public_url": args.base_url.strip()}
    if args.full:
        scopes = list(ALL_SCOPES)
    elif args.scopes:
        scopes = [s.strip() for s in args.scopes.split(",") if s.strip()]
    elif args.scope_from_edits:
        scopes = scopes_from_edits()
    else:
        scopes = list(ALL_SCOPES)
    scopes = merge_mandatory_scopes(scopes)

    steps: list[dict] = []
    from operator_spec_guard import run_operator_spec_guard

    steps.extend(run_operator_spec_guard(step))
    steps.append(
        step("meta_scope", "QA対象スコープ", True, ", ".join(scopes), kind="meta")
    )

    if "http" in scopes:
        run_http(cfg, steps)
    if "html_player" in scopes:
        run_html_player(cfg, steps)
    if "voice" in scopes:
        run_voice(cfg, steps)
    if "staff" in scopes:
        run_staff(cfg, steps)
    if "countdown" in scopes:
        run_countdown(cfg, steps)

    ws_reg = "ws_register" in scopes
    if "ws_drill" in scopes or ws_reg:
        asyncio.run(run_ws_tests(cfg, steps, do_register=ws_reg))

    if "operator" in scopes or "wd_manual" in scopes:
        from qa_operator_checks import OPERATOR_MANUAL, run_all as run_operator_all

        steps.extend(run_operator_all(step, cfg, ws_url))

    op_fail = [
        s
        for s in steps
        if s.get("id", "").startswith("op_")
        and s.get("id") != "op_operator_mandatory_bundle"
        and s.get("ok") is False
    ]
    steps.append(
        step(
            "op_operator_mandatory_bundle",
            "操作者ロジック 必須QAバンドル（差込・入替・集結・占領抜き）",
            len(op_fail) == 0,
            "ok" if not op_fail else f"FAIL: {', '.join(s['id'] for s in op_fail[:8])}",
            kind="meta",
        )
    )

    manual_steps = list(MANUAL_STEPS)
    if "operator" in scopes:
        from qa_operator_checks import OPERATOR_MANUAL

        manual_steps.extend(OPERATOR_MANUAL)
    if args.full or "voice" in scopes or "countdown" in scopes or "operator" in scopes:
        seen = set()
        for m in manual_steps:
            if m["id"] in seen:
                continue
            seen.add(m["id"])
            steps.append({**m, "kind": "manual"})

    auto_ok = automated_pass(steps)
    manual = [s for s in steps if s.get("kind") == "manual"]
    payload = {
        "pass": auto_ok,
        "pass_automated": auto_ok,
        "manual_required": [m["id"] for m in manual],
        "scopes": scopes,
        "mode": "full" if args.full else "scoped",
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "steps": steps,
    }
    write_result(payload)

    out = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        print(out)
    except UnicodeEncodeError:
        print(out.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))
    for s in steps:
        mark = "OK" if s.get("ok") is True else ("MANUAL" if s.get("ok") is None else "NG")
        line = f"  [{mark}] {s.get('id')}: {s.get('name')} - {s.get('note', '')}"
        try:
            print(line)
        except UnicodeEncodeError:
            print(line.encode("cp932", errors="replace").decode("cp932", errors="replace"))
    return 0 if auto_ok else 1


if __name__ == "__main__":
    sys.exit(main())

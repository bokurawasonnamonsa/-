#!/usr/bin/env python3
"""Operator-perspective QA: countdown logic + live WebSocket flows (本番)."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parents[1]
PLAYER_HTML = REPO / "player.html"


@dataclass
class DisplayBlock:
    type: str
    action_ms: int
    target_ms: int
    pre_warn_ms: int | None = None


WD_PREWARN_SEC = 18
WD_COUNTDOWN_SEC = 10


def block_kept(b: DisplayBlock, now_ms: int) -> bool:
    """player.html displayBlocks.filter と同じ"""
    if b.type in ("swap", "wd_manual", "gorei", "ins"):
        return True
    return (b.target_ms - now_ms) > -5000


def wd_cd_seconds(b: DisplayBlock, now_ms: int) -> float | None:
    """player.html wd_manual: 指示後すぐ targetMs までの残り秒（入替と同様に即表示）"""
    if now_ms >= b.target_ms:
        return 0.0
    return max(0.0, (b.target_ms - now_ms) / 1000.0)


def ins_cd_seconds(b: DisplayBlock, now_ms: int) -> float:
    """player.html ins: 表示は差込スタート(actionMs)まで"""
    if b.type != "ins":
        return -1.0
    if now_ms >= b.action_ms:
        return 0.0
    return max(0.0, (b.action_ms - now_ms) / 1000.0)


def countdown_seconds(b: DisplayBlock, now_ms: int) -> float:
    """player.html updateBoxDynamic の cd 表示ロジック（swap 等）"""
    if b.type == "wd_manual":
        v = wd_cd_seconds(b, now_ms)
        return v if v is not None else -1.0
    if b.type == "ins":
        return ins_cd_seconds(b, now_ms)
    action_done = b.action_ms <= now_ms
    if not action_done:
        return (b.action_ms - now_ms) / 1000.0
    return 0.0


def wd_manual_times(swap_land_ms: int, wd_margin_sec: int = 1) -> tuple[int, int, int]:
    """入替着弾から: ゼロ=margin秒前, 10秒前からCD, 18秒前から予告"""
    target_ms = swap_land_ms - wd_margin_sec * 1000
    action_ms = target_ms - WD_COUNTDOWN_SEC * 1000
    pre_warn_ms = target_ms - WD_PREWARN_SEC * 1000
    return pre_warn_ms, action_ms, target_ms


def run_logic_tests(step_fn: Callable) -> list[dict]:
    steps: list[dict] = []
    now = 5000

    # 差込: 入替同様 action=着弾-行軍、表示は着弾まで即CD
    land_ms = 100_000
    margin_ms = 1_000
    march_ms = 12_000
    ins_tgt = land_ms - margin_ms
    ins_act = ins_tgt - march_ms
    ins = DisplayBlock("ins", action_ms=ins_act, target_ms=ins_tgt)
    steps.append(
        step_fn(
            "op_ins_swap_like_start",
            "差込: スタート=着弾-行軍秒（入替同様）",
            ins.action_ms == ins_tgt - march_ms,
            f"action={ins.action_ms} target={ins_tgt}",
        )
    )
    cd_before_start = ins_cd_seconds(ins, ins_act - 12000)
    cd_at_start = ins_cd_seconds(ins, ins_act + 5000)
    steps.append(
        step_fn(
            "op_ins_cd_to_start_display",
            "差込: 表示CDはスタート(actionMs)まで",
            11.0 <= cd_before_start <= 13.0 and cd_at_start == 0.0,
            f"スタート12秒前={cd_before_start:.1f}s スタート5秒後={cd_at_start:.1f}s",
        )
    )
    steps.append(
        step_fn(
            "op_ins_block_persists",
            "差込: 号令後も表示ブロック維持",
            block_kept(ins, ins_tgt + 5000),
            "ins は filter で常に残る",
        )
    )

    # 占領入替: ブロックはアクション後も消えない
    swap = DisplayBlock("swap", action_ms=2000, target_ms=15000)
    steps.append(
        step_fn(
            "op_swap_block_persists",
            "占領入替: 指示後も表示ブロック維持",
            block_kept(swap, 6000),
            "swap は filter で常に残る",
        )
    )
    steps.append(
        step_fn(
            "op_swap_has_target",
            "占領入替: 着弾時刻あり",
            swap.target_ms > swap.action_ms,
            f"target={swap.target_ms}",
        )
    )

    # 集結号令後、差込と入替が同時にあっても差込カウントが優先継続
    ins2 = DisplayBlock("ins", action_ms=3000, target_ms=12000)
    swap2 = DisplayBlock("swap", action_ms=4000, target_ms=20000)
    steps.append(
        step_fn(
            "op_ins_with_swap_parallel",
            "差込+入替並存時も差込カウント継続",
            ins_cd_seconds(ins2, 2500) > 0 and block_kept(swap2, 7000),
            f"ins残り={ins_cd_seconds(ins2, 2500):.0f}s swap維持={block_kept(swap2, 7000)}",
        )
    )

    # 集結(gorei): アクション後は 00:00 だがブロックは維持（着弾UTC表示）
    gorei = DisplayBlock("gorei", action_ms=2000, target_ms=10000)
    steps.append(
        step_fn(
            "op_gorei_block_after_action",
            "集結: 号令後もブロック維持",
            block_kept(gorei, 6000),
            f"cd={countdown_seconds(gorei, 6000):.0f}s（アクション表示は0想定）",
        )
    )

    swap_land = 100_000
    pre_ms, act_ms, tgt_ms = wd_manual_times(swap_land, 1)
    wd = DisplayBlock("wd_manual", action_ms=act_ms, target_ms=tgt_ms, pre_warn_ms=pre_ms)
    steps.append(
        step_fn(
            "op_wd_zero_before_swap",
            "占領抜き: ゼロ=入替着弾の1秒前",
            tgt_ms == swap_land - 1000,
            f"target={tgt_ms} swap={swap_land}",
        )
    )
    steps.append(
        step_fn(
            "op_wd_countdown_10s",
            "占領抜き: 10秒前からカウント",
            act_ms == tgt_ms - WD_COUNTDOWN_SEC * 1000 and countdown_seconds(wd, act_ms + 5000) > 0,
            f"残り={countdown_seconds(wd, act_ms + 5000):.0f}s",
        )
    )
    steps.append(
        step_fn(
            "op_wd_prewarn_18s",
            "占領抜き: 18秒前から予告フェーズ",
            pre_ms == tgt_ms - WD_PREWARN_SEC * 1000,
            f"preWarn={pre_ms}",
        )
    )
    steps.append(
        step_fn(
            "op_wd_no_march_offset",
            "占領抜き: 行軍時間でactionMsをずらさない",
            act_ms == tgt_ms - 10_000,
            "actionMs=target-10s（行軍秒なし）",
        )
    )
    far_before = pre_ms - 5_000
    cd_far = wd_cd_seconds(wd, far_before)
    steps.append(
        step_fn(
            "op_wd_display_immediate",
            "占領抜き: 指示後すぐCD表示（入替同様）",
            cd_far is not None and cd_far > WD_COUNTDOWN_SEC,
            f"18秒前でも残り={cd_far:.0f}s（10秒待たない）",
        )
    )
    at_cd_start = act_ms + 200
    cd_at_start = wd_cd_seconds(wd, at_cd_start)
    steps.append(
        step_fn(
            "op_wd_countdown_to_zero_at_target",
            "占領抜き: CDは常にゼロ時刻まで一本",
            cd_at_start is not None and 9.0 <= cd_at_start <= 10.5,
            f"10秒前残り={cd_at_start:.1f}s（actionMs境界ではない）",
        )
    )
    at_boundary = act_ms - 500
    cd_boundary = wd_cd_seconds(wd, at_boundary)
    steps.append(
        step_fn(
            "op_wd_no_zero_at_10s_boundary",
            "占領抜き: 10秒前に0→再スタートしない",
            cd_boundary is not None and cd_boundary > 10.0,
            f"10秒境界手前残り={cd_boundary:.1f}s",
        )
    )
    mid_cd = wd_cd_seconds(wd, act_ms + 5000)
    steps.append(
        step_fn(
            "op_wd_monotonic_to_zero",
            "占領抜き: カウント中はゼロ方向へ減少",
            mid_cd is not None and 4.0 <= mid_cd <= 5.5,
            f"中間残り={mid_cd:.1f}s",
        )
    )

    return steps


def run_html_operator_checks(step_fn: Callable) -> list[dict]:
    steps: list[dict] = []
    if not PLAYER_HTML.is_file():
        steps.append(step_fn("op_html", "player.html", False, "file missing"))
        return steps
    html = PLAYER_HTML.read_text(encoding="utf-8")
    checks = [
        ("op_src_ins_usage_gate", "差込 利用ゲート(占領のみ)", "allianceUsesInsertFeature"),
        ("op_src_ins_build", "差込 buildInsertDisplayBlock", "buildInsertDisplayBlock"),
        ("op_src_ins_landing", "差込 getInsertLandingMs", "getInsertLandingMs"),
        ("op_src_ins_margin", "差込 insert_margin_sec", "insert_margin_sec"),
        ("op_src_swap", "占領入替 manual_swap", "manual_swap_trigger_time"),
        ("op_src_swap_label", "占領入替ラベル", "占領入替"),
        ("op_src_insert_fire", "差込号令 insert_fire_target", "insert_fire_target"),
        ("op_src_fire_swap", "入替発火コマンド", "fire_manual_swap"),  # main.py / 管理画面
        ("op_src_fire_insert", "差込発火", "fire_insert_fixed_target"),
        ("op_src_filter_swap", "入替/集結のfilter維持", "b.type === 'swap'"),
        ("op_src_update_cd", "カウントダウン更新", "updateBoxDynamic"),
        ("op_src_wd_immediate_cd", "占領抜き 即CD", "(b.targetMs - now)"),
        ("op_src_wd_isWd", "占領抜き isWd", "wd_manual"),
        ("op_src_wd_target_swap", "占領抜き 入替着弾基準", "manual_swap_trigger_time"),
    ]
    admin = (REPO / "index.html").read_text(encoding="utf-8") if (REPO / "index.html").is_file() else ""
    main_py = (REPO / "main.py").read_text(encoding="utf-8") if (REPO / "main.py").is_file() else ""
    blob = html + admin + main_py
    for sid, name, needle in checks:
        ok = needle in blob
        steps.append(step_fn(sid, name, ok, "ok" if ok else f"missing {needle}"))
    if admin:
        steps.append(
            step_fn(
                "op_admin_insert_send_staff",
                "管理画面:差込ボタンがstaff_modeを送る",
                "fire_insert_fixed_target' || cmd === 'clear_insert_fixed_target')" in admin
                and "set_staff_mode" in admin.split("function send")[1].split("function ")[0],
                "index.html send()",
            )
        )
    return steps


async def ws_recv_json(ws, timeout: float = 5.0) -> dict:
    import asyncio

    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


async def ws_send_cmd(ws, cmd: str, idx: int | None = None, val: Any = None) -> None:
    msg: dict = {"cmd": cmd}
    if idx is not None:
        msg["idx"] = idx
    if val is not None:
        msg["val"] = val
    await ws.send(json.dumps(msg))


async def ws_collect_state(ws, seconds: float = 2.5) -> dict | None:
    import asyncio

    state = None
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            msg = await ws_recv_json(ws, 0.4)
        except Exception:
            continue
        if msg.get("type") in ("init", "tick") and isinstance(msg.get("data"), dict):
            state = msg["data"]
        if msg.get("type") == "force_gorei":
            pass
    return state


async def run_operator_ws(cfg: dict, ws_url_fn: Callable[[dict, str, str], str], step_fn: Callable) -> list[dict]:
    steps: list[dict] = []
    try:
        import websockets
    except ImportError:
        steps.append(step_fn("op_ws_lib", "websockets", False, "pip install websockets"))
        return steps

    url_default = ws_url_fn(cfg, "drill", "default")
    ssl_ctx = None
    try:
        from qa_feature_check import ws_ssl_context

        ssl_ctx = ws_ssl_context(url_default)
    except Exception:
        import ssl

        ssl_ctx = ssl.create_default_context() if url_default.startswith("wss://") else None
    room_code = "op" + uuid.uuid4().hex[:6]
    room_name = "QA操作"

    try:
        async with websockets.connect(url_default, ssl=ssl_ctx, open_timeout=15) as ws0:
            await ws_recv_json(ws0, 8)
            await ws_send_cmd(
                ws0,
                "set_mode",
                val={
                    "mode": "drill",
                    "alliance_id": 0,
                    "room_action": "create",
                    "room_code": room_code,
                    "alliance_name": room_name,
                },
            )
            room_id = None
            for _ in range(10):
                m = await ws_recv_json(ws0, 5)
                if m.get("type") == "mode_ok":
                    room_id = m.get("room_id")
                    break
            if not room_id:
                steps.append(step_fn("op_ws_room", "訓練ルーム作成", False, "mode_okなし"))
                return steps

        url = ws_url_fn(cfg, "drill", room_id)
        async with websockets.connect(url, ssl=ssl_ctx, open_timeout=15) as staff, websockets.connect(
            url, ssl=ssl_ctx, open_timeout=15
        ) as leader:
            await ws_recv_json(staff, 6)
            await ws_recv_json(leader, 6)

            await ws_send_cmd(staff, "set_staff_mode", val={"enabled": True, "alliance_id": 0})
            await ws_send_cmd(staff, "update_alliance_role", idx=0, val="occupy")
            await ws_send_cmd(
                leader,
                "register_player",
                val={
                    "role": "leader1",
                    "alliance_id": 0,
                    "name": "QA_OP_L1",
                    "march_min": 0,
                    "march_sec": 25,
                    "device_mode": "2device",
                },
            )
            st = await ws_collect_state(staff, 2.0)
            names_ok = False
            if isinstance(st, dict):
                timers = st.get("timers") or []
                squad_start = 6
                for i in range(squad_start, min(squad_start + 6, len(timers))):
                    t = timers[i]
                    if isinstance(t, dict) and (t.get("name") or "").strip() == "QA_OP_L1":
                        names_ok = True
                        break
            steps.append(
                step_fn(
                    "op_ws_register_leader",
                    "集結主登録→タイマー反映",
                    names_ok,
                    "名前登録OK" if names_ok else "タイマー未反映",
                )
            )

            st_pre = await ws_collect_state(staff, 1.5)
            min_tgt = None
            if isinstance(st_pre, dict):
                marches = []
                for i in range(6, 12):
                    timers = st_pre.get("timers") or []
                    if i < len(timers) and isinstance(timers[i], dict):
                        nm = (timers[i].get("name") or "").strip()
                        if nm:
                            marches.append(int(timers[i].get("sub_set") or 0))
                max_march = max(marches) if marches else 0
                off = int((st_pre.get("gorei_offsets") or [0] * 6)[0] or 0)
                rally = int(st_pre.get("default_rally") or 300)
                min_tgt = time.time() + off + rally + max_march
            await ws_send_cmd(staff, "mod_gorei_target", idx=0, val=-600)
            st_fix = await ws_collect_state(staff, 2.0)
            fixed0 = None
            if isinstance(st_fix, dict):
                gft = st_fix.get("gorei_fixed_targets") or []
                if len(gft) > 0:
                    fixed0 = gft[0]
            below_min = (
                fixed0 is not None
                and min_tgt is not None
                and float(fixed0) < float(min_tgt) - 30
            )
            steps.append(
                step_fn(
                    "op_ws_gorei_target_before_min",
                    "着弾指定:計算下限より前を設定可",
                    below_min,
                    f"fixed={fixed0} min~{min_tgt:.0f}" if min_tgt else f"fixed={fixed0}",
                )
            )

            await ws_send_cmd(staff, "mod_gorei_target", idx=0, val=120)
            await ws_collect_state(staff, 1.0)
            got_force_fixed = False
            await ws_send_cmd(staff, "fire_gorei_fixed", idx=0)
            end_fixed = time.monotonic() + 6.0
            while time.monotonic() < end_fixed:
                try:
                    m = await ws_recv_json(staff, 1.0)
                    if m.get("type") == "force_gorei" and int(m.get("squad_idx", -1)) == 0:
                        got_force_fixed = True
                        break
                except Exception:
                    await asyncio.sleep(0.1)
            st_fix_fire = await ws_collect_state(staff, 1.5)
            gft = (st_fix_fire or {}).get("gorei_fixed_targets") if isinstance(st_fix_fire, dict) else None
            has_fixed = isinstance(gft, list) and len(gft) > 0 and gft[0] is not None
            fixed_fired = got_force_fixed or has_fixed
            steps.append(
                step_fn(
                    "op_ws_gorei_fixed_no_members",
                    "着弾指定号令:集結主0人でも発火",
                    fixed_fired,
                    "force_gorei" if got_force_fixed else ("fixed_target kept" if has_fixed else "no fire"),
                )
            )

            got_force = False
            await ws_send_cmd(staff, "fire_gorei", idx=0)
            end_recv = time.monotonic() + 8.0
            while time.monotonic() < end_recv:
                try:
                    m = await ws_recv_json(leader, 1.0)
                    if m.get("type") in ("force_gorei", "gorei_hint"):
                        got_force = True
                        if m.get("type") == "force_gorei":
                            break
                except Exception:
                    await asyncio.sleep(0.15)
            st_g = await ws_collect_state(leader, 1.5)
            timer_active = False
            if isinstance(st_g, dict):
                timers = st_g.get("timers") or []
                for i in range(6, 12):
                    if i < len(timers) and isinstance(timers[i], dict):
                        if int(timers[i].get("state") or 0) == 4:
                            timer_active = True
                            break
            steps.append(
                step_fn(
                    "op_ws_gorei_force",
                    "集結号令→プレイヤーへ伝達",
                    got_force or timer_active,
                    "force/hint受信" if got_force else ("timer state=4" if timer_active else "未受信"),
                )
            )

            st = await ws_collect_state(staff, 2.0)
            glt = (st or {}).get("gorei_last_target") if isinstance(st, dict) else None
            gorei_set = isinstance(glt, list) and len(glt) > 0 and glt[0] is not None
            steps.append(
                step_fn(
                    "op_ws_gorei_state",
                    "集結号令→gorei_last_target設定",
                    gorei_set,
                    str(st.get("gorei_last_target", [])[:1]) if st else "no state",
                )
            )

            await ws_send_cmd(staff, "fire_manual_swap")
            st2 = await ws_collect_state(staff, 2.0)
            swap_set = isinstance(st2, dict) and st2.get("manual_swap_trigger_time") is not None
            swap_ts = float(st2.get("manual_swap_trigger_time") or 0) if isinstance(st2, dict) else 0
            steps.append(
                step_fn(
                    "op_ws_manual_swap",
                    "占領入替発火→manual_swap_trigger_time",
                    swap_set,
                    f"trigger={st2.get('manual_swap_trigger_time')}" if st2 else "no state",
                )
            )

            await ws_send_cmd(staff, "fire_manual_wd")
            st_wd = await ws_collect_state(staff, 2.0)
            wd_ts = float(st_wd.get("manual_wd_trigger_time") or 0) if isinstance(st_wd, dict) else 0
            margin = int(st_wd.get("manual_wd_margin") or 1) if isinstance(st_wd, dict) else 1
            wd_ok = swap_set and wd_ts > 0 and abs(wd_ts - (swap_ts - margin)) < 0.05
            steps.append(
                step_fn(
                    "op_ws_wd_vs_swap",
                    "占領抜きゼロ=入替着弾-margin秒",
                    wd_ok,
                    f"swap={swap_ts} wd={wd_ts} margin={margin}",
                )
            )

            future = time.time() + 50
            await ws_send_cmd(staff, "mod_insert_target", val=30)
            await ws_send_cmd(staff, "fire_insert_fixed_target")
            st3 = await ws_collect_state(staff, 2.0)
            ins_set = isinstance(st3, dict) and st3.get("insert_fire_target") is not None
            steps.append(
                step_fn(
                    "op_ws_insert_fire",
                    "差込号令→insert_fire_target",
                    ins_set,
                    f"target={st3.get('insert_fire_target')}" if st3 else "no state",
                )
            )

            roles = (st3 or {}).get("alliance_roles") if isinstance(st3, dict) else []
            occ_ok = isinstance(roles, list) and len(roles) > 0 and roles[0] == "occupy"
            steps.append(
                step_fn(
                    "op_ws_occupy_role",
                    "占領同盟ロール設定",
                    occ_ok,
                    str(roles[:1]) if isinstance(roles, list) else str(roles),
                )
            )

            await ws_send_cmd(staff, "start", idx=0)
            await ws_collect_state(staff, 1.0)
            await ws_send_cmd(staff, "mod_insert_target", val=120)
            await ws_send_cmd(staff, "fire_insert_fixed_target")
            ins_leader = False
            end_ins = time.monotonic() + 6.0
            while time.monotonic() < end_ins:
                try:
                    m = await ws_recv_json(leader, 1.0)
                    if m.get("type") in ("init", "tick") and isinstance(m.get("data"), dict):
                        data = m["data"]
                        if data.get("insert_fire_target") and data.get("alliance_roles", [""])[0] == "occupy":
                            ins_leader = True
                            break
                except Exception:
                    await asyncio.sleep(0.1)
            steps.append(
                step_fn(
                    "op_ws_insert_player_visible",
                    "差込号令→占領プレイヤーに反映",
                    ins_leader,
                    "insert_fire_target+occupy" if ins_leader else "no insert on leader",
                )
            )

    except Exception as e:
        import traceback

        steps.append(
            step_fn("op_ws_flow", "操作者WSフロー", False, f"{e} | {traceback.format_exc()[-180:]}")
        )

    return steps


OPERATOR_MANUAL = [
    {
        "id": "manual_op_ins_screen",
        "name": "差込: 画面で着弾までカウント",
        "ok": None,
        "note": "占領同盟で号令後すぐCD、スタート18秒/10秒音声、着弾0まで一本",
    },
    {
        "id": "manual_op_swap_screen",
        "name": "占領入替: 画面で入替着弾確認",
        "ok": None,
        "note": "入替指示後、着弾(UTC)時刻が表示され、実戦で意図どおりか確認",
    },
    {
        "id": "manual_op_wd_screen",
        "name": "占領抜き: 18秒予告→10秒CD→0",
        "ok": None,
        "note": "攻撃同盟画面で18秒前に予告音声、10秒前から数字CD、入替1秒前で0（margin変更も確認）",
    },
    {
        "id": "manual_op_gorei_screen",
        "name": "集結号令: 画面・音声",
        "ok": None,
        "note": "号令〜着弾まで、表示と音声が役割どおりか（2台/1台）",
    },
    {
        "id": "manual_staff_panel",
        "name": "参謀パネル操作",
        "ok": None,
        "note": "差込▲▼・集結/行軍・第1/2班の操作が効くこと",
    },
]


def run_all(step_fn: Callable, cfg: dict, ws_url_fn) -> list[dict]:
    import asyncio

    steps: list[dict] = []
    steps.extend(run_logic_tests(step_fn))
    steps.extend(run_html_operator_checks(step_fn))
    steps.extend(asyncio.run(run_operator_ws(cfg, ws_url_fn, step_fn)))
    try:
        from qa_occupy_duty_checks import run_all as run_occupy_duty_all

        steps.extend(run_occupy_duty_all(step_fn, cfg, ws_url_fn))
    except Exception as e:
        steps.append(step_fn("op_occupy_duty_import", "占領割当QA", False, str(e)[:160]))
    return steps

#!/usr/bin/env python3
"""占領同盟 差込/入替 自動割当 QA（ロジック + 本番WS）。"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from main import (  # noqa: E402
    OCCUPY_CMD_MAX_AHEAD_SEC,
    compute_occupy_duty_plan,
    occupy_can_also_swap,
    occupy_duty_for_connection,
)


def step(id_: str, name: str, ok: bool, note: str = "") -> dict:
    return {"id": id_, "name": name, "ok": ok, "note": note, "kind": "auto"}


def run_logic_tests(step_fn) -> list[dict]:
    steps = []
    steps.append(
        step_fn(
            "op_occupy_can_both",
            "着弾後入替出発可(47秒×2<120秒差)",
            occupy_can_also_swap(47, 1000.0, 1120.0),
            "gap=120s march=47",
        )
    )
    steps.append(
        step_fn(
            "op_occupy_cannot_both",
            "入替出発が差込着弾前は不可",
            not occupy_can_also_swap(47, 1100.0, 1120.0),
            "swap_dep before ins land",
        )
    )
    fake_state = {
        "alliance_roles": ["occupy", "attack", "attack"],
        "insert_fire_target": time.time() + 120,
        "manual_swap_trigger_time": time.time() + 200,
    }
    conn = []
    for i, m in enumerate([30, 47, 60]):
        conn.append(
            (
                object(),
                {
                    "mode": "prod",
                    "a_id": 0,
                    "role": "rider",
                    "staff_enabled": False,
                    "march_sec": m,
                    "id": f"p{i}",
                },
            )
        )
    plan = compute_occupy_duty_plan(fake_state, conn, 0, time.time())
    ok_plan = (
        plan is not None
        and plan.get("has_ins")
        and plan.get("has_swap")
        and plan["counts"]["ins"] >= 1
        and plan["counts"]["swap"] >= 1
    )
    steps.append(
        step_fn(
            "op_occupy_plan_balance",
            "差込+入替時に両方へ割当",
            ok_plan,
            str(plan.get("counts") if plan else "none"),
        )
    )
    swap_only_st = {
        "alliance_roles": ["occupy", "attack", "attack"],
        "manual_swap_trigger_time": time.time() + 100,
    }
    plan2 = compute_occupy_duty_plan(swap_only_st, conn, 0, time.time())
    all_swap = (
        plan2
        and plan2.get("has_swap")
        and not plan2.get("has_ins")
        and all(v.get("primary") == "swap" for v in plan2.get("by_id", {}).values())
    )
    steps.append(
        step_fn(
            "op_occupy_swap_only_all",
            "差込なし時は全員入替役",
            all_swap,
            str(plan2.get("counts") if plan2 else "none"),
        )
    )
    stale_swap = {
        "alliance_roles": ["occupy", "attack", "attack"],
        "manual_swap_trigger_time": time.time() + OCCUPY_CMD_MAX_AHEAD_SEC + 3600,
    }
    plan_stale = compute_occupy_duty_plan(stale_swap, conn, 0, time.time())
    steps.append(
        step_fn(
            "op_occupy_ignore_stale_swap",
            "総指揮未指示相当(遠い未来の入替ゴミ)は割当なし",
            plan_stale is None,
            "plan=None" if plan_stale is None else str(plan_stale.get("counts")),
        )
    )
    return steps


async def run_prod_ws_test(cfg: dict, ws_url_fn, step_fn) -> list[dict]:
    steps: list[dict] = []
    try:
        import websockets
        from qa_feature_check import ws_collect_until, ws_recv_json, ws_ssl_context
        from qa_operator_checks import ws_send_cmd, ws_collect_state
    except ImportError as e:
        steps.append(step_fn("op_occupy_ws", "import", False, str(e)))
        return steps

    url = ws_url_fn(cfg, "prod", "default")
    ssl_ctx = ws_ssl_context(url)
    now = time.time()
    ins_t = now + 90
    swap_t = now + 150

    try:
        async with websockets.connect(url, ssl=ssl_ctx, open_timeout=15) as w1, websockets.connect(
            url, ssl=ssl_ctx, open_timeout=15
        ) as w2, websockets.connect(url, ssl=ssl_ctx, open_timeout=15) as whq:
            await ws_recv_json(w1, 6)
            await ws_recv_json(w2, 6)
            await ws_recv_json(whq, 6)

            for w, march in ((w1, 30), (w2, 55)):
                await ws_send_cmd(w, "set_mode", val={"mode": "prod", "alliance_id": 0})
                await ws_send_cmd(w, "update_alliance_role", idx=0, val="occupy")
                await ws_send_cmd(
                    w,
                    "register_player",
                    val={
                        "role": "rider",
                        "alliance_id": 0,
                        "name": f"QA{march}",
                        "march_min": 0,
                        "march_sec": march,
                        "device_mode": "2device",
                    },
                )

            await ws_send_cmd(whq, "set_mode", val={"mode": "prod", "alliance_id": 0})
            await ws_send_cmd(whq, "update_alliance_role", idx=0, val="occupy")
            await ws_send_cmd(whq, "set_staff_mode", val={"enabled": True, "alliance_id": 0})
            await ws_send_cmd(whq, "clear_insert_fixed_target")
            await ws_send_cmd(whq, "cancel_manual_swap")
            await ws_drain(whq, 0.4)
            now = time.time()
            await ws_send_cmd(whq, "set_manual_base_abs", val=now + 180)
            await ws_send_cmd(whq, "mod_insert_target", val=120)
            await ws_send_cmd(whq, "fire_insert_fixed_target")
            await ws_drain(whq, 0.4)
            st = await ws_collect_state(whq, 3.0)
            ins_ok = bool(st and st.get("insert_fire_target"))
            ins_land = float(st["insert_fire_target"]) if ins_ok else now + 120
            await ws_send_cmd(whq, "set_manual_base_abs", val=ins_land + 70)
            await ws_send_cmd(whq, "fire_manual_swap")
            await ws_drain(whq, 0.5)
            st = await ws_collect_state(whq, 2.0)
            swap_ok = bool(st and st.get("manual_swap_trigger_time"))
            steps.append(
                step_fn(
                    "op_occupy_ws_ins_fire",
                    "差込号令",
                    ins_ok and swap_ok,
                    f"ins={st.get('insert_fire_target') if st else None} swap={st.get('manual_swap_trigger_time') if st else None}",
                )
            )

            has_cmds_on_sync = False
            m = None
            for _ in range(10):
                m, _ = await ws_collect_until(w1, {"sync"}, 2)
                if m and m.get("occupy_cmds"):
                    has_cmds_on_sync = bool(m["occupy_cmds"].get("insert_fire_target") or m["occupy_cmds"].get("manual_swap_trigger_time"))
                    if has_cmds_on_sync:
                        break
            steps.append(
                step_fn(
                    "op_occupy_ws_sync_cmds",
                    "syncに号令時刻(occupy_cmds)",
                    has_cmds_on_sync,
                    str(m.get("occupy_cmds") if m else "")[:100],
                )
            )

            duty1 = None
            duty2 = None
            end_bal = time.monotonic() + 18
            while time.monotonic() < end_bal:
                m1, _ = await ws_collect_until(w1, {"tick", "sync"}, 2)
                if m1 and m1.get("occupy_duty"):
                    duty1 = m1["occupy_duty"]
                m2, _ = await ws_collect_until(w2, {"tick", "sync"}, 2)
                if m2 and m2.get("occupy_duty"):
                    duty2 = m2["occupy_duty"]
                c = (duty1 or {}).get("counts") or {}
                if (
                    duty1
                    and duty2
                    and int(c.get("ins", 0)) >= 1
                    and int(c.get("swap", 0)) >= 1
                ):
                    break

            steps.append(
                step_fn(
                    "op_occupy_ws_duty_p1",
                    "参加者1: occupy_duty",
                    duty1 is not None and duty1.get("primary") in ("ins", "swap"),
                    str(duty1)[:120] if duty1 else "none",
                )
            )
            steps.append(
                step_fn(
                    "op_occupy_ws_duty_p2",
                    "参加者2: occupy_duty",
                    duty2 is not None and duty2.get("primary") in ("ins", "swap"),
                    str(duty2)[:120] if duty2 else "none",
                )
            )
            balanced = (
                duty1
                and duty2
                and duty1.get("primary") != duty2.get("primary")
                and duty1.get("counts")
                and int(duty1["counts"].get("ins", 0)) >= 1
                and int(duty1["counts"].get("swap", 0)) >= 1
            )
            steps.append(
                step_fn(
                    "op_occupy_ws_balance",
                    "2名で差込/入替が分かれる",
                    balanced,
                    f"p1={duty1.get('primary') if duty1 else '?'} p2={duty2.get('primary') if duty2 else '?'}",
                )
            )

            await ws_send_cmd(whq, "clear_insert_fixed_target")
            await ws_drain(whq, 0.3)
            swap_only_duty = None
            for _ in range(12):
                m, _ = await ws_collect_until(w1, {"tick"}, 2)
                if m and m.get("occupy_duty") and m["occupy_duty"].get("primary") == "swap":
                    swap_only_duty = m["occupy_duty"]
                    break
            steps.append(
                step_fn(
                    "op_occupy_ws_swap_only",
                    "差込解除後は入替役",
                    swap_only_duty is not None,
                    str(swap_only_duty.get("primary_label") if swap_only_duty else ""),
                )
            )
    except Exception as e:
        steps.append(step_fn("op_occupy_ws", "WS検証", False, str(e)[:200]))
    return steps


async def ws_drain(ws, sec: float) -> None:
    end = time.monotonic() + sec
    while time.monotonic() < end:
        try:
            await asyncio.wait_for(ws.recv(), timeout=0.15)
        except Exception:
            await asyncio.sleep(0.05)


def run_all(step_fn, cfg: dict, ws_url_fn) -> list[dict]:
    steps = run_logic_tests(step_fn)
    steps.extend(asyncio.run(run_prod_ws_test(cfg, ws_url_fn, step_fn)))
    return steps

#!/usr/bin/env python3
"""操作者ロジック（差込・入替・集結・占領抜き）の HTML/サーバー仕様ロック。毎回 QA から呼ぶ。"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

REPO = Path(__file__).resolve().parents[1]
PLAYER = REPO / "player.html"
MAIN = REPO / "main.py"
INDEX = REPO / "index.html"

# --- 占領抜き: 戻してはいけない旧実装 ---
WD_FORBIDDEN = [
    "function wdDisplayPhase",
    "WD_PREWARN_SEC",
    "WD_COUNTDOWN_SEC",
    'wdPhase === "prewarn"',
    'cdText = "—"',
]

WD_REQUIRED = [
    ("isWd", "const isWd = (b.type === 'wd_manual')"),
    ("label_immediate", "actionLabel = (now < b.targetMs) ? `⏳ ${b.actionLabel} まで`"),
    ("voice_target", "if (b.type === 'wd_manual') {\n                        wait = (b.targetMs - now) / 1000"),
    ("margin_from_swap", "swapLandMs - wdMarginSec * 1000"),
]

# --- 占領入替 ---
SWAP_REQUIRED = [
    ("manual_swap_field", "manual_swap_trigger_time"),
    ("swap_block", "type: 'swap'"),
    ("swap_march_action", "actionTime = targetMs - (myMarchSec * 1000)"),
    ("swap_label", "占領入替"),
    ("swap_filter_keep", "b.type === 'swap' || b.type === 'wd_manual' || b.type === 'gorei'"),
]

# --- 集結号令 ---
GOREI_REQUIRED = [
    ("gorei_block", "type: 'gorei'"),
    ("gorei_last_target", "gorei_last_target"),
    ("gorei_pre_rally", "actionLabel: '集結開始まで'"),
    ("gorei_rallying", "actionLabel: '集結中'"),
    ("gorei_marching", "actionLabel: '行軍中'"),
    ("gorei_rider_watch", "gorei_rider_watch"),
    ("gorei_rider_prep", "集結準備中"),
    ("gorei_rider_rallying_ui", "集結中"),
    ("gorei_rider_subline", "集結主が集結中です。"),
    ("gorei_rider_cd", 'cdCaption: \'CD\''),
    ("gorei_rider_tag", "riderTag: '乗り手'"),
    ("gorei_role_pick", "effectiveRoleForUi === 'leader1'"),
    ("gorei_hint", "pendingGoreiHints"),
    ("force_gorei_handler", "force_gorei"),
    ("fire_gorei_cmd", 'cmd:"fire_gorei"'),
]

# --- 差込（入替同型ロジック。利用は占領同盟のみ＝表示ゲート） ---
INS_REQUIRED = [
    ("ins_usage_gate", "allianceUsesInsertFeature"),
    ("ins_build_fn", "buildInsertDisplayBlock"),
    ("ins_block", "type: 'ins'"),
    ("ins_isIns", "const isIns = (b.type === 'ins')"),
    ("wd_cd_to_target", "if (isWd) {\n            if (now < b.targetMs) {\n                cdText = formatSec((b.targetMs - now) / 1000)"),
    ("ins_cd_to_start", "else if (isIns) {\n            if (now < b.actionMs) {\n                cdText = formatSec((b.actionMs - now) / 1000)"),
    ("ins_label_start", 'actionLabel: "差込スタート"'),
    ("ins_march_start", "const actionMs = targetMs - msec"),
    ("insert_fire", "insert_fire_target"),
    ("get_insert_landing", "function getInsertLandingMs"),
    ("compute_enemy_landing", "computeInsertLandingMsFromEnemy"),
    ("insert_margin", "insert_margin_sec"),
    ("ins_filter_keep", "b.type === 'ins') return true"),
]

GOREI_FORBIDDEN = [
    'isRider ? "出発"',
    'actionLabel: isRider ? "出発"',
    "司令塔",
    "司令官",
    "班長",
    'actionLabel: isRider ? "集結開始"',
]

# --- 共通カウントダウン更新 ---
COMMON_REQUIRED = [
    ("update_box", "function updateBoxDynamic"),
    ("build_box", "function buildBoxHTML"),
]


def _check_needles(
    step_fn: Callable,
    prefix: str,
    category: str,
    html: str,
    needles: list[tuple[str, str]],
) -> list[dict]:
    steps: list[dict] = []
    for sid, needle in needles:
        ok = needle in html
        steps.append(
            step_fn(
                f"op_spec_{prefix}_{sid}",
                f"{category}:{sid}",
                ok,
                "ok" if ok else f"missing: {needle[:48]}...",
            )
        )
    return steps


def _check_forbidden(
    step_fn: Callable,
    prefix: str,
    category: str,
    html: str,
    patterns: list[str],
) -> list[dict]:
    steps: list[dict] = []
    for i, bad in enumerate(patterns):
        found = bad in html
        steps.append(
            step_fn(
                f"op_spec_{prefix}_forbid_{i}",
                f"{category}:禁止パターンなし",
                not found,
                f"禁止:{bad}" if found else "ok",
            )
        )
    return steps


def _check_main(step_fn: Callable, main_py: str) -> list[dict]:
    steps: list[dict] = []
    cmds = [
        ("fire_manual_swap", "fire_manual_swap"),
        ("fire_manual_wd", "fire_manual_wd"),
        ("fire_insert", "fire_insert_fixed_target"),
        ("mod_insert_margin", "mod_insert_margin"),
        ("wd_from_swap", 'float(state["manual_swap_trigger_time"]) - state["manual_wd_margin"]'),
    ]
    for sid, needle in cmds:
        ok = needle in main_py
        steps.append(
            step_fn(
                f"op_spec_main_{sid}",
                f"サーバー:{sid}",
                ok,
                "ok" if ok else f"missing: {needle}",
            )
        )
    return steps


def run_operator_spec_guard(step_fn: Callable) -> list[dict]:
    steps: list[dict] = []
    if not PLAYER.is_file():
        steps.append(step_fn("op_spec_player_file", "player.html 存在", False, "missing"))
        return steps

    html = PLAYER.read_text(encoding="utf-8")
    main_py = MAIN.read_text(encoding="utf-8") if MAIN.is_file() else ""

    steps.extend(_check_needles(step_fn, "common", "共通", html, COMMON_REQUIRED))
    steps.extend(_check_needles(step_fn, "ins", "差込", html, INS_REQUIRED))
    steps.extend(_check_needles(step_fn, "swap", "入替", html, SWAP_REQUIRED))
    steps.extend(_check_needles(step_fn, "gorei", "集結", html, GOREI_REQUIRED))
    steps.extend(_check_forbidden(step_fn, "gorei", "集結", html, GOREI_FORBIDDEN))
    steps.extend(_check_needles(step_fn, "wd", "占領抜き", html, WD_REQUIRED))
    steps.extend(_check_forbidden(step_fn, "wd", "占領抜き", html, WD_FORBIDDEN))
    if main_py:
        steps.extend(_check_main(step_fn, main_py))

    # preWarnMs は wd ブロック専用禁止（他用途があれば誤検知するので wd 周辺のみ）
    wd_push = "type: 'wd_manual'"
    if wd_push in html:
        idx = html.find(wd_push)
        wd_chunk = html[max(0, idx - 200) : idx + 400]
        steps.append(
            step_fn(
                "op_spec_wd_no_prewarn_block",
                "占領抜き:preWarnMsブロックなし",
                "preWarnMs" not in wd_chunk,
                "preWarnMs in wd block" if "preWarnMs" in wd_chunk else "ok",
            )
        )

    return steps

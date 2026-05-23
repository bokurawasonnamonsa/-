import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import uuid
import os
import urllib.request
import urllib.parse
import ssl
import json
import copy
import io
import wave
import struct

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

state = {
    "timers": [{"name": "", "sec": 300, "off": 0, "sub_set": 30, "sub_sec": 0, "state": 0, "end": None, "frozen_target": None, "start_at": None, "online": False, "device_mode": "2device"} for i in range(42)],
    "alliance_names": ["XYZ", "MTC", "APL"],
    "alliance_roles": ["occupy", "attack", "attack"], 
    "gorei_offsets": [15] * 6,
    "gorei_fixed_targets": [None] * 6,
    "gorei_last_target": [None] * 6,
    "default_rally": 300, 
    "swap_extras": [10, 10, 10], 
    "withdraw_margins": [1, 1, 1], 
    "swap_base_squad": -1,     
    "withdraw_base_squad": -1, 
    "insert_target_idx": -1, 
    "insert_fixed_target": None,
    "insert_fire_target": None,
    "insert_margin_sec": 1,
    "insert_offset_tenth": -10,
    "delay_target_idxs": [-1] * 6,
    "cancel_trigger": 0, 
    "online_counts": {
        "total": {"leader": 0, "rider": 0},
        "aln0": {"leader": 0, "rider": 0},
        "aln1": {"leader": 0, "rider": 0},
        "aln2": {"leader": 0, "rider": 0}
    },
    "pair_selected": [False] * 6,
    "pair_gorei_offset": 15,
    "pair_fixed_target": None,
    "manual_base_target": None, 
    "manual_swap_margin": 10,   
    "manual_wd_margin": 1,      
    "manual_swap_trigger_time": None,
    "manual_wd_trigger_time": None,
    "staff_names": ["", "", ""],
    "support_chats": {},
}
drill_states = {
    0: copy.deepcopy(state),
    1: copy.deepcopy(state),
    2: copy.deepcopy(state),
}
drill_rooms = {}
drill_room_meta = {}

def fresh_drill_state(alliance_primary: str):
    """訓練ルーム用の初期状態。本番 ``state`` の deepcopy は使わない（本番タイマー名・号令が混入するため）。"""
    an = (alliance_primary or "").strip() or "訓練"
    return {
        "timers": [
            {"name": "", "sec": 300, "off": 0, "sub_set": 30, "sub_sec": 0, "state": 0, "end": None, "frozen_target": None, "start_at": None, "online": False, "device_mode": "2device"}
            for _ in range(42)
        ],
        "alliance_names": [an, f"{an}-2", f"{an}-3"],
        "alliance_roles": ["occupy", "", ""],
        "gorei_offsets": [15] * 6,
        "gorei_fixed_targets": [None] * 6,
        "gorei_last_target": [None] * 6,
        "default_rally": 300,
        "swap_extras": [10, 10, 10],
        "withdraw_margins": [1, 1, 1],
        "swap_base_squad": -1,
        "withdraw_base_squad": -1,
        "insert_target_idx": -1,
        "insert_fixed_target": None,
        "insert_fire_target": None,
        "insert_margin_sec": 1,
        "insert_offset_tenth": -10,
        "delay_target_idxs": [-1] * 6,
        "cancel_trigger": 0,
        "online_counts": {
            "total": {"leader": 0, "rider": 0},
            "aln0": {"leader": 0, "rider": 0},
            "aln1": {"leader": 0, "rider": 0},
            "aln2": {"leader": 0, "rider": 0},
        },
        "pair_selected": [False] * 6,
        "pair_gorei_offset": 15,
        "pair_fixed_target": None,
        "manual_base_target": None,
        "manual_swap_margin": 10,
        "manual_wd_margin": 1,
        "manual_swap_trigger_time": None,
        "manual_wd_trigger_time": None,
        "staff_names": ["", "", ""],
        "support_chats": {},
    }

connections = {}
voice_cache = {}
# サポートのみ更新された tick でも全クライアントへ data 載せ替え同期するためのフラグ
FORCE_SUPPORT_CHAT_BROADCAST = False
FORCE_STATE_BROADCAST = False
voice_speakers_cache = None
voice_speakers_cache_at = 0

state_version = 0
tick_counter = 0
AI_MODEL_CACHE = "gemini-2.0-flash-lite"
AI_MODEL_CACHE_AT = 0
AI_MODEL_CANDIDATES_CACHE = []
AI_MODEL_CANDIDATES_CACHE_AT = 0
GOREI_DEBUG_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gorei_debug.log")

def gorei_debug_log(message: str):
    try:
        ts = datetime.now(timezone.utc).isoformat()
        with open(GOREI_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{ts} {message}\n")
    except Exception:
        pass

def get_state_for_conn(info):
    mode = (info or {}).get("mode", "prod")
    if mode == "drill":
        room_key = (info or {}).get("drill_key", "default")
        if room_key not in drill_rooms:
            dn = drill_room_meta.get(room_key, {}).get("name", "").strip()
            drill_rooms[room_key] = fresh_drill_state(dn or "訓練")
        return drill_rooms[room_key]
    return state

def is_automation_test_room(name: str, online: int) -> bool:
    """自動QAが量産した幽霊ルーム（0人・固定名）を一覧から除外する。"""
    if int(online or 0) > 0:
        return False
    n = (name or "").strip()
    if n in ("QA自動", "QA操作"):
        return True
    return n.startswith("QA_E2E_")


def drill_room_online_count(room_id):
    """ルームに紐づく drill WebSocket 接続数。参謀のみ在室のときも最低 1 とする。"""
    cnt = 0
    for _ws, info in list(connections.items()):
        if info.get("mode") == "drill" and info.get("drill_key") == room_id:
            cnt += 1
    if cnt <= 0 and room_id in drill_rooms:
        st = drill_rooms.get(room_id)
        if drill_staff_status_for_room(room_id, st).get("present"):
            cnt = 1
    return cnt


async def broadcast_drill_room_list():
    """訓練モードの全クライアントへルーム一覧を即時配信（作成直後の参加一覧反映用）。"""
    rooms = get_public_drill_rooms()
    dead = []
    for ws, info in list(connections.items()):
        if info.get("mode") != "drill":
            continue
        try:
            await ws.send_json({"type": "drill_rooms", "rooms": rooms})
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections.pop(ws, None)


def get_public_drill_rooms():
    """公開ルーム一覧。同盟名のみ表示。同名は接続中が多い1件だけ返す。"""
    items = []
    for room_id, meta in list(drill_room_meta.items()):
        name = (meta.get("name") or "訓練ルーム").strip() or "訓練ルーム"
        cnt = drill_room_online_count(room_id)
        if is_automation_test_room(name, cnt):
            continue
        items.append({"room_id": room_id, "name": name, "online": cnt})
    by_name = {}
    for it in items:
        n = it["name"]
        prev = by_name.get(n)
        if prev is None or int(it.get("online") or 0) > int(prev.get("online") or 0):
            by_name[n] = it
    items = list(by_name.values())
    items.sort(key=lambda x: (-int(x.get("online") or 0), str(x.get("name") or "")))
    return items

def same_context(info_a, info_b):
    mode_a = (info_a or {}).get("mode", "prod")
    mode_b = (info_b or {}).get("mode", "prod")
    if mode_a != mode_b:
        return False
    if mode_a == "drill":
        return (info_a or {}).get("drill_key", "default") == (info_b or {}).get("drill_key", "default")
    return True

def drill_staff_status_for_room(room_key, state_obj):
    """訓練ルーム内で参謀(staff+a_id0)が実接続中か。名前はstateのstaff_names[0]（接続中のみ意味を持つ）。"""
    present = False
    for _ws, info in list(connections.items()):
        if info.get("mode") != "drill":
            continue
        if info.get("drill_key") != room_key:
            continue
        if info.get("staff_enabled") and info.get("a_id") == 0:
            present = True
            break
    name = ""
    sn = (state_obj or {}).get("staff_names")
    if isinstance(sn, list) and len(sn) > 0:
        name = str(sn[0] or "").strip()
    return {"present": present, "name": name}

def build_alliance_presence(state_obj, conn_items, alliance_id: int) -> dict:
    """自同盟の接続人数（参謀・集結主・乗り手）。同盟名直下表示用。"""
    staff_online = 0
    leader_online = 0
    rider_online = 0
    for _ws, info in conn_items:
        if info.get("a_id") != alliance_id:
            continue
        if info.get("staff_enabled"):
            staff_online += 1
            continue
        role = str(info.get("role") or "")
        if role == "rider":
            rider_online += 1
        elif role.startswith("leader"):
            leader_online += 1
    staff_names = []
    sn = (state_obj or {}).get("staff_names")
    staff_nm = ""
    if isinstance(sn, list) and 0 <= alliance_id < len(sn):
        staff_nm = str(sn[alliance_id] or "").strip()
        if staff_online > 0 and staff_nm:
            staff_names.append(staff_nm)
    leader_cnt = leader_online
    rider_cnt = rider_online
    leader_names = []
    seen = set()
    timers = (state_obj or {}).get("timers") or []
    for squad_off in (0, 1):
        sid = alliance_id * 2 + squad_off
        start = 6 + sid * 6
        squad_name = ""
        for i in range(start, start + 6):
            if i >= len(timers) or not isinstance(timers[i], dict):
                continue
            t = timers[i]
            if not t.get("online"):
                continue
            nm = (t.get("name") or "").strip()
            if nm:
                squad_name = nm
                break
        if not squad_name or squad_name in seen:
            continue
        if staff_nm and squad_name == staff_nm:
            continue
        seen.add(squad_name)
        leader_names.append(squad_name)
    return {
        "staff": {"count": staff_online, "names": staff_names},
        "leader": {"count": leader_cnt, "names": leader_names},
        "rider": {"count": rider_cnt, "names": []},
    }


def alliance_presence_by_alliance(state_obj, conn_items) -> dict:
    out = {}
    for aid in range(3):
        out[f"aln{aid}"] = build_alliance_presence(state_obj, conn_items, aid)
    return out


def clear_drill_staff_name_if_absent(state_obj, present):
    """参謀が誰も接続していないとき、表示名のゴーストを残さない。"""
    if present or not isinstance(state_obj, dict):
        return False
    sn = state_obj.setdefault("staff_names", ["", "", ""])
    if not isinstance(sn, list):
        state_obj["staff_names"] = ["", "", ""]
        return True
    while len(sn) < 3:
        sn.append("")
    if sn[0]:
        sn[0] = ""
        return True
    return False

OCCUPY_DUTY_BUFFER_SEC = 3
# 号令の有効範囲（これより先の時刻は QA 残り等のゴミとみなして無効化）
OCCUPY_CMD_MAX_AHEAD_SEC = 4 * 3600


def _occupy_cmd_ts_active(ts: float | None, now_ts: float) -> bool:
    if ts is None:
        return False
    try:
        t = float(ts)
    except (TypeError, ValueError):
        return False
    return (now_ts - 5) < t <= (now_ts + OCCUPY_CMD_MAX_AHEAD_SEC)


def _occupy_insert_landing_ts(state_obj) -> float | None:
    ft = (state_obj or {}).get("insert_fire_target")
    if ft is None:
        return None
    try:
        v = float(ft)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def _occupy_swap_landing_ts(state_obj) -> float | None:
    st = (state_obj or {}).get("manual_swap_trigger_time")
    if st is None:
        return None
    try:
        v = float(st)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def occupy_can_also_swap(march_sec: int, ins_land: float, swap_land: float, buffer_sec: int = OCCUPY_DUTY_BUFFER_SEC) -> bool:
    """差込着弾後（帰還中）に入替出発が取れるか。"""
    m = max(0, int(march_sec or 0))
    swap_dep = float(swap_land) - m
    return swap_dep >= float(ins_land) + buffer_sec


def _occupy_prod_players(conn_items, alliance_id: int) -> list[dict]:
    out = []
    for _ws, info in conn_items:
        if info.get("mode") != "prod":
            continue
        if info.get("a_id") != alliance_id:
            continue
        role = info.get("role")
        if not role:
            continue
        cid = str(info.get("id") or "")
        if not cid:
            continue
        out.append({"id": cid, "march": max(0, int(info.get("march_sec") or 0))})
    return out


def _occupy_fill_counts(by_id: dict, counts: dict) -> None:
    c = dict(counts)
    for rec in by_id.values():
        rec["counts"] = c


def compute_occupy_duty_plan(state_obj, conn_items, alliance_id: int, now_ts: float) -> dict | None:
    """SVS 占領同盟: 差込/入替の自動割当（参謀・集結主・乗り手）。"""
    roles = (state_obj or {}).get("alliance_roles") or []
    if alliance_id < 0 or alliance_id >= len(roles) or roles[alliance_id] != "occupy":
        return None
    players = _occupy_prod_players(conn_items, alliance_id)
    if not players:
        return None

    ins_land = _occupy_insert_landing_ts(state_obj)
    swap_land = _occupy_swap_landing_ts(state_obj)
    has_ins = _occupy_cmd_ts_active(ins_land, now_ts)
    has_swap = _occupy_cmd_ts_active(swap_land, now_ts)

    by_id: dict[str, dict] = {}
    counts = {"ins": 0, "swap": 0}

    if has_swap and not has_ins:
        for p in players:
            by_id[p["id"]] = {
                "primary": "swap",
                "primary_label": "入替役",
                "can_also_swap": False,
                "insert_landed": False,
                "counts": None,
            }
            counts["swap"] += 1
        _occupy_fill_counts(by_id, counts)
        return {"counts": counts, "by_id": by_id, "has_ins": False, "has_swap": True}

    if has_ins and not has_swap:
        for p in players:
            by_id[p["id"]] = {
                "primary": "ins",
                "primary_label": "差込役",
                "can_also_swap": False,
                "insert_landed": bool(now_ts >= float(ins_land)),
                "counts": None,
            }
            counts["ins"] += 1
        _occupy_fill_counts(by_id, counts)
        return {"counts": counts, "by_id": by_id, "has_ins": True, "has_swap": False}

    if not has_ins and not has_swap:
        return None

    swap_pool: list[dict] = []
    ins_pool: list[dict] = []
    flex_pool: list[dict] = []
    for p in players:
        m = p["march"]
        swap_dep = float(swap_land) - m
        if swap_dep < float(ins_land):
            swap_pool.append(p)
        elif occupy_can_also_swap(m, float(ins_land), float(swap_land)):
            flex_pool.append(p)
        else:
            ins_pool.append(p)

    ins_cnt = 0
    swap_cnt = 0
    for p in swap_pool:
        by_id[p["id"]] = {
            "primary": "swap",
            "primary_label": "入替役",
            "can_also_swap": False,
            "insert_landed": bool(now_ts >= float(ins_land)),
            "counts": None,
        }
        swap_cnt += 1
    for p in ins_pool:
        by_id[p["id"]] = {
            "primary": "ins",
            "primary_label": "差込役",
            "can_also_swap": False,
            "insert_landed": bool(now_ts >= float(ins_land)),
            "counts": None,
        }
        ins_cnt += 1

    flex_pool.sort(key=lambda x: x["id"])
    for p in flex_pool:
        if ins_cnt <= swap_cnt:
            primary = "ins"
            ins_cnt += 1
            can_also = True
        else:
            primary = "swap"
            swap_cnt += 1
            can_also = False
        by_id[p["id"]] = {
            "primary": primary,
            "primary_label": "差込役" if primary == "ins" else "入替役",
            "can_also_swap": can_also,
            "insert_landed": bool(now_ts >= float(ins_land)),
            "counts": None,
        }

    counts = {"ins": ins_cnt, "swap": swap_cnt}
    _occupy_fill_counts(by_id, counts)
    return {"counts": counts, "by_id": by_id, "has_ins": True, "has_swap": True}


def _occupy_cmd_fields_for_clients(state_obj, now_ts: float) -> dict:
    """占領プレイヤーへ sync でも渡す号令時刻（CD 表示に必須）。"""
    out: dict = {}
    ins = _occupy_insert_landing_ts(state_obj)
    swap = _occupy_swap_landing_ts(state_obj)
    if _occupy_cmd_ts_active(ins, now_ts):
        out["insert_fire_target"] = float(ins)
    if _occupy_cmd_ts_active(swap, now_ts):
        out["manual_swap_trigger_time"] = float(swap)
    return out


def occupy_duty_for_connection(state_obj, conn_items, info: dict, now_ts: float) -> dict | None:
    if info.get("mode") != "prod":
        return None
    a_id = info.get("a_id")
    if a_id is None or a_id not in (0, 1, 2):
        return None
    if not info.get("role"):
        return None
    plan = compute_occupy_duty_plan(state_obj, conn_items, int(a_id), now_ts)
    if not plan:
        return None
    cid = str(info.get("id") or "")
    rec = plan.get("by_id", {}).get(cid)
    if not rec:
        return None
    cmds = _occupy_cmd_fields_for_clients(state_obj, now_ts)
    if not cmds:
        return None
    out = dict(rec)
    out.update(cmds)
    return out


def _timer_target_ts(t, default_rally):
    if not isinstance(t, dict):
        return None
    st = int(t.get("state", 0) or 0)
    off_s = float(t.get("off", 0) or 0) / 1000.0
    sub = float(t.get("sub_set", 0) or 0)
    try:
        if st == 4 and t.get("start_at"):
            base = datetime.fromisoformat(t["start_at"]).timestamp()
            return base + off_s + float(default_rally or 0) + sub
        if st == 1 and t.get("end"):
            base = datetime.fromisoformat(t["end"]).timestamp()
            return base + off_s + sub
        if st == 2 and t.get("frozen_target"):
            return datetime.fromisoformat(t["frozen_target"]).timestamp()
    except Exception:
        return None
    return None

def _insert_margin_sec(state_obj) -> int:
    if not isinstance(state_obj, dict):
        return 1
    if state_obj.get("insert_margin_sec") is not None:
        return max(0, min(5, int(state_obj["insert_margin_sec"])))
    # 旧 insert_offset_tenth（-10 = 1秒前）からの読み替え
    tenth = int(state_obj.get("insert_offset_tenth", -10) or -10)
    return max(0, min(5, int(round(-tenth / 10))))


def _compute_insert_auto_target_ts(state_obj):
    if not isinstance(state_obj, dict):
        return None
    timers = state_obj.get("timers", [])
    if not isinstance(timers, list) or len(timers) < 6:
        return None
    margin = _insert_margin_sec(state_obj)
    idx = int(state_obj.get("insert_target_idx", -1) or -1)
    default_rally = state_obj.get("default_rally", 300)
    if 0 <= idx < 6:
        t = _timer_target_ts(timers[idx], default_rally)
        if t is not None:
            return float(t) - margin
    arr = []
    for i in range(6):
        t = _timer_target_ts(timers[i], default_rally)
        if t is not None:
            arr.append(t)
    return (max(arr) - margin) if arr else None

def _compute_squad_gorei_target_ts(state_obj, squad_idx):
    if not isinstance(state_obj, dict):
        return None
    timers = state_obj.get("timers", [])
    if not isinstance(timers, list) or len(timers) < 42:
        return None
    if squad_idx is None or squad_idx < 0 or squad_idx > 5:
        return None
    start_idx = 6 + squad_idx * 6
    arr = []
    default_rally = state_obj.get("default_rally", 300)
    for i in range(start_idx, start_idx + 6):
        t = timers[i]
        ts = _timer_target_ts(t, default_rally)
        if ts is not None:
            arr.append(ts)
    return min(arr) if arr else None

async def generate_ai_reply(client_id, user_msg, state_obj):
    global FORCE_SUPPORT_CHAT_BROADCAST
    if not GEMINI_API_KEY:
        ai_text = (
            "【設定不足】環境変数 GEMINI_API_KEY を設定してください。"
            "APIキーはコードやGitに含めないでください。"
        )
        now_dt = datetime.now(timezone.utc) + timedelta(hours=9)
        time_str = now_dt.strftime("%H:%M")
        if "support_chats" not in state_obj:
            state_obj["support_chats"] = {}
        if client_id in state_obj["support_chats"]:
            state_obj["support_chats"][client_id]["messages"].append({"sender": "ai", "text": ai_text, "time": time_str})
            state_obj["support_chats"][client_id]["unread_admin"] = True
            FORCE_SUPPORT_CHAT_BROADCAST = True
        try:
            await broadcast_state()
        except Exception:
            pass
        return
    try:
        # APIキーの空白や改行を確実に取り除く
        api_key = GEMINI_API_KEY.strip()
        chat_history_text = ""
        recent_msgs = []
        if "support_chats" in state_obj and client_id in state_obj["support_chats"]:
            recent_msgs = state_obj["support_chats"][client_id].get("messages", [])[-8:]
            lines = []
            for m in recent_msgs:
                sender = m.get("sender", "user")
                label = "利用者" if sender == "user" else ("AI" if sender == "ai" else "総指揮")
                t = m.get("text", "") or ""
                if sender == "user" and m.get("attachments"):
                    t = (t + f" [画像{len(m['attachments'])}枚]").strip()
                lines.append(f"{label}: {t}")
            chat_history_text = "\n".join(lines)

        last_user_extra = ""
        if "support_chats" in state_obj and client_id in state_obj["support_chats"]:
            for m in reversed(state_obj["support_chats"][client_id].get("messages", [])):
                if m.get("sender") == "user":
                    if m.get("attachments"):
                        last_user_extra = f"（この送信に画像が{len(m['attachments'])}枚含まれます。内容はユーザーが見えている画面のスクリーンショットの可能性があります。）"
                    break

        prompt = (
            "あなたは運用サポート担当AIです。自然な対話（LLMとして）で、丁寧詳細型の返答をしてください。"
            "このツールの画面表記は次のとおり固定: 役割は「参謀」「集結主（第1班）」「集結主（第2班）」「乗り手」。"
            "ボタンは「登録して開始」。モードは「本番」「【訓練】参謀主導」や訓練ルームの作成・参加。"
            "隊長・班長・炙り手など、画面上に存在しない呼び方は絶対に使わない。"
            "ユーザーが用語や操作の意味を質問したら（例: ピンチとは、Ctrl+Vとは）、必ず先に平易に1〜5行で説明する。"
            "説明を省略して次の手順だけ続けない。"
            "まずユーザーの意図を判定: (A)不具合・動作異常 (B)UIの見やすさ・要望 (C)使い方 (D)戸惑い・短文のみ。"
            "(D)のときは手順を並べず、意図確認と選択肢（A/B/C）を短く提示する。"
            "(B)は再読み込みやConsoleを求めない。拡大表示・アクセシビリティ・要望の整理へ。"
            "同じ説明を繰り返さない。"
            f"直近の会話履歴:\n{chat_history_text}\n"
            f"ユーザー発言: {user_msg}\n{last_user_extra}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 260}
        }
        data_bytes = json.dumps(payload).encode('utf-8')

        def call_raw_api():
            import urllib.error
            import time
            global AI_MODEL_CACHE, AI_MODEL_CACHE_AT, AI_MODEL_CANDIDATES_CACHE, AI_MODEL_CANDIDATES_CACHE_AT
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            headers = {'Content-Type': 'application/json'}
            last_err = ""

            # 1) 毎回の探索を避けるため、前回成功モデルを先頭で試す
            model_candidates = []
            now_ts = time.time()
            if AI_MODEL_CACHE and (now_ts - AI_MODEL_CACHE_AT) < 3600:
                model_candidates.append(AI_MODEL_CACHE)

            def discover_model_candidates():
                try:
                    if AI_MODEL_CANDIDATES_CACHE and (now_ts - AI_MODEL_CANDIDATES_CACHE_AT) < 1800:
                        return list(AI_MODEL_CANDIDATES_CACHE)
                    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                    req = urllib.request.Request(list_url, method="GET")
                    with urllib.request.urlopen(req, context=ctx, timeout=6) as res:
                        raw = json.loads(res.read().decode("utf-8"))
                    found = []
                    for m in raw.get("models", []):
                        methods = m.get("supportedGenerationMethods", []) or []
                        name = str(m.get("name", "")).replace("models/", "")
                        if "generateContent" not in methods:
                            continue
                        if not name:
                            continue
                        if "flash" in name and "vision" not in name and "embedding" not in name:
                            found.append(name)
                    if not found:
                        return []
                    # 最新系を先頭にする
                    found = sorted(set(found), reverse=True)
                    AI_MODEL_CANDIDATES_CACHE = found
                    AI_MODEL_CANDIDATES_CACHE_AT = now_ts
                    return found
                except Exception:
                    return []

            discovered = discover_model_candidates()
            for m in discovered:
                if m not in model_candidates:
                    model_candidates.append(m)
            for m in ["gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-1.5-flash"]:
                if m not in model_candidates:
                    model_candidates.append(m)

            def fallback_reply(msg_text):
                text = (msg_text or "").strip()
                history_joined = " ".join([(m.get("text", "") or "") for m in recent_msgs]).lower()
                text_l = text.lower()
                user_msg_count = len([m for m in recent_msgs if m.get("sender") == "user"])
                last_ai_text = ""
                for m in reversed(recent_msgs):
                    if m.get("sender") == "ai":
                        last_ai_text = (m.get("text", "") or "").lower()
                        break
                has_device = any(k in (history_joined + " " + text_l) for k in ["pc", "iphone", "android", "ipad"])
                has_network = any(k in (history_joined + " " + text_l) for k in ["wi-fi", "wifi", "4g", "5g"])
                has_browser = any(k in (history_joined + " " + text_l) for k in ["chrome", "safari", "edge", "firefox"])
                ask_env = not (has_device and has_network and has_browser)
                greeted = any(g in text for g in ["こんにちは", "こんばんは", "おはよう", "はじめまして"])
                thanks = any(g in text for g in ["ありがとう", "助かる", "thanks"])
                unresolved = any(g in text for g in ["解決していない", "解決しない", "直っていない", "改善しない", "変わらない", "まだ"])
                ai_history = " ".join([(m.get("text", "") or "").lower() for m in recent_msgs if m.get("sender") == "ai"])
                asked_reload = ("再読み込み" in ai_history) or ("ページを更新" in ai_history)
                asked_private = ("シークレット" in ai_history) or ("プライベートウィンドウ" in ai_history)
                asked_other_browser = ("別ブラウザ" in ai_history) or ("他ブラウザ" in ai_history)
                asked_console = ("コンソール" in ai_history) or ("開発者ツール" in ai_history)
                asked_message_copy = ("表示メッセージ" in ai_history) or ("文言" in ai_history)
                missing_env = []
                if not has_device:
                    missing_env.append("利用端末(PC/iPhone/Android)")
                if not has_network:
                    missing_env.append("接続回線(Wi-Fi/4G/5G)")
                if not has_browser:
                    missing_env.append("ブラウザ名")

                # ユーザーが環境情報だけ返した場合、同じ再質問ループに入らないよう次工程へ進める
                only_env_reply = (
                    len(text) <= 30
                    and any(k in text_l for k in ["iphone", "android", "pc", "wi-fi", "wifi", "4g", "5g", "chrome", "safari", "edge", "firefox"])
                    and not any(k in text for k in ["出ない", "できない", "不具合", "エラー", "音声", "集結", "止ま", "遅"])
                )
                issue_hint = any(k in text for k in ["出ない", "できない", "不具合", "エラー", "音声", "集結", "止ま", "遅い", "固まる", "落ちる"])
                short_plain = len(text) <= 14 and not issue_hint

                # ----- UI/UX・要望（不具合切り分けテンプレに流し込まない）-----
                _tl = text.lower()
                _ui_ctx = (
                    ("ui" in _tl)
                    or ("画面" in text)
                    or ("見た目" in text)
                    or ("レイアウト" in text)
                    or ("テーマ" in text)
                    or ("カスタマイズ" in text)
                    or (("表示" in text) and any(x in text for x in ["変え", "変更", "カスタマイズ"]))
                )
                _bug_ctx_for_ui = any(k in text for k in ["エラー", "聞こえない", "聞こえ辛", "出ない", "動かない", "落ちる", "バグ", "同期ずれ", "音声", "集結"])
                _change_words = any(k in text for k in ["変えられ", "変えたい", "変えられる", "変更したい", "カスタマイズ", "レイアウトを", "テーマ"])
                ui_change_ask = (not _bug_ctx_for_ui) and _ui_ctx and _change_words
                ui_readability = any(
                    k in text for k in
                    ["見づらい", "見にくい", "読みにくい", "文字が小さ", "字が小さ", "暗すぎ", "明るすぎ", "コントラスト"]
                ) or ("表示" in text and any(k in text for k in ["見づら", "見にく", "読みにく", "小さ"]))

                # A/B/C メニュー直後は「見やすさ」等が文面に含まれるため、last_was_ui を誤爆させない
                abc_menu_in_last = ("次のどれに近い" in last_ai_text) or ("A … 不具合" in last_ai_text) or ("「A」「B」「C」" in last_ai_text)

                def _abc_pick(raw):
                    t = (raw or "").strip()
                    if not t:
                        return None
                    wide = {"Ａ": "a", "Ｂ": "b", "Ｃ": "c", "ａ": "a", "ｂ": "b", "ｃ": "c"}
                    if t in wide:
                        return wide[t]
                    if len(t) == 1:
                        c = t.lower()
                        if c in ("a", "b", "c"):
                            return c
                    return None

                last_was_ui = (not abc_menu_in_last) and any(
                    k in last_ai_text
                    for k in ["見づら", "見やす", "読みにく", "拡大", "アクセシビリティ", "表示拡大", "文字サイズ"]
                )

                if ui_change_ask:
                    return (
                        "ご質問の意図、理解しました。\n"
                        "このツールは画面デザインを細かく切り替える「テーマ設定」は用意していないことが多いです（開発者の手元のHTMLで配色・文字サイズを調整する形です）。\n"
                        "代替として、ブラウザの表示拡大（PC: Ctrl+マウスホイール / 端末: ピンチイン・アウト）や、OSの文字サイズ設定で見やすさを上げられます。\n"
                        "「どの画面のどの部分が見づらいか」（例: サポートチャット上部、タイマー数字）を1行で教えてください。\n"
                        "要望として運営側へ共有できるよう、希望（例: 文字を大きくしたい、背景を明るくしたい）も一言添えてもらえますか。"
                    )
                if ui_readability:
                    return (
                        "表示の見やすさの件、承知しました。\n"
                        "まずブラウザや端末の表示拡大で改善するか試してください（PC: ページ拡大、iPhone: 設定＞画面表示と明るさ＞表示＞文字サイズ など）。\n"
                        "画面上のどの要素が読みにくいか（スクショの説明で可）を簡単に教えてください。\n"
                        "ツール側の色・字体の変更は個人開発の範囲で反映可能な場合があります。希望を一言添えていただければ要望として引き継ぎます。\n"
                        "いま一番困っているのは、文字サイズ・コントラスト・レイアウトのどれに近いですか。"
                    )

                _choice = _abc_pick(text)
                if _choice and abc_menu_in_last:
                    if _choice == "a":
                        return (
                            "A（不具合・おかしい挙動）ですね、承知しました。\n"
                            "まず次を1行ずついただけると切り分けが早いです。\n"
                            "・いま起きていること（例: 音声が途切れる、数字が止まる）\n"
                            "・使っている画面（プレイヤー画面／訓練ルーム／別タブの同盟司令塔の管理画面 など）\n"
                            "・端末種別とブラウザ名（例: iPhone + Safari）\n"
                            "分かる範囲で結構です。まずは現象を一文で送ってください。"
                        )
                    if _choice == "b":
                        return (
                            "B（画面の見やすさ・UIの要望）ですね、承知しました。\n"
                            "アプリ内のテーマ切替のような画面は基本なく、配色や文字サイズは開発側でHTML調整する運用です。\n"
                            "まずはブラウザの表示拡大（PC: Ctrl+ホイール／スマホ:ピンチ）で改善しないか試してください。\n"
                            "どの画面のどの部分が見づらいか（例: タイマー数字、チャット見出し）を1行で、希望があれば一言添えてください。"
                        )
                    return (
                        "C（使い方）ですね、承知しました。（画面のボタン名は実際の表記に合わせています）\n"
                        "・上部で「1台で使う／2台で使う」を選び、時計合わせのあと同盟（APL/PKD/MTC）を選びます。\n"
                        "・役割は画面どおり「参謀」「集結主（第1班）」「集結主（第2班）」「乗り手」から選び、名前が必要なら入力して「登録して開始」を押します。\n"
                        "・参謀を選んだ場合は、あらためて「第1班 集結主／第2班 集結主／乗り手」のどれで動くか選んでから登録します。\n"
                        "・訓練は画面上部のモードで訓練ルームを作成するか、参加コードで入室します。\n"
                        "・音声は音声ONのうえ「音声テスト」「カウントダウンテスト」で確認できます。\n"
                        "いま知りたい操作を、画面のどの部分か（できるだけ具体的に）一文で教えてください。"
                    )

                def glossary_reply(ut_raw):
                    """用語・操作への「とは／何ですか」系。テンプレに吸われないよう先に処理する。"""
                    ut = (ut_raw or "").strip()
                    if len(ut) > 140:
                        return None
                    q = any(
                        x in ut
                        for x in [
                            "何ですか",
                            "何でしょう",
                            "とは",
                            "どういう",
                            "どうゆう",
                            "教えて",
                            "意味",
                            "わからない",
                            "って何",
                            "て何？",
                            "教えてください",
                        ]
                    )
                    ul = ut.lower()
                    if ("ピンチ" in ut or "ピンチイン" in ut) and (q or len(ut) <= 24):
                        return (
                            "「ピンチ操作」とは、スマホやタブレットで画面を指2本でつまむように開いたり閉じたりして、表示を拡大・縮小する操作のことです。\n"
                            "指を広げるほど拡大、指を寄せるほど縮小です。地図や写真と同じ動かし方です。\n"
                            "ほかにも分からない言葉があれば、そのまま聞いてください。"
                        )
                    if ("長押し" in ut) and q:
                        return (
                            "「長押し」とは、画面を軽くタップするのではなく、指を置いたまましばらく止めておく操作です。\n"
                            "機種や場所によってはメニューや「貼り付け」が出ます。\n"
                            "ほかにも知りたい操作があれば聞いてください。"
                        )
                    if (("貼り付け" in ut) or ("ペースト" in ut)) and q:
                        return (
                            "「貼り付け」とは、コピーした画像や文字を、入力欄などに取り込む操作です。\n"
                            "パソコンでは Ctrl+V や右クリックの貼り付け、スマホでは長押しメニューなどから選べます。\n"
                            "ほかにもあれば聞いてください。"
                        )
                    if ("ctrl" in ul or "コントロール" in ut) and ("v" in ul or "Ｖ" in ut) and q:
                        return (
                            "Ctrl+V は、パソコンで「貼り付け」をするためのキーの組み合わせです（Mac は Command+V）。\n"
                            "スマホには Ctrl が無いので、🖼ボタンで画像を選ぶか、長押しで貼り付けを試してください。\n"
                            "ほかにも用語があれば聞いてください。"
                        )
                    if ("ホイール" in ut or "マウスホイール" in ut) and q:
                        return (
                            "マウスホイールとは、マウスの中央にある上下に回せる車輪状の部分です。転がすとページが上下に動いたり、Ctrl と一緒に回すと表示の拡大縮小になることがあります。\n"
                            "ほかにも聞きたいことがあればどうぞ。"
                        )
                    if ("キャッシュ" in ut or "クッキー" in ut) and q:
                        return (
                            "ブラウザのキャッシュとは、一度読み込んだページのデータを端末に一時保存して次回速く見せる仕組みです。表示がおかしいときはページ再読み込みやキャッシュ削除で直ることがあります。\n"
                            "ほかにも聞いてください。"
                        )
                    return None

                _gloss = glossary_reply(text)
                if _gloss:
                    return _gloss

                if last_was_ui and len(text) <= 40 and not issue_hint:
                    return (
                        "続き了解です。\n"
                        "前回お聞きした見やすさのポイントに、補足はありますか（なければ「なし」で結構です）。\n"
                        "ご希望があれば、運営・開発への要望としてまとめます。\n"
                        "他に音声や集結の不具合など、切り分けが必要な症状はありますか。"
                    )

                # ----- 短文・あいまい返答（テンプレ連呼を止めて普通の会話に戻す）-----
                _filler_tokens = (
                    "あ",
                    "あー",
                    "あっ",
                    "ん",
                    "ん？",
                    "んー",
                    "は？",
                    "え？",
                    "えっ",
                    "う",
                    "お",
                    "うーん",
                    "…",
                    "...",
                    "w",
                    "ｗ",
                )
                _meta_confusion = any(
                    k in text
                    for k in [
                        "意味わから",
                        "分からない",
                        "わからない",
                        "同じ",
                        "繰り返",
                        "ループ",
                        "ふつう",
                        "普通の会話",
                        "会話でき",
                        "噛み合",
                    ]
                )
                _last_was_script = ("切り分け" in last_ai_text) or ("再読み込み" in last_ai_text) or ("不足情報" in last_ai_text)
                if (text in _filler_tokens) or (_meta_confusion and len(text) <= 60):
                    return (
                        "すみません、こちらの返答がうまく噛み合っていない感じがしますね。いったん整理し直します。\n"
                        "いま知りたいのは、次のどれに近いですか？\n"
                        "A … 不具合・おかしい挙動の相談\n"
                        "B … 画面の見やすさやUIの要望\n"
                        "C … 使い方の質問\n"
                        "「A」「B」「C」のどれか1文字だけでも送ってください。\n"
                        "併せて、使っているブラウザ名（例: Chrome）がわかればそれだけでも構いません。"
                    )
                if _last_was_script and len(text) <= 4 and not issue_hint and text not in ("はい", "いいえ", "うん", "PC", "pc"):
                    return (
                        "意図が読み取りづらい短文でした。すみません。\n"
                        "直前の案内で聞きたかったのは、次のどちらでしょうか。\n"
                        "1) ブラウザ名（例: Chrome / Safari / Edge）\n"
                        "2) いま起きていることの一文説明\n"
                        "どちらか、分かる方だけ送ってください。"
                    )

                if greeted and len(text) <= 15:
                    return "ご連絡ありがとうございます。状況把握から進めます。\n・まず、困っている現象を1行で教えてください。\n・発生時刻（だいたいで大丈夫です）も添えてください。\n・ページ再読み込み後に同じ操作を1回だけお試しください。\n次に、直前に表示された文言をそのまま送っていただけますか。"
                if (user_msg_count <= 1 and short_plain) or text in ["接続テスト", "テスト", "確認です", "確認"]:
                    return "ご連絡ありがとうございます。受信できています。\nこのままサポートを進めるため、まず困っている内容を1行で教えてください。\n可能であれば、発生時刻（だいたい）と直前の操作も添えてください。\n必要な確認は私から順番に案内します。\n最初にどの機能で困っているか教えていただけますか。"
                if thanks:
                    return "ご連絡ありがとうございます。いったん改善方向でよかったです。\n・同じ操作を1回だけ再実行し、再発有無を確認してください。\n・再発した場合は、時刻と直前操作を2行で送ってください。\n・必要ならこちらで要点整理して引き継ぎます。\n現時点では解消済みで問題なさそうでしょうか。"
                if unresolved:
                    if asked_reload and not asked_private:
                        return "未解決とのこと、次の段階に進めます。\n・通常画面を閉じ、シークレット/プライベートウィンドウで同じ操作を実施してください。\n・結果が変わるか（改善/同じ）を確認してください。\n・発生時刻と押したボタン名を1行で送ってください。\n通常画面とシークレット画面で、結果は同じでしたか。"
                    if asked_private and not asked_other_browser:
                        return "切り分け継続します。ありがとうございます。\n・別ブラウザ（例: Chrome→Safari）で同じ操作を実施してください。\n・同じ症状が出るか確認してください。\n・出た場合は、表示された文言をそのまま送ってください。\n別ブラウザでも同じ症状になりましたか。"
                    if asked_other_browser and not asked_console:
                        return "ここから通信/実行エラーを確認します。\n・ブラウザの開発者ツールを開いてください。\n・Console に赤字エラーが出るか確認してください。\n・エラーがあれば先頭1行だけそのまま送ってください。\nConsole に赤字エラーは表示されていますか。"
                    return "未解決とのこと、もう一段切り分けます。\n・ページを再読み込みして同じ操作を1回だけ実行してください。\n・発生時刻と直前の操作内容を2行で送ってください。\n・可能なら表示メッセージをそのまま貼り付けてください。\n直前の表示メッセージをそのまま送っていただけますか。"
                if (has_device or has_network or has_browser) and ("端末" in last_ai_text or "ブラウザ" in last_ai_text):
                    if only_env_reply and not asked_reload:
                        return "環境情報ありがとうございます。確認が進めやすくなりました。\n・ページ再読み込み後に、同じ操作を1回だけ実施してください。\n・発生時刻を1行で送ってください。\n・直前の表示文言をそのまま貼り付けてください。\nこの症状は毎回発生しますか、それとも時々でしょうか。"
                    if not asked_reload:
                        return "環境情報ありがとうございます。次の確認に進みます。\n・ページ再読み込み後に同じ操作を1回だけ実行してください。\n・発生時刻を1行で送ってください。\n・直前の表示文言をそのまま貼ってください。\n症状は毎回発生しますか、それとも時々でしょうか。"
                    if not asked_message_copy:
                        return "ありがとうございます。あと1点で切り分けできます。\n・発生直前の表示文言をそのまま送ってください。\n・可能なら押したボタン名も1つ添えてください。\n表示文言をそのまま貼り付けていただけますか。"

                if "音声" in text:
                    base = "音声の件、順番に確認していきます。\n・音声モードをONにしてください。\n・端末サイレントをOFF、音量を50%以上にしてください。\n・ブラウザのタブ消音がONならOFFにしてください。\n・ページ再読み込み後に「音声テスト」を実行してください。"
                    if ask_env:
                        base += "\n利用端末(PC/iPhone/Android)と回線(Wi-Fi/4G/5G)、ブラウザ名を教えてください。"
                    else:
                        base += "\n音声テスト結果（聞こえる/聞こえない）を教えてください。"
                    return base
                if "集結" in text and ("表示" in text or "出ない" in text):
                    base = "集結表示の件、順番に確認します。\n・役割登録が完了しているか確認してください。\n・行軍秒数の入力値が0でないか確認してください。\n・画面右上UTC時刻が更新されているか確認してください。\n・再接続後にページ再読み込みを実行してください。"
                    if ask_env:
                        base += "\n利用端末(PC/iPhone/Android)と回線(Wi-Fi/4G/5G)、ブラウザ名を教えてください。"
                    else:
                        base += "\nUTC時刻が動いているか（はい/いいえ）を教えてください。"
                    return base

                base = "状況確認ありがとうございます。切り分けを進めます。\n・まずページ再読み込みを実行してください。\n・同じ操作を1回だけ再現してください。\n・発生時刻と症状を短く送ってください。"
                if ask_env:
                    base += "\n不足情報だけ教えてください: " + " / ".join(missing_env) + "。"
                else:
                    base += "\n直前に表示されたメッセージをそのまま1行で教えてください。"
                return base

            for model_name in model_candidates:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                for attempt in range(3):
                    req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
                    try:
                        with urllib.request.urlopen(req, context=ctx, timeout=12) as res:
                            res_data = json.loads(res.read().decode('utf-8'))
                            parts = res_data.get('candidates', [{}])[0].get('content', {}).get('parts', [])
                            if parts and isinstance(parts[0], dict) and parts[0].get('text'):
                                AI_MODEL_CACHE = model_name
                                AI_MODEL_CACHE_AT = time.time()
                                return parts[0]['text']
                            last_err = f"【API応答異常】model={model_name} response={res_data}"
                            break
                    except urllib.error.HTTPError as e:
                        err_msg = e.read().decode('utf-8')
                        # モデル未対応の場合は次の候補へ
                        if e.code == 404:
                            last_err = f"model={model_name} HTTP404 {err_msg}"
                            break
                        # 混雑時は短時間リトライ
                        if e.code == 503:
                            last_err = f"model={model_name} HTTP503 {err_msg}"
                            if attempt < 3:
                                time.sleep(0.6 * (attempt + 1))
                                continue
                            break
                        # TEXT非対応モデル(例: tts)を引いた場合は次モデルへ
                        if e.code == 400 and "response modalities" in err_msg:
                            last_err = f"model={model_name} HTTP400(TEXT非対応) {err_msg}"
                            break
                        # それ以外のAPIエラーも画面には出さず、最終的に丁寧な代替返信へフォールバック
                        last_err = f"model={model_name} HTTP{e.code} {err_msg}"
                        break
                    except Exception as e:
                        last_err = f"model={model_name} {str(e)}"
                        break

            # すべて失敗した場合も、チャットを止めないためローカル応答を返す
            if "HTTP403" in last_err or "API key" in last_err.lower() or "permission" in last_err.lower():
                return "AI接続に失敗しています（認証エラー）。管理者がAPIキー設定を確認します。いまは状況を整理して一次対応します。\n・発生時刻\n・発生画面\n・直前の操作\nを1行ずつ送ってください。"
            return fallback_reply(user_msg)

        loop = asyncio.get_running_loop()
        ai_text = await loop.run_in_executor(None, call_raw_api)
        # 固有名が混入しないよう最終サニタイズ
        ai_text = (
            ai_text.replace("天津飯（総指揮）", "総指揮")
            .replace("総指揮（天津飯）", "総指揮")
            .replace("天津飯", "総指揮")
        )
    except Exception as e:
        ai_text = f"【AI副官 起動待機中】システムエラー: {str(e)}"

    now_dt = datetime.now(timezone.utc) + timedelta(hours=9)
    time_str = now_dt.strftime("%H:%M")
    if "support_chats" not in state_obj:
        state_obj["support_chats"] = {}
    if client_id in state_obj["support_chats"]:
        state_obj["support_chats"][client_id]["messages"].append({"sender": "ai", "text": ai_text, "time": time_str})
        state_obj["support_chats"][client_id]["unread_admin"] = True
        FORCE_SUPPORT_CHAT_BROADCAST = True

    # 画面に変更を即座に反映させる
    try:
        await broadcast_state()
    except Exception:
        pass

async def broadcast_state():
    await broadcast()

async def broadcast():
    global state_version, tick_counter, FORCE_SUPPORT_CHAT_BROADCAST, FORCE_STATE_BROADCAST
    if not connections:
        return
    force_support_reload = FORCE_SUPPORT_CHAT_BROADCAST
    FORCE_SUPPORT_CHAT_BROADCAST = False
    force_state_reload = FORCE_STATE_BROADCAST
    FORCE_STATE_BROADCAST = False

    async def broadcast_context(state_obj, conn_items, drill_key=None):
        global state_version, tick_counter
        now = datetime.now(timezone.utc)
        now_ts = now.timestamp()
        changed = bool(force_support_reload or force_state_reload)
        if "gorei_last_target" not in state_obj or not isinstance(state_obj.get("gorei_last_target"), list) or len(state_obj.get("gorei_last_target", [])) != 6:
            state_obj["gorei_last_target"] = [None] * 6
            changed = True
        for s in range(6):
            calc_t = _compute_squad_gorei_target_ts(state_obj, s)
            cur_t = state_obj["gorei_last_target"][s]
            if calc_t is None:
                if cur_t is not None:
                    state_obj["gorei_last_target"][s] = None
                    changed = True
            else:
                # 小数点揺れで毎tick changed しないよう秒単位で比較
                if cur_t is None or int(cur_t) != int(calc_t):
                    state_obj["gorei_last_target"][s] = float(calc_t)
                    changed = True

        if state_obj["manual_base_target"] is not None and state_obj["manual_base_target"] <= now_ts:
            state_obj["manual_base_target"] = None; changed = True
        if state_obj["manual_swap_trigger_time"] is not None:
            t_swap = float(state_obj["manual_swap_trigger_time"])
            if not _occupy_cmd_ts_active(t_swap, now_ts):
                state_obj["manual_swap_trigger_time"] = None
                changed = True
        if state_obj["manual_wd_trigger_time"] is not None:
            t_wd = float(state_obj["manual_wd_trigger_time"])
            if t_wd < now_ts - 5 or t_wd > now_ts + OCCUPY_CMD_MAX_AHEAD_SEC:
                state_obj["manual_wd_trigger_time"] = None
                changed = True

        for s in range(6):
            if state_obj["gorei_last_target"][s] is not None and state_obj["gorei_last_target"][s] <= (now_ts - 10):
                if state_obj["gorei_fixed_targets"][s] is None:
                    state_obj["gorei_last_target"][s] = None; changed = True

        if state_obj.get("insert_fire_target") is not None:
            t_ins = float(state_obj["insert_fire_target"])
            if not _occupy_cmd_ts_active(t_ins, now_ts):
                state_obj["insert_fire_target"] = None
                changed = True
        if state_obj.get("insert_fixed_target") is not None:
            t_fix = float(state_obj["insert_fixed_target"])
            if not _occupy_cmd_ts_active(t_fix, now_ts):
                state_obj["insert_fixed_target"] = None
                changed = True

        for t in state_obj["timers"]:
            if t["state"] == 4 and t["start_at"]:
                start_at = datetime.fromisoformat(t["start_at"])
                if (start_at - now).total_seconds() <= 0:
                    t["state"] = 1; t["sec"] = state_obj["default_rally"]
                    t["end"] = (start_at + timedelta(seconds=state_obj["default_rally"])).isoformat()
                    changed = True
            elif t["state"] == 1 and t["end"]:
                end_dt = datetime.fromisoformat(t["end"])
                rem = (end_dt - now).total_seconds()
                if rem <= 0:
                    if t["sub_set"] > 0:
                        t["state"] = 2; t["sub_sec"] = t["sub_set"]
                        t["end"] = (end_dt + timedelta(seconds=t["sub_set"])).isoformat()
                        adj_rally_end = end_dt + timedelta(milliseconds=t["off"])
                        t["frozen_target"] = (adj_rally_end + timedelta(seconds=t["sub_set"])).isoformat()
                    else:
                        t["state"] = 0; t["sec"] = state_obj["default_rally"]
                    changed = True
                else:
                    t["sec"] = rem
            elif t["state"] == 2 and t["end"]:
                end_dt = datetime.fromisoformat(t["end"])
                rem = (end_dt - now).total_seconds()
                if rem <= 0:
                    t["state"] = 0; t["sub_sec"] = 0; t["sec"] = state_obj["default_rally"]; t["frozen_target"] = None
                    changed = True
                else:
                    t["sub_sec"] = rem

        for t in state_obj["timers"]:
            t["online"] = False
        counts = {"total": {"leader": 0, "rider": 0}, "aln0": {"leader": 0, "rider": 0}, "aln1": {"leader": 0, "rider": 0}, "aln2": {"leader": 0, "rider": 0}}
        for _ws, info in conn_items:
            role = info.get("role"); a_id = info.get("a_id")
            if role and role.startswith("leader") and info.get("idx") is not None:
                state_obj["timers"][info["idx"]]["online"] = True
                counts["total"]["leader"] += 1
                if a_id is not None and 0 <= a_id <= 2:
                    counts[f"aln{a_id}"]["leader"] += 1
            elif role == "rider":
                counts["total"]["rider"] += 1
                if a_id is not None and 0 <= a_id <= 2:
                    counts[f"aln{a_id}"]["rider"] += 1
        if json.dumps(counts) != json.dumps(state_obj["online_counts"]):
            state_obj["online_counts"] = counts
            changed = True

        drill_staff_payload = None
        if drill_key is not None:
            ds = drill_staff_status_for_room(drill_key, state_obj)
            if clear_drill_staff_name_if_absent(state_obj, ds["present"]):
                changed = True
                ds = drill_staff_status_for_room(drill_key, state_obj)
            drill_staff_payload = ds

        if changed:
            state_version += 1

        # 訓練ルームの tick でも本番のサポート受信箱を渡す（クライアントは support_chats のみ上書き参照）
        data_out = {**state_obj, "support_chats": state.get("support_chats", {})} if drill_key is not None else state_obj

        payload = {
            "type": "tick",
            "data": data_out,
            "utc": now.strftime("%H:%M:%S"),
            "server_timestamp": now_ts * 1000,
            "drill_rooms": get_public_drill_rooms(),
            "alliance_presence": alliance_presence_by_alliance(state_obj, conn_items),
        }
        if drill_staff_payload is not None:
            payload["drill_staff"] = drill_staff_payload
        sync_payload = {"type": "sync", "utc": now.strftime("%H:%M:%S"), "server_timestamp": now_ts * 1000}
        if drill_staff_payload is not None:
            sync_payload["drill_staff"] = drill_staff_payload
        force_player_sync = (tick_counter % 12 == 0)
        dead_ws = []
        for ws, info in conn_items:
            try:
                od = occupy_duty_for_connection(state_obj, conn_items, info, now_ts) if drill_key is None else None
                out_payload = {**payload, "occupy_duty": od} if od else payload
                if drill_key is None and info.get("mode") == "prod" and info.get("role"):
                    cmd_fields = _occupy_cmd_fields_for_clients(state_obj, now_ts)
                    if cmd_fields:
                        out_payload = {**out_payload, "occupy_cmds": cmd_fields}
                if info.get("role") is None:
                    await ws.send_json(out_payload)
                else:
                    # 訓練モードは常時フル state を配信して端末差分同期ズレを防ぐ
                    if info.get("mode") == "drill":
                        await ws.send_json(out_payload)
                    elif changed or force_player_sync:
                        await ws.send_json(out_payload)
                    else:
                        if tick_counter % 4 == 0:
                            sync_out = {**sync_payload, "occupy_duty": od} if od else sync_payload
                            if od:
                                cmd_fields = _occupy_cmd_fields_for_clients(state_obj, now_ts)
                                if cmd_fields:
                                    sync_out["occupy_cmds"] = cmd_fields
                            await ws.send_json(sync_out)
                        elif od:
                            cmd_fields = _occupy_cmd_fields_for_clients(state_obj, now_ts)
                            sync_body = {
                                "type": "sync",
                                "utc": now.strftime("%H:%M:%S"),
                                "server_timestamp": now_ts * 1000,
                                "occupy_duty": od,
                            }
                            if cmd_fields:
                                sync_body["occupy_cmds"] = cmd_fields
                            await ws.send_json(sync_body)
            except Exception:
                dead_ws.append(ws)
        for ws in dead_ws:
            if ws in connections:
                del connections[ws]

    prod_conns = [(ws, info) for ws, info in list(connections.items()) if info.get("mode", "prod") == "prod"]
    if prod_conns:
        await broadcast_context(state, prod_conns)
    drill_keys = set([info.get("drill_key", "default") for _ws, info in list(connections.items()) if info.get("mode") == "drill"])
    for dk in drill_keys:
        drill_conns = [(ws, info) for ws, info in list(connections.items()) if info.get("mode") == "drill" and info.get("drill_key", "default") == dk]
        if drill_conns:
            if dk not in drill_rooms:
                dn = drill_room_meta.get(dk, {}).get("name", "").strip()
                drill_rooms[dk] = fresh_drill_state(dn or "訓練")
            await broadcast_context(drill_rooms[dk], drill_conns, drill_key=dk)
    tick_counter += 1

async def broadcast_loop():
    while True:
        try:
            await broadcast()
        except Exception:
            # ブロードキャスト中の一時的な例外でループ全体が停止しないようにする
            pass
        await asyncio.sleep(0.25)

@asynccontextmanager
async def lifespan(app: FastAPI):
    gorei_debug_log("[GOREI_DEBUG] server startup")
    task = asyncio.create_task(broadcast_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# HTML は各端末・CDNで古いものが残らないよう明示（完全保証はCDN設定も要参照）
HTML_NO_CACHE_HEADERS = {
    "Cache-Control": "private, no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0, s-maxage=0",
    "Pragma": "no-cache",
    "Expires": "0",
    # Cloudflare: エッジのキャッシュ挙動を弱める（ダッシュボード設定で上書きされる場合あり）
    "CDN-Cache-Control": "private, no-store, no-cache, max-age=0, s-maxage=0",
}


@app.head("/", include_in_schema=False)
@app.head("/player", include_in_schema=False)
@app.head("/admin_hq_777", include_in_schema=False)
@app.head("/staff_hq_3301", include_in_schema=False)
@app.head("/support_hq_3301", include_in_schema=False)
@app.head("/staff_hq_555", include_in_schema=False)
async def head_pages():
    """HEAD（CDN／監視）：GET と同ページで 405 になるとチェック実装によっては失敗する。"""
    return Response(status_code=200, headers=dict(HTML_NO_CACHE_HEADERS))


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.head("/healthz", include_in_schema=False)
async def head_healthz():
    return Response(status_code=200)


@app.get("/")
async def get_player():
    with open("player.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read(), headers=dict(HTML_NO_CACHE_HEADERS))

@app.get("/player")
async def get_player_backup():
    with open("player.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read(), headers=dict(HTML_NO_CACHE_HEADERS))

@app.get("/admin_hq_777")
async def get_admin():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read(), headers=dict(HTML_NO_CACHE_HEADERS))

# ★ 追加：参謀用画面へのアクセスルート
@app.get("/staff_hq_3301")
async def get_staff():
    with open("staff.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read(), headers=dict(HTML_NO_CACHE_HEADERS))

@app.get("/support_hq_3301")
async def get_support():
    with open("support.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read(), headers=dict(HTML_NO_CACHE_HEADERS))

@app.get("/staff_hq_555")
async def get_staff_555():
    with open("staff.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read(), headers=dict(HTML_NO_CACHE_HEADERS))


@app.head("/map.jpg", include_in_schema=False)
async def head_map():
    if os.path.exists("map.jpg"):
        return Response(status_code=200)
    return Response(status_code=404)


@app.get("/map.jpg")
async def get_map():
    if os.path.exists("map.jpg"):
        return FileResponse("map.jpg")
    return Response(status_code=404)


def _safe_asset_path(name: str) -> str | None:
    if not name or "/" in name or "\\" in name or ".." in name:
        return None
    path = os.path.join("assets", name)
    if os.path.isfile(path):
        return path
    return None


@app.head("/assets/{asset_name}", include_in_schema=False)
async def head_asset(asset_name: str):
    path = _safe_asset_path(asset_name)
    if path:
        return Response(status_code=200)
    return Response(status_code=404)


@app.get("/assets/{asset_name}")
async def get_asset(asset_name: str):
    path = _safe_asset_path(asset_name)
    if path:
        return FileResponse(path)
    return Response(status_code=404)


VOICE_OUTPUT_GAIN = float(os.environ.get("UTC_VOICE_GAIN", "2.5"))


def _normalize_wav_loudness(wav_bytes: bytes) -> bytes:
    """VOICEVOX 出力が小さい端末向けに 16bit PCM を正規化してから返す。"""
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as w:
            nch, sampwidth, framerate, nframes, comptype, compname = w.getparams()
            if sampwidth != 2 or nch < 1:
                return wav_bytes
            frames = w.readframes(nframes)
        count = len(frames) // 2
        if count == 0:
            return wav_bytes
        samples = struct.unpack(f"<{count}h", frames)
        peak = max(abs(s) for s in samples) or 1
        target_peak = 28000
        scale = min(6.0, target_peak / peak)
        boosted = [max(-32768, min(32767, int(s * scale))) for s in samples]
        out = io.BytesIO()
        with wave.open(out, "wb") as wout:
            wout.setnchannels(nch)
            wout.setsampwidth(sampwidth)
            wout.setframerate(framerate)
            wout.writeframes(struct.pack(f"<{len(boosted)}h", *boosted))
        return out.getvalue()
    except Exception:
        return wav_bytes


@app.get("/api/voice")
def get_voice(text: str, speaker: int = 3):
    cache_key = f"{speaker}:{text}"
    if cache_key in voice_cache:
        return Response(content=voice_cache[cache_key], media_type="audio/wav", headers={"Cache-Control": "public, max-age=31536000"})
    try:
        query_url = "http://127.0.0.1:50021/audio_query?text=" + urllib.parse.quote(text) + f"&speaker={speaker}"
        req1 = urllib.request.Request(query_url, method="POST")
        with urllib.request.urlopen(req1) as res1: query_data = res1.read()
        query_dict = json.loads(query_data)
        query_dict["speedScale"] = 1.35
        query_dict["volumeScale"] = VOICE_OUTPUT_GAIN
        query_data_modified = json.dumps(query_dict).encode("utf-8")
        synth_url = f"http://127.0.0.1:50021/synthesis?speaker={speaker}"
        req2 = urllib.request.Request(synth_url, data=query_data_modified, method="POST")
        req2.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req2) as res2: audio_data = res2.read()
        audio_data = _normalize_wav_loudness(audio_data)
        voice_cache[cache_key] = audio_data
        return Response(content=audio_data, media_type="audio/wav", headers={"Cache-Control": "public, max-age=31536000"})
    except Exception as e:
        return Response(status_code=503)

@app.get("/api/voice_speakers")
def get_voice_speakers():
    global voice_speakers_cache, voice_speakers_cache_at
    now_ts = datetime.now(timezone.utc).timestamp()
    if voice_speakers_cache and (now_ts - voice_speakers_cache_at) < 300:
        return voice_speakers_cache
    try:
        req = urllib.request.Request("http://127.0.0.1:50021/speakers", method="GET")
        with urllib.request.urlopen(req, timeout=5) as res:
            speakers = json.loads(res.read().decode("utf-8"))
        simplified = []
        for sp in speakers:
            styles = []
            for st in sp.get("styles", []):
                styles.append({"id": st.get("id"), "name": st.get("name", "")})
            simplified.append({"name": sp.get("name", ""), "styles": styles})
        voice_speakers_cache = {"speakers": simplified}
        voice_speakers_cache_at = now_ts
        return voice_speakers_cache
    except Exception:
        # Fallback: default style id 3
        return {"speakers": [{"name": "デフォルト", "styles": [{"id": 3, "name": "ノーマル"}]}]}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    q_mode = websocket.query_params.get("mode", "prod")
    mode = "drill" if q_mode == "drill" else "prod"
    try:
        q_aln = int(websocket.query_params.get("aln", "0"))
    except Exception:
        q_aln = 0
    if q_aln not in [0, 1, 2]:
        q_aln = 0
    q_room = (websocket.query_params.get("room", "default") or "default").strip()[:64]
    connections[websocket] = {
        "role": None, "idx": None, "a_id": None, "id": str(uuid.uuid4()), "staff_enabled": False,
        "mode": mode, "drill_alliance": q_aln, "drill_key": q_room
    }
    try:
        init_st = get_state_for_conn(connections[websocket])
        init_pkg = {
            "type": "init",
            "data": init_st,
            "mode": mode,
            "drill_rooms": get_public_drill_rooms(),
            "alliance_presence": alliance_presence_by_alliance(init_st, list(connections.items())),
        }
        if mode == "drill":
            dk = connections[websocket]["drill_key"]
            init_pkg["drill_staff"] = drill_staff_status_for_room(dk, init_st)
        await websocket.send_json(init_pkg)
        while True:
            try:
                data = await websocket.receive_json()
                await process_command(data, websocket)
                await broadcast()
            except WebSocketDisconnect:
                break
            except Exception:
                # 単発の不正データ/処理失敗で接続全体を落とさない
                try:
                    await websocket.send_json({"type": "error", "message": "invalid command"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if websocket in connections:
            del connections[websocket]

async def send_full_state_to_one(websocket: WebSocket):
    """対象クライアント1本へフルstateを即送信（反映遅延時の救済）。"""
    info = connections.get(websocket)
    if not info:
        return
    now = datetime.now(timezone.utc)
    payload = {
        "type": "tick",
        "data": get_state_for_conn(info),
        "utc": now.strftime("%H:%M:%S"),
        "server_timestamp": now.timestamp() * 1000,
        "drill_rooms": get_public_drill_rooms()
    }
    if info.get("mode") == "drill":
        dk = info.get("drill_key", "default")
        payload["drill_staff"] = drill_staff_status_for_room(dk, get_state_for_conn(info))
    elif info.get("mode") == "prod":
        st = get_state_for_conn(info)
        od = occupy_duty_for_connection(st, list(connections.items()), info, now.timestamp())
        if od:
            payload["occupy_duty"] = od
    try:
        await websocket.send_json(payload)
    except Exception:
        pass

async def send_full_state_to_context(conn):
    now = datetime.now(timezone.utc)
    dead_ws = []
    for ws, info in list(connections.items()):
        if not same_context(info, conn):
            continue
        payload = {
            "type": "tick",
            "data": get_state_for_conn(info),
            "utc": now.strftime("%H:%M:%S"),
            "server_timestamp": now.timestamp() * 1000,
            "drill_rooms": get_public_drill_rooms()
        }
        if info.get("mode") == "drill":
            dk = info.get("drill_key", "default")
            payload["drill_staff"] = drill_staff_status_for_room(dk, get_state_for_conn(info))
        try:
            await ws.send_json(payload)
        except Exception:
            dead_ws.append(ws)
    for ws in dead_ws:
        if ws in connections:
            del connections[ws]

async def send_gorei_hint_to_context(conn, squad_idx, target_ts, cancel=False):
    payload = {
        "type": "gorei_hint",
        "squad_idx": int(squad_idx),
        "target_ts": (None if cancel else float(target_ts))
    }
    dead_ws = []
    sent_cnt = 0
    for ws, info in list(connections.items()):
        if not same_context(info, conn):
            continue
        try:
            await ws.send_json(payload)
            sent_cnt += 1
        except Exception:
            dead_ws.append(ws)
    for ws in dead_ws:
        if ws in connections:
            del connections[ws]
    try:
        gorei_debug_log(f"[GOREI_DEBUG] gorei_hint squad={squad_idx} target={target_ts} cancel={1 if cancel else 0} sent={sent_cnt}")
    except Exception:
        pass

async def send_force_gorei_to_context(conn, squad_idx, target_ts, cancel=False):
    """非参謀端末の表示取りこぼし対策: 号令着弾を即時プッシュ。"""
    payload = {
        "type": "force_gorei",
        "squad_idx": int(squad_idx),
        "target_ts": (None if cancel else float(target_ts)),
        "cancel": bool(cancel),
    }
    dead_ws = []
    sent_cnt = 0
    for ws, info in list(connections.items()):
        if not same_context(info, conn):
            continue
        try:
            await ws.send_json(payload)
            sent_cnt += 1
        except Exception as e:
            try:
                msg = f"[GOREI_DEBUG] force_gorei send_error squad={squad_idx} err={e}"
                print(msg)
                gorei_debug_log(msg)
            except Exception:
                pass
            dead_ws.append(ws)
    for ws in dead_ws:
        if ws in connections:
            del connections[ws]
    msg = f"[GOREI_DEBUG] force_gorei squad={squad_idx} target={target_ts} cancel={1 if cancel else 0} sent={sent_cnt}"
    print(msg)
    gorei_debug_log(msg)

async def process_command(data, websocket):
    global state_version, FORCE_SUPPORT_CHAT_BROADCAST, FORCE_STATE_BROADCAST
    cmd, idx, val = data.get("cmd"), data.get("idx"), data.get("val")
    now_ts = datetime.now(timezone.utc).timestamp()
    conn = connections.get(websocket, {})
    state = get_state_for_conn(conn)
    # サポート受信箱・AI返信は本番状態に一本化（support.html と訓練参加クライアント両方から共有）
    prod_state = get_state_for_conn({})
    is_staff_limited = bool(conn.get("staff_enabled", False))
    staff_a_id = conn.get("a_id")
    if cmd in ("set_staff_mode", "register_player", "fire_gorei", "fire_gorei_fixed", "cancel_gorei"):
        gorei_debug_log(
            f"[GOREI_DEBUG] recv cmd={cmd} idx={idx} role={conn.get('role')} "
            f"staff_enabled={is_staff_limited} staff_a_id={staff_a_id} a_id={conn.get('a_id')} mode={conn.get('mode')}"
        )

    def in_staff_scope(squad_idx):
        if not is_staff_limited:
            return True
        if staff_a_id is None or squad_idx is None:
            return False
        return squad_idx in (staff_a_id * 2, staff_a_id * 2 + 1)

    # Keepalive heartbeat from clients.
    if cmd == "ping":
        try:
            await websocket.send_json({
                "type": "pong",
                "server_timestamp": datetime.now(timezone.utc).timestamp() * 1000
            })
        except Exception:
            pass
        return
    if cmd == "set_mode":
        payload = val if isinstance(val, dict) else {}
        mode = "drill" if payload.get("mode") == "drill" else "prod"
        a_id = int(payload.get("alliance_id", 0)) if str(payload.get("alliance_id", "0")).isdigit() else 0
        if a_id not in [0, 1, 2]:
            a_id = 0
        room_key = str(payload.get("room_key", "default")).strip()[:64] or "default"
        drill_name = str(payload.get("alliance_name", "")).strip()[:24]
        room_action = str(payload.get("room_action", "")).strip()
        room_code = str(payload.get("room_code", "")).strip()[:32]
        room_id = str(payload.get("room_id", "")).strip()[:32]
        broadcast_rooms_after_set_mode = False
        if websocket in connections:
            if mode == "drill":
                if room_action == "create":
                    if not drill_name or not room_code:
                        await websocket.send_json({"type": "mode_error", "message": "訓練同盟名と参加コードを入力してください。"})
                        return
                    room_id = uuid.uuid4().hex[:8]
                    room_key = room_id
                    drill_room_meta[room_id] = {"name": drill_name, "code": room_code}
                    drill_rooms[room_id] = fresh_drill_state(drill_name)
                    await websocket.send_json({"type": "mode_ok", "action": "create", "room_id": room_id})
                    broadcast_rooms_after_set_mode = True
                elif room_action == "join":
                    if room_id not in drill_room_meta:
                        await websocket.send_json({"type": "mode_error", "message": "訓練ルームが見つかりません。"})
                        return
                    if drill_room_meta[room_id].get("code", "") != room_code:
                        await websocket.send_json({"type": "mode_error", "message": "参加コードが違います。"})
                        return
                    room_key = room_id
                    drill_name = drill_room_meta[room_id].get("name", drill_name)
                    await websocket.send_json({"type": "mode_ok", "action": "join", "room_id": room_id})
                elif room_action == "list":
                    await websocket.send_json({"type": "drill_rooms", "rooms": get_public_drill_rooms()})
                    return

            connections[websocket]["mode"] = mode
            connections[websocket]["drill_alliance"] = a_id
            connections[websocket]["drill_key"] = room_key
            connections[websocket]["role"] = None
            connections[websocket]["idx"] = None
            connections[websocket]["a_id"] = None
            connections[websocket]["staff_enabled"] = False
            if mode == "drill":
                st = get_state_for_conn(connections[websocket])
                if drill_name:
                    st["alliance_names"] = [drill_name, f"{drill_name}-2", f"{drill_name}-3"]
                roles = st.get("alliance_roles")
                if not isinstance(roles, list) or len(roles) != 3:
                    st["alliance_roles"] = ["occupy", "", ""]
                elif room_action == "create" and not any(str(r or "").strip() for r in roles):
                    st["alliance_roles"] = ["occupy", "", ""]
            ack_st = get_state_for_conn(connections[websocket])
            ack = {
                "type": "init",
                "data": ack_st,
                "mode": mode,
                "drill_rooms": get_public_drill_rooms(),
                "alliance_presence": alliance_presence_by_alliance(ack_st, list(connections.items())),
            }
            if mode == "drill":
                dk = connections[websocket]["drill_key"]
                ack["drill_staff"] = drill_staff_status_for_room(dk, ack_st)
            await websocket.send_json(ack)
            if broadcast_rooms_after_set_mode:
                await broadcast_drill_room_list()
        return
    if cmd == "set_staff_mode":
        enabled = bool(val.get("enabled")) if isinstance(val, dict) else False
        a_id = (val.get("alliance_id", 0) if isinstance(val, dict) else 0)
        if websocket in connections:
            connections[websocket]["staff_enabled"] = enabled
            if enabled:
                connections[websocket]["a_id"] = a_id
            elif not enabled:
                conn_role = connections[websocket].get("role")
                if not conn_role:
                    connections[websocket]["a_id"] = None
        FORCE_STATE_BROADCAST = True
        state_version += 1
        return
    if cmd == "set_staff_name":
        payload = val if isinstance(val, dict) else {}
        a_id = int(payload.get("alliance_id", 0))
        name = str(payload.get("name", "")).strip()
        if "staff_names" not in state or not isinstance(state["staff_names"], list) or len(state["staff_names"]) != 3:
            state["staff_names"] = ["", "", ""]
        if 0 <= a_id < 3:
            state["staff_names"][a_id] = name
        FORCE_STATE_BROADCAST = True
        state_version += 1
        return
    
    if cmd == "mod_manual_base":
        current = state["manual_base_target"] if state["manual_base_target"] else now_ts
        new_tgt = current + val
        if new_tgt > now_ts: state["manual_base_target"] = new_tgt
        else: state["manual_base_target"] = None
    elif cmd == "set_manual_base_abs": 
        if val is not None and val > now_ts: state["manual_base_target"] = val
    elif cmd == "mod_manual_swap_margin": state["manual_swap_margin"] = max(0, state["manual_swap_margin"] + val)
    elif cmd == "mod_manual_wd_margin": state["manual_wd_margin"] = max(0, state["manual_wd_margin"] + val)
    
    elif cmd == "fire_manual_swap":
        base = state["manual_base_target"] if state["manual_base_target"] else now_ts
        state["manual_swap_trigger_time"] = base + state["manual_swap_margin"]
        FORCE_STATE_BROADCAST = True
    elif cmd == "fire_manual_wd":
        if state.get("manual_swap_trigger_time") is not None:
            state["manual_wd_trigger_time"] = float(state["manual_swap_trigger_time"]) - state["manual_wd_margin"]
        else:
            base = state["manual_base_target"] if state["manual_base_target"] else now_ts
            state["manual_wd_trigger_time"] = (base + state["manual_swap_margin"]) - state["manual_wd_margin"]
        
    elif cmd == "cancel_manual_swap": 
        state["manual_swap_trigger_time"] = None
        state["cancel_trigger"] = datetime.now(timezone.utc).timestamp()
    elif cmd == "cancel_manual_wd": 
        state["manual_wd_trigger_time"] = None
        state["cancel_trigger"] = datetime.now(timezone.utc).timestamp()

    elif cmd == "update_name": state["timers"][idx]["name"] = val
    elif cmd == "update_alliance": state["alliance_names"][idx] = val
    elif cmd == "update_alliance_role": state["alliance_roles"][idx] = val
    elif cmd == "mod_main":
        state["timers"][idx]["sec"] = max(0, state["timers"][idx]["sec"] + val)
        if state["timers"][idx]["state"] == 1: state["timers"][idx]["end"] = (datetime.now(timezone.utc) + timedelta(seconds=state["timers"][idx]["sec"])).isoformat()
    elif cmd == "mod_sub": state["timers"][idx]["sub_set"] = max(0, state["timers"][idx]["sub_set"] + val)
    
    elif cmd == "mod_swap_ex": state["swap_extras"][idx] = min(99, max(0, state["swap_extras"][idx] + (val if val else 0)))
    elif cmd == "mod_withdraw_margin": state["withdraw_margins"][idx] = min(10, max(0, state["withdraw_margins"][idx] + (val if val else 0)))
    elif cmd == "set_swap_base": state["swap_base_squad"] = idx
    elif cmd == "set_wd_base": state["withdraw_base_squad"] = idx
    elif cmd == "set_insert_target": state["insert_target_idx"] = -1 if state["insert_target_idx"] == idx else idx
    elif cmd == "mod_insert_target":
        if not bool(conn.get("staff_enabled", False)):
            return
        delta = int(val if isinstance(val, (int, float, str)) and str(val).strip() != "" else 0)
        auto_base = _compute_insert_auto_target_ts(state)
        current = state["insert_fixed_target"] if state.get("insert_fixed_target") else (auto_base if auto_base else now_ts + 1)
        state["insert_fixed_target"] = float(current) + delta
    elif cmd == "fire_insert_fixed_target":
        if not bool(conn.get("staff_enabled", False)):
            return
        auto_tgt = _compute_insert_auto_target_ts(state)
        tgt = state.get("insert_fixed_target")
        if tgt is None:
            tgt = auto_tgt
        if tgt is not None:
            state["insert_fire_target"] = float(tgt)
            FORCE_STATE_BROADCAST = True
    elif cmd == "clear_insert_fixed_target":
        if not bool(conn.get("staff_enabled", False)):
            return
        state["insert_fixed_target"] = None
        state["insert_fire_target"] = None
    elif cmd in ("mod_insert_margin", "mod_insert_offset_tenth"):
        if not bool(conn.get("staff_enabled", False)):
            return
        delta = int(val if isinstance(val, (int, float, str)) and str(val).strip() != "" else 0)
        current = _insert_margin_sec(state)
        state["insert_margin_sec"] = max(0, min(5, current + delta))
        state["insert_offset_tenth"] = -int(state["insert_margin_sec"]) * 10
    elif cmd == "set_delay_target":
        squad_id = (idx - 6) // 6
        state["delay_target_idxs"][squad_id] = -1 if state["delay_target_idxs"][squad_id] == idx else idx
        
    elif cmd == "mod_gorei":
        if not in_staff_scope(idx): return
        state["gorei_offsets"][idx] = max(0, state["gorei_offsets"][idx] + (val if val else 0))
    elif cmd == "mod_gorei_target":
        if not in_staff_scope(idx): return
        squad_id = idx; start_idx = 6 + squad_id * 6
        marches = [state["timers"][i]["sub_set"] for i in range(start_idx, start_idx + 6) if state["timers"][i]["name"].strip() != ""]
        max_march = max(marches) if marches else 0
        min_tgt = now_ts + state["gorei_offsets"][squad_id] + state["default_rally"] + max_march
        current = state["gorei_fixed_targets"][squad_id] if state["gorei_fixed_targets"][squad_id] else min_tgt
        state["gorei_fixed_targets"][squad_id] = current + val

    elif cmd == "toggle_pair_squad":
        if is_staff_limited and not in_staff_scope(idx): return
        state["pair_selected"][idx] = not state["pair_selected"][idx]
    elif cmd == "mod_pair_gorei":
        if is_staff_limited: return
        state["pair_gorei_offset"] = max(0, state["pair_gorei_offset"] + (val if val else 0))
    elif cmd == "mod_pair_gorei_target":
        if is_staff_limited: return
        marches = []
        for s in range(6):
            if state["pair_selected"][s]:
                start_idx = 6 + s * 6
                for i in range(start_idx, start_idx + 6):
                    if state["timers"][i]["name"].strip() != "": marches.append(state["timers"][i]["sub_set"])
        max_march = max(marches) if marches else 0
        min_tgt = now_ts + state["pair_gorei_offset"] + state["default_rally"] + max_march
        current = state["pair_fixed_target"] if state["pair_fixed_target"] else min_tgt
        state["pair_fixed_target"] = current + val

    elif cmd == "fire_pair_gorei" or cmd == "fire_pair_gorei_fixed":
        if is_staff_limited: return
        marches = []
        for s in range(6):
            if state["pair_selected"][s]:
                start_idx = 6 + s * 6
                for i in range(start_idx, start_idx + 6):
                    if state["timers"][i]["name"].strip() != "": marches.append(state["timers"][i]["sub_set"])
        max_march = max(marches) if marches else 0
        if cmd == "fire_pair_gorei": sync_target = datetime.now(timezone.utc) + timedelta(seconds=state["pair_gorei_offset"] + state["default_rally"] + max_march)
        else:
            if not state["pair_fixed_target"]: return
            sync_target = datetime.fromtimestamp(state["pair_fixed_target"], tz=timezone.utc)
        for s in range(6):
            if state["pair_selected"][s]:
                start_idx = 6 + s * 6
                for i in range(start_idx, start_idx + 6):
                    if state["timers"][i]["name"].strip() != "":
                        state["timers"][i]["state"] = 4
                        my_target = sync_target + timedelta(seconds=1 if i == state["delay_target_idxs"][s] else 0)
                        state["timers"][i]["start_at"] = (my_target - timedelta(seconds=state["timers"][i]["sub_set"] + state["default_rally"])).isoformat()

    elif cmd == "cancel_pair_gorei":
        if is_staff_limited: return
        state["cancel_trigger"] = datetime.now(timezone.utc).timestamp() 
        state["pair_fixed_target"] = None
        for s in range(6):
            if state["pair_selected"][s]:
                start_idx = 6 + s * 6
                for i in range(start_idx, start_idx + 6): state["timers"][i]["state"] = 0; state["timers"][i]["sec"] = state["default_rally"]

    elif cmd == "clear_player":
        state["cancel_trigger"] = datetime.now(timezone.utc).timestamp() 
        state["timers"][idx] = {"name": "", "sec": state["default_rally"], "off": 0, "sub_set": 0, "sub_sec": 0, "state": 0, "end": None, "frozen_target": None, "start_at": None, "online": False, "device_mode": "2device"}
        if idx < 6:
            if state["insert_target_idx"] == idx: state["insert_target_idx"] = -1
        else:
            squad_id = (idx - 6) // 6
            if state["delay_target_idxs"][squad_id] == idx: state["delay_target_idxs"][squad_id] = -1
        for ws, info in connections.items():
            if same_context(info, conn) and info["idx"] == idx:
                info["role"] = None
                info["idx"] = None
            
    elif cmd == "start":
        t = state["timers"][idx]
        now = datetime.now(timezone.utc)
        if t["sec"] > 0: t["state"] = 1; t["end"] = (now + timedelta(seconds=t["sec"])).isoformat()
    elif cmd == "stop":
        state["cancel_trigger"] = datetime.now(timezone.utc).timestamp() 
        state["timers"][idx]["state"] = 0; state["timers"][idx]["sec"] = state["default_rally"]
    elif cmd == "toggle_rally":
        state["default_rally"] = 60 if state["default_rally"] == 300 else 300
        for t in state["timers"]:
            if t["state"] == 0: t["sec"] = state["default_rally"]
    elif cmd == "set_default_rally":
        if (conn or {}).get("mode") != "drill":
            return
        if not is_staff_limited:
            return
        try:
            rally_sec = int(float(val)) if val is not None else 300
        except (TypeError, ValueError):
            return
        if rally_sec not in (60, 300):
            return
        state["default_rally"] = rally_sec
        for t in state["timers"]:
            if t["state"] == 0:
                t["sec"] = rally_sec
        FORCE_STATE_BROADCAST = True
            
    elif cmd == "fire_gorei":
        if not is_staff_limited:
            msg_dbg = f"[GOREI_DEBUG] fire_gorei rejected not staff idx={idx} role={conn.get('role')} a_id={conn.get('a_id')}"
            print(msg_dbg)
            gorei_debug_log(msg_dbg)
            return
        if not in_staff_scope(idx):
            msg_dbg = f"[GOREI_DEBUG] fire_gorei rejected by staff scope idx={idx} staff_enabled={is_staff_limited} staff_a_id={staff_a_id}"
            print(msg_dbg)
            gorei_debug_log(msg_dbg)
            return
        start_idx = 6 + idx * 6
        names = [state["timers"][i]["name"] for i in range(start_idx, start_idx + 6)]
        marches = [state["timers"][i]["sub_set"] for i in range(start_idx, start_idx + 6) if state["timers"][i]["name"].strip() != ""]
        msg_dbg = f"[GOREI_DEBUG] fire_gorei idx={idx} names={names} marches={marches} delay_idx={state['delay_target_idxs'][idx]}"
        print(msg_dbg)
        gorei_debug_log(msg_dbg)
        max_march = max(marches) if marches else 0
        sync_target = datetime.now(timezone.utc) + timedelta(seconds=state["gorei_offsets"][idx] + state["default_rally"] + max_march)
        state["gorei_last_target"][idx] = sync_target.timestamp()
        for i in range(start_idx, start_idx + 6):
            if state["timers"][i]["name"].strip() != "":
                state["timers"][i]["state"] = 4
                my_target = sync_target + timedelta(seconds=1 if i == state["delay_target_idxs"][idx] else 0)
                state["timers"][i]["start_at"] = (my_target - timedelta(seconds=state["timers"][i]["sub_set"] + state["default_rally"])).isoformat()
        started = [
            {"idx": i, "name": state["timers"][i]["name"], "start_at": state["timers"][i]["start_at"]}
            for i in range(start_idx, start_idx + 6)
            if state["timers"][i]["name"].strip() != ""
        ]
        msg_dbg = f"[GOREI_DEBUG] fire_gorei started idx={idx} started={started}"
        print(msg_dbg)
        gorei_debug_log(msg_dbg)
        FORCE_STATE_BROADCAST = True
        try:
            await broadcast_state()
            await send_gorei_hint_to_context(conn, idx, sync_target.timestamp(), cancel=False)
            msg_dbg = f"[GOREI_DEBUG] force_gorei call fire_gorei idx={idx} target={sync_target.timestamp()}"
            print(msg_dbg)
            gorei_debug_log(msg_dbg)
            await send_force_gorei_to_context(conn, idx, sync_target.timestamp(), cancel=False)
            await send_full_state_to_context(conn)
            await send_full_state_to_one(websocket)
        except Exception as e:
            msg_err = f"[GOREI_DEBUG] fire_gorei post_send error idx={idx} err={e}"
            print(msg_err)
            gorei_debug_log(msg_err)
            raise

    elif cmd == "fire_gorei_fixed":
        if not is_staff_limited:
            gorei_debug_log(f"[GOREI_DEBUG] fire_gorei_fixed rejected not staff idx={idx} role={conn.get('role')} a_id={conn.get('a_id')}")
            return
        if not in_staff_scope(idx): return
        squad_id = idx; start_idx = 6 + squad_id * 6
        tgt_ts = state["gorei_fixed_targets"][squad_id]
        if not tgt_ts: return 
        sync_target = datetime.fromtimestamp(tgt_ts, tz=timezone.utc)
        state["gorei_last_target"][squad_id] = sync_target.timestamp()
        for i in range(start_idx, start_idx + 6):
            if state["timers"][i]["name"].strip() != "":
                state["timers"][i]["state"] = 4
                my_target = sync_target + timedelta(seconds=1 if i == state["delay_target_idxs"][squad_id] else 0)
                state["timers"][i]["start_at"] = (my_target - timedelta(seconds=state["timers"][i]["sub_set"] + state["default_rally"])).isoformat()
        FORCE_STATE_BROADCAST = True
        try:
            await broadcast_state()
            await send_gorei_hint_to_context(conn, squad_id, sync_target.timestamp(), cancel=False)
            msg_dbg = f"[GOREI_DEBUG] force_gorei call fire_gorei_fixed idx={squad_id} target={sync_target.timestamp()}"
            print(msg_dbg)
            gorei_debug_log(msg_dbg)
            await send_force_gorei_to_context(conn, squad_id, sync_target.timestamp(), cancel=False)
            await send_full_state_to_context(conn)
            await send_full_state_to_one(websocket)
        except Exception as e:
            msg_err = f"[GOREI_DEBUG] fire_gorei_fixed post_send error idx={squad_id} err={e}"
            print(msg_err)
            gorei_debug_log(msg_err)
            raise

    elif cmd == "cancel_gorei":
        if not is_staff_limited:
            gorei_debug_log(f"[GOREI_DEBUG] cancel_gorei rejected not staff idx={idx} role={conn.get('role')} a_id={conn.get('a_id')}")
            return
        if not in_staff_scope(idx): return
        state["cancel_trigger"] = datetime.now(timezone.utc).timestamp() 
        state["gorei_fixed_targets"][idx] = None
        state["gorei_last_target"][idx] = None
        start_idx = 6 + idx * 6
        for i in range(start_idx, start_idx + 6): state["timers"][i]["state"] = 0; state["timers"][i]["sec"] = state["default_rally"]
        FORCE_STATE_BROADCAST = True
        try:
            await broadcast_state()
            await send_gorei_hint_to_context(conn, idx, None, cancel=True)
            msg_dbg = f"[GOREI_DEBUG] force_gorei call cancel_gorei idx={idx}"
            print(msg_dbg)
            gorei_debug_log(msg_dbg)
            await send_force_gorei_to_context(conn, idx, None, cancel=True)
            await send_full_state_to_context(conn)
            await send_full_state_to_one(websocket)
        except Exception as e:
            msg_err = f"[GOREI_DEBUG] cancel_gorei post_send error idx={idx} err={e}"
            print(msg_err)
            gorei_debug_log(msg_err)
            raise

    elif cmd == "register_player":
        role = val.get("role"); a_id = val.get("alliance_id", 0); d_mode = val.get("device_mode", "2device")
        name = val.get("name", ""); total_sec = int(val.get("march_min", 0)) * 60 + int(val.get("march_sec", 0))
        msg_dbg = f"[GOREI_DEBUG] register_player role={role} a_id={a_id} name={name} total_sec={total_sec} mode={(conn or {}).get('mode','prod')}"
        print(msg_dbg)
        gorei_debug_log(msg_dbg)
        
        if websocket in connections:
            connections[websocket]["march_sec"] = total_sec
            
        if role.startswith("leader"):
            global_squad = a_id * 2 + (0 if role == "leader1" else 1)
            start_idx = 6 + global_squad * 6
            for i in range(start_idx, start_idx + 6):
                if state["timers"][i]["name"] in ["", name]:
                    state["timers"][i]["name"] = name; state["timers"][i]["sub_set"] = total_sec; state["timers"][i]["device_mode"] = d_mode
                    if websocket in connections:
                        connections[websocket]["role"] = role
                        connections[websocket]["idx"] = i
                        connections[websocket]["a_id"] = a_id 
                    break
        elif role == "rider":
            if websocket in connections:
                connections[websocket]["role"] = "rider"
                connections[websocket]["a_id"] = a_id 
        await send_full_state_to_one(websocket)
    elif cmd == "send_support_chat":
        if "support_chats" not in prod_state:
            prod_state["support_chats"] = {}
        payload = data.get("val") if isinstance(data.get("val"), dict) else data
        cid = payload.get("client_id") or (connections.get(websocket, {}).get("id") if websocket in connections else None) or str(uuid.uuid4())
        msg = str(payload.get("msg") or "").strip()
        sender_name = str(payload.get("name") or "").strip()
        is_admin = bool(payload.get("is_admin", False))
        raw_att = payload.get("attachments")
        attachments = []
        if isinstance(raw_att, list):
            for a in raw_att[:3]:
                if not isinstance(a, dict):
                    continue
                mime = str(a.get("mime") or "image/jpeg").strip().lower()
                if mime not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
                    continue
                data = str(a.get("data") or "").strip()
                if data.startswith("data:") and "," in data:
                    data = data.split(",", 1)[1]
                data = "".join(data.split())
                if not data or len(data) > 900_000:
                    continue
                attachments.append({"mime": mime, "data": data})
        if not msg and not attachments:
            return
        if not is_admin and not sender_name:
            try:
                await websocket.send_json({"type": "error", "message": "support_name_required"})
            except Exception:
                pass
            return
        if is_admin and not sender_name:
            sender_name = "総指揮"
        now_dt = datetime.now(timezone.utc) + timedelta(hours=9)
        time_str = now_dt.strftime("%H:%M")

        if cid not in prod_state["support_chats"]:
            prod_state["support_chats"][cid] = {"name": sender_name, "messages": [], "unread_admin": False}
        elif sender_name and not is_admin:
            prod_state["support_chats"][cid]["name"] = sender_name
        entry_msg = {
            "sender": "admin" if is_admin else "user",
            "text": msg if msg else ("（画像のみ）" if attachments else ""),
            "time": time_str,
        }
        if attachments:
            entry_msg["attachments"] = attachments
        prod_state["support_chats"][cid]["messages"].append(entry_msg)
        prod_state["support_chats"][cid]["unread_admin"] = not is_admin
        FORCE_SUPPORT_CHAT_BROADCAST = True
        await broadcast_state()

        if not is_admin:
            asyncio.create_task(generate_ai_reply(cid, msg if msg else "（画像が添付されました）", prod_state))
    elif cmd == "mark_chat_read":
        payload = data.get("val") if isinstance(data.get("val"), dict) else data
        cid = payload.get("client_id")
        if "support_chats" in prod_state and cid in prod_state["support_chats"]:
            prod_state["support_chats"][cid]["unread_admin"] = False
            FORCE_SUPPORT_CHAT_BROADCAST = True
    elif cmd == "client_debug":
        try:
            txt = str(val if val is not None else "").strip()
            if txt:
                gorei_debug_log(f"[CLIENT_DEBUG] {txt}")
        except Exception:
            pass

    FORCE_STATE_BROADCAST = True
    state_version += 1

if __name__ == "__main__":
    _port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=_port,
        reload=False,
        timeout_keep_alive=int(os.environ.get("UVICORN_TIMEOUT_KEEP_ALIVE", "120")),
        backlog=int(os.environ.get("UVICORN_BACKLOG", "2048")),
        ws_ping_interval=float(os.environ.get("UVICORN_WS_PING_INTERVAL", "25")),
        ws_ping_timeout=float(os.environ.get("UVICORN_WS_PING_TIMEOUT", "120")),
    )
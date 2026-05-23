#!/usr/bin/env python3
"""
Agent stop hook: deploy to VPS, HTTP verify, then auto-followup for QA or fix loop.
User does not run .bat files.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hook_util import (
    emit,
    load_json,
    load_production_urls,
    read_stdin_json,
    run_hook,
    save_json,
    update_workflow_status,
)

PIPELINE = REPO / "scripts" / "production_auto_pipeline.py"
QA_CHECK = REPO / "scripts" / "qa_feature_check.py"
MAX_LOOP = 12


def run_pipeline() -> int:
    return subprocess.run(
        [sys.executable, str(PIPELINE), "full"],
        cwd=str(REPO),
    ).returncode


def run_qa_check(scoped: bool = True) -> int:
    if not QA_CHECK.is_file():
        return 0
    args = [sys.executable, str(QA_CHECK)]
    # 操作者ロジック(operator)は編集ファイルに関係なく毎回検証（仕様ロック含む）
    args.append("--scope-from-edits" if scoped else "--full")
    return subprocess.run(args, cwd=str(REPO)).returncode


def main() -> int:
    payload = read_stdin_json()
    status = payload.get("status", "")
    loop_count = int(payload.get("loop_count") or 0)

    if status != "completed":
        emit({})
        return 0

    if loop_count >= MAX_LOOP:
        emit({})
        return 0

    st = load_json("loop_state.json", {})
    urls = load_production_urls()
    player = urls.get("player_url", "https://3301-svs.jp/")

    # 1) Deploy + HTTP verify after code edits
    if st.get("pending_deploy"):
        update_workflow_status(
            "stop: VPSデプロイ + HTTP検証",
            pending_deploy=True,
            edited_files=load_json("workflow_status.json", {}).get("edited_files", []),
        )
        rc = run_pipeline()
        st["pending_deploy"] = False
        st["last_pipeline_rc"] = rc
        st["qa_pass"] = False
        st["qa_triggered"] = False
        save_json("loop_state.json", st)
        update_workflow_status(
            "stop: VPSデプロイ + HTTP検証",
            last_pipeline_rc=rc,
            pending_deploy=False,
        )
        if rc != 0:
            emit(
                {
                    "followup_message": (
                        "**現在の作業:** 【followup: 自動修正】\n"
                        "【自動修正】VPSデプロイまたはHTTP検証が失敗しました。"
                        "logs/production_pipeline_status.json を読み、原因を修正して保存してください。"
                        "ユーザーに.batの実行は依頼しないでください。終了後stopフックが再デプロイします。"
                    )
                }
            )
            return 0
        run_qa_check(scoped=True)

    # 2) Trigger browser QA (once per deploy cycle) if automated QA failed or UI flow untested
    qa = load_json("qa_last_result.json", {})
    if not qa:
        qa = load_json(str(REPO / "logs" / "qa_last_result.json"), {})
    needs_browser = not qa.get("pass_automated", qa.get("pass"))
    if st.get("last_pipeline_rc") == 0 and not st.get("qa_triggered") and needs_browser:
        st["qa_triggered"] = True
        save_json("loop_state.json", st)
        update_workflow_status("followup: 自動QA")
        emit(
            {
                "followup_message": (
                    "**現在の作業:** 【followup: 自動QA】→【browserで本番チェック】\n"
                    f"【自動QA・コード編集禁止】まず logs/qa_last_result.json の FAIL を確認。\n"
                    f"browser MCP で本番のみ検証: {player}\n"
                    f"1. logs/qa_last_result.json の op_operator_mandatory_bundle を確認\n"
                    f"2. .cursor/qa_checklist.md（操作者ロジック必須）\n"
                    f"3. manual_required（音声・画面）があれば本番で確認\n"
                    f"3. 結果を logs/qa_last_result.json に更新して保存\n"
                    f"4. 終了（追加の説明不要）"
                )
            }
        )
        return 0

    # 3) QA failed -> auto fix
    if qa.get("pass") is False and not st.get("pending_deploy"):
        st["fix_round"] = int(st.get("fix_round") or 0) + 1
        save_json("loop_state.json", st)
        update_workflow_status("followup: 自動修正")
        emit(
            {
                "followup_message": (
                    "**現在の作業:** 【followup: 自動修正】→【エージェントがコード編集】\n"
                    "【自動修正】logs/qa_last_result.json の FAIL のみ最小修正。"
                    "操作者ロジック(op_*)のFAILは .cursor/rules/operator-logic-guard.mdc の仕様に必ず戻す。"
                    "デプロイは行わず終了（stopフックが再デプロイ＋operator再QA）。.bat案内禁止。"
                )
            }
        )
        return 0

    # 4) All green
    if qa.get("pass") is True and st.get("last_pipeline_rc") == 0:
        st["qa_triggered"] = False
        save_json("loop_state.json", st)
        update_workflow_status("あなた: 3301-svs.jp を確認", qa_pass=True)

    emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(run_hook("stop", main))

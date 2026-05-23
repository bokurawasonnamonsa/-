#!/usr/bin/env python3
"""Parse QA subagent result and continue fix loop if needed."""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hook_util import emit, load_json, read_stdin_json, run_hook, save_json

QA_HINTS = re.compile(r"qa|品質|3301|production|checklist|browser|検証", re.I)


def infer_pass(summary: str, task: str) -> bool | None:
    text = f"{summary}\n{task}"
    if re.search(r"\bFAIL\b|失敗|NG\b|不合格", text, re.I):
        if re.search(r"\bPASS\b|成功|合格|すべてOK", text, re.I):
            return False
        return False
    if re.search(r"\bPASS\b|すべてOK|全項目OK|合格", text, re.I):
        return True
    return None


def main() -> int:
    payload = read_stdin_json()
    if payload.get("status") != "completed":
        emit({})
        return 0

    task = payload.get("task") or ""
    desc = payload.get("description") or ""
    summary = payload.get("summary") or ""
    blob = f"{task} {desc} {summary}"
    if not QA_HINTS.search(blob):
        emit({})
        return 0

    passed = infer_pass(summary, task)
    result = {
        "pass": passed if passed is not None else False,
        "summary": summary[:4000],
        "task": task[:500],
    }
    save_json("qa_last_result.json", result)
    log_path = REPO / "logs" / "qa_last_result.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    st = load_json("loop_state.json", {})
    st["qa_pass"] = bool(result["pass"])
    save_json("loop_state.json", st)

    if result["pass"] is False:
        emit(
            {
                "followup_message": (
                    "【自動修正】QAサブエージェントが不合格。"
                    "logs/qa_last_result.json の FAIL のみ修正。"
                    "op_* / op_operator_mandatory_bundle は .cursor/rules/operator-logic-guard.mdc に戻す。.bat案内禁止。"
                )
            }
        )
    else:
        emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(run_hook("subagentStop", main))

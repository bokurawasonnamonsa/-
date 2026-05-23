#!/usr/bin/env python3
"""Mark pending VPS deploy when agent edits app files."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hook_util import (
    emit,
    is_deployable_file,
    load_json,
    read_stdin_json,
    record_file_edit,
    run_hook,
    save_json,
)


def main() -> int:
    payload = read_stdin_json()
    fp = payload.get("file_path") or ""
    if fp:
        record_file_edit(fp)
    if is_deployable_file(fp):
        st = load_json("loop_state.json", {})
        st["pending_deploy"] = True
        st["qa_pass"] = False
        st["qa_triggered"] = False
        save_json("loop_state.json", st)
    emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(run_hook("afterFileEdit", main))

#!/usr/bin/env python3
"""Inject autonomous VPS production workflow context."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hook_util import emit, load_production_urls, read_stdin_json, run_hook


def main() -> int:
    read_stdin_json()
    urls = load_production_urls()
    ctx = f"""
【UTC 自動本番ループ — 常時有効】
- ユーザーは https://3301-svs.jp/ の確認のみ。 .bat のダブルクリックや手動デプロイを依頼しない。
- コード変更後の VPS 反映は stop フックが `python scripts/production_auto_pipeline.py` で自動実行。
- 本番URL: {urls.get('player_url', 'https://3301-svs.jp/')}  スタッフ: {urls.get('staff_url', '')}
- HTTP検証後、followup で【自動QA】が来たら browser MCP で .cursor/qa_checklist.md を実行し logs/qa_last_result.json を書く。
- 【自動修正】followup では FAIL のみ最小修正。修正後は保存して終了（デプロイはフック任せ）。

【作業フェーズ表示 — 毎返答必須】
.cursor/rules/workflow-status.mdc に従い、返答の先頭に **現在の作業:** 【フェーズ名】、末尾に ## 作業完了サマリー（自動保存・編集ファイル・次ステップ）を付ける。
フェーズ名はフロー図と同じ: あなた: Agentで修正依頼 / エージェントがコード編集 / afterFileEdit: デプロイ予約 / stop: VPSデプロイ + HTTP検証 / followup: 自動QA / browserで本番チェック / followup: 自動修正 / あなた: 3301-svs.jp を確認
自動保存状態は .cursor/hooks/state/workflow_status.json を読んで報告する。
"""
    emit({"additional_context": ctx.strip()})
    return 0


if __name__ == "__main__":
    raise SystemExit(run_hook("sessionStart", main))

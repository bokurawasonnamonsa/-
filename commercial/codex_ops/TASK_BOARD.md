# TactNode Labs Task Board

Last updated: 2026-06-11

## Doing

（なし — 次のタスク待ち）

## Workflow (確定: 2026-06-11)

- **Claude Code** → 設計・タスクファイル作成 (`cursor_tasks/*.md`)
- **Codex** → 実装・ビルド・Play Consoleリリース・完了通知 (`notify_claude.ps1`)
- **Cursor は使用しない。Cursor関連hook/watcherは再有効化しない。**

## Next: Command Clock Product Repair

- Rebuild the 3301-style synchronization flow in generic language.
- Make language selector obvious, likely as a bordered dropdown near the top.
- Verify floating overlay on Android emulator/device with screenshots.
- Ensure countdown does not start incorrectly before an instruction is issued.
- Make timer labels understandable without knowing 3301.
- Add/update emulator verification screenshots.

## Next: Team Connection Model

- Design no-server share code for early testing.
- Allow coordinator to create an operation code.
- Allow participant to paste/import the same target settings.
- Keep live rooms/server investment for a later paid phase.

## Next: Store / Testing

- Keep internal testing releases moving only after emulator/device verification.
- Maintain release notes in plain English.
- Prepare tester feedback form or simple feedback workflow.

## Next: Marketing / SNS

- Keep global SNS profiles prepared.
- Draft posts and assets, but wait for a useful app before major launch push.
- Prepare English-first content, then expand to high-priority languages.

## Done
- Task `20260611_label_input_free_text` (Label input: free text field) completed by Codex.
- Task `20260611_arrival_format_fix` (Arrival time format fix) completed by Codex.
- Task `20260611_arrival_time_display` (到着時刻表示) completed by Codex.
  - 0.1.17 (versionCode 18): 初回リリース
  - 0.1.18 (versionCode 19): フローティング4行目切れ修正 → 表示領域拡張。2026-06-11 15:09 内部テスト公開済み（未審査）
- Task `20260611_overlay_display_toggles` (Cursor Task: フローティング表示項目トグル) completed by Codex.

- Git for Windows installed on this machine.
- Shared agent instruction files added.
- Claude -> Cursor hook created.
- Cursor -> Codex watcher created.
- Codex -> Claude notification script created.
- Cursor workflow paused on 2026-06-11; operation moved to Claude Code + Codex direct workflow.
- Command Clock `0.1.7` internal test release published.
- Command Clock `0.1.8` internal test release `9 (0.1.8)` published.
- Command Clock `0.1.9` internal test release `10 (0.1.9)` published with multi-language support fix.
- Command Clock `0.1.10` internal test release `11 (0.1.10)` published with floating permission button disabled state.
- Command Clock `0.1.11` internal test release `12 (0.1.11)` published with language selector visual improvement.
- Command Clock `0.1.12` internal test release `13 (0.1.12)` published with floating overlay auto-on after permission grant.
- Command Clock `0.1.13` internal test release `14 (0.1.13)` published with Android 13+ overlay permission step-by-step guide.
- Command Clock `0.1.14` internal test release `15 (0.1.14)` published with simplified direct overlay permission flow.
- Command Clock `0.1.15` internal test release `16 (0.1.15)` published with overlay UTC duplicate fix and localized overlay text.
- Cursor workflow 完全停止 (2026-06-11): Claude Code + Codex直接連携フローへ移行確定。
- Command Clock `0.1.16` internal test release `17 (0.1.16)` published with floating overlay display toggles (UTC / phase / countdown Switch widgets).
- Command Clock `0.1.17` internal test release `18 (0.1.17)` published with arrival time display, then superseded by `0.1.18`.
- Command Clock `0.1.18` internal test release `19 (0.1.18)` published with arrival time display and larger floating overlay area.
- Command Clock `0.1.19` internal test release `20 (0.1.19)` published with simplified arrival display format.
- Command Clock `0.1.20` internal test release `21 (0.1.20)` published with the optional free-text note field.
- Realtime agent dashboard generator added at `automation/generate_dashboard.ps1`; `automation/dashboard.html` now regenerates from live task, release, and git state.
- Google Play listing draft v1 created at `commercial/store/play_listing_v1.md`.
- Codex -> Claude completion notifications sent for Floating Button Behavior Fix, Release 0.1.8 Prep, Release 0.1.8 Prep Retrigger, and Hook Test.
- Codex re-verified Floating Button Behavior Fix (2026-06-10): debug + signed AAB + emulator scenario A; Claude notified again.

# Claude Local Session Guide

Start here when Claude is used locally in this folder.

## Claudeの役割（ワークフロー上の位置づけ）

Claude Code は **設計・判断・レビュー** 担当。
- 実装はCursorに渡す。コードを大量に書き替えるのではなく、設計と指示書の作成に集中する。
- Cursorへの指示書は `commercial/codex_ops/cursor_tasks/YYYYMMDD_<タスク名>.md` に作成する。
- ワークフロー全体は `commercial/codex_ops/workflow_design.md` を参照。

## First Read

1. `AGENTS.md`
2. `commercial/codex_ops/TEAM_HANDOFF.md`
3. `commercial/codex_ops/TASK_BOARD.md`
4. `commercial/codex_ops/workflow_design.md`
5. For Android work: `commercial/apps/command_clock/android/BUILD_STATUS.md`
6. For 3301 feature migration: `commercial/product/command_clock_3301_feature_migration.md`

## How To Work

- Keep changes small and task-focused.
- Update `commercial/codex_ops/TASK_BOARD.md` when starting or finishing meaningful work.
- When a feature needs implementation, write a cursor_tasks/ instruction file instead of implementing directly.
- Do not touch production deployment scripts unless the task is explicitly about production.
- Do not commit secrets or private credentials.
- Use generic commercial wording. Avoid 3301, SVS, WOS, alliance names, or game-specific names in public product surfaces.

## Android Expectations

If changing Command Clock behavior:

1. Build debug.
2. Run on emulator or connected device.
3. Confirm the exact behavior visually.
4. Save screenshots for important timer, overlay, permission, or language changes.
5. Only then prepare release/AAB work.

## Git

Use:

`C:\Program Files\Git\cmd\git.exe`

Check status before editing. Do not reset, clean, or checkout away user work without explicit approval.


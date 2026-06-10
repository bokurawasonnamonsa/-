# TactNode Labs Agent Operating Guide

This repository is the shared workspace for TactNode Labs. Codex, Claude, Cursor, and any future agents must use this file as the first operating guide.

## Mission

Build a commercial, global strategy-game companion business starting with Command Clock for Android. Preserve the valuable coordination logic proven in the 3301 tool, but do not expose 3301-specific names, server details, alliance names, or game-specific terms in the commercial product.

## Current Product

- Product name: Command Clock
- Android package: `com.tactnodelabs.commandclock`
- Main app path: `commercial/apps/command_clock/android`
- Commercial dashboard: `commercial/dashboard.html`
- Business docs: `commercial/business`
- Product docs: `commercial/product`
- Store docs: `commercial/store`
- Social docs: `commercial/social`

## Non-Negotiables

1. Do not damage the existing 3301 production tool.
2. Do not overwrite or revert user changes unless the user explicitly asks.
3. Do not publish SNS posts, send support replies, or make store submissions without human confirmation unless the user has explicitly approved that exact action.
4. Do not commit secrets, passwords, keystores, tokens, Play Console credentials, or private server data.
5. Do not use 3301, WOS, SVS, alliance names, or specific game names in the commercial app UI or store copy.
6. For Android behavior, do not rely only on code inspection. Build and verify on an Android emulator or connected device when functionality matters.

## Verification Standard

For Command Clock Android changes:

- Build debug APK before emulator verification.
- Install and run on emulator or connected device.
- Visually confirm the changed behavior.
- Capture screenshots for UI, overlay, permission, or timer behavior.
- Build signed AAB only after emulator/device verification is acceptable.

Useful paths:

- AAB output: `commercial/apps/command_clock/android/app/build/outputs/bundle/release/app-release.aab`
- Debug APK output: `commercial/apps/command_clock/android/app/build/outputs/apk/debug/app-debug.apk`
- Build status: `commercial/apps/command_clock/android/BUILD_STATUS.md`

## Git Workflow

Git for Windows is expected at:

`C:\Program Files\Git\cmd\git.exe`

Before editing:

1. Check status.
2. Identify files relevant to the task.
3. Avoid unrelated cleanup.

For multi-agent work:

- Prefer one branch per agent/task when the current worktree is clean enough.
- If the worktree is dirty, coordinate in `commercial/codex_ops/TASK_BOARD.md` before large edits.
- Do not run destructive Git commands such as reset, checkout, or clean without explicit user approval.

## Agent Roles

- Executive/Codex: strategy, final judgment, user coordination, release flow.
- Engineering: Android app, web app, build, emulator/device verification.
- Product: feature design, 3301 feature migration into generic product language.
- Store: Google Play/App Store text, screenshots, release notes, policy checks.
- Marketing: SNS drafts, launch calendars, community research, posting assets.
- Support: FAQ, tester instructions, response drafts, complaint triage.
- Security: brand protection, code hardening, release signing, secret handling.
- Research/Finance: market sizing, competitor research, KPI and revenue plans.

## Current Near-Term Priority

Command Clock must become actually useful before broader promotion:

1. Restore the full coordination model from 3301 in generic language.
2. Make language selection obvious and polished.
3. Make floating overlay reliable and verified on emulator/device.
4. Add clear team sharing without server cost first.
5. Keep Google Play internal testing moving with verified builds.

## Codex Completion Notification

When Codex completes a task that was generated from `commercial/codex_ops/codex_ready/*_codex.md`, notify Claude so the multi-agent loop can continue:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\jarauser0\Desktop\utc_web\automation\notify_claude.ps1" -Message "TASK_NAME complete"
```

Use a concrete task name in the message, for example `0.1.8 build+upload complete`.

Preferred command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\jarauser0\Desktop\utc_web\automation\complete_codex_task.ps1" -TaskName "TASK_NAME" -Details "WHAT_CODEX_DID"
```

This writes `automation/codex_completion.log` and sends the Claude notification in one step.

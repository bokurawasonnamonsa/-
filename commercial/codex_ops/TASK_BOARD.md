# TactNode Labs Task Board

Last updated: 2026-06-10

## Doing

- Multi-agent workflow hardening:
  - Claude Code creates `commercial/codex_ops/cursor_tasks/*.md`
  - Claude hook opens Cursor for implementation
  - Cursor marks task `Status: Done`
  - watcher generates `commercial/codex_ops/codex_ready/*_codex.md`
  - watcher posts the Codex instruction into the open Codex window
  - Codex performs final verification/release work and notifies Claude with `automation/notify_claude.ps1`

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

- Git for Windows installed on this machine.
- Shared agent instruction files added.
- Claude -> Cursor hook created.
- Cursor -> Codex watcher created.
- Codex -> Claude notification script created.
- Command Clock `0.1.7` internal test release published.
- Command Clock `0.1.8` internal test release `9 (0.1.8)` published.
- Codex -> Claude completion notifications sent for Floating Button Behavior Fix, Release 0.1.8 Prep, Release 0.1.8 Prep Retrigger, and Hook Test.

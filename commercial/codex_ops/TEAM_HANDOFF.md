# TactNode Labs Team Handoff

Last updated: 2026-06-11

## Executive Context

The owner wants to grow this from a 3301-specific tool into a commercial, global app business. First revenue target is Android. iPhone comes later after Mac purchase or access. Current priority is not promotion volume; it is making Command Clock genuinely useful and trustworthy.

## Current App Status

- App: Command Clock
- Platform: Android first
- Distribution: Google Play internal testing
- Package: `com.tactnodelabs.commandclock`
- Current internal version after latest publish: `0.1.19`, version code `20`
- Main issue from owner: app still does not fully express the valuable 3301 coordination mechanism, and floating overlay reliability must be proven by emulator/device verification.

## Core Product Logic To Preserve

Generic wording only:

- Each participant has their own travel/setup duration.
- The coordinator knows the longest participant duration.
- A buffer time is added by default, usually 15 seconds but user-adjustable.
- The system calculates when each participant should press the in-game action so everyone arrives together.
- Countdown phases must be clear:
  - time until the participant should press the action
  - time until synchronized arrival
  - visible buffer, operation duration, own duration, longest duration
- Floating overlay must show the meaningful current phase while the main game is open.

## Active Work Areas

- Engineering: repair Command Clock UX and timer/overlay behavior.
- Product: convert 3301 flow into generic, sellable app language.
- Store: keep internal releases clean and documented.
- Marketing: prepare global positioning, but do not push hard until the app is useful.
- Support: prepare tester instructions and feedback triage.

## Current Agent Workflow

- Cursor is paused unless the owner explicitly asks to use it again.
- Claude Code and Codex should coordinate directly.
- Claude Code should handle implementation/design planning and can hand Codex a clear task file or direct instruction.
- Codex should handle verification, Android builds, Play Console internal test releases, release notes, task board updates, and Claude Code completion notifications.
- Codex should notify Claude Code after every completed task using `automation/notify_claude.ps1`.

## Human Approval Required

- SNS post publish button
- Store public production release
- Paid pricing or subscription enablement
- Anything involving passwords, Play Console account security, or payment profile changes

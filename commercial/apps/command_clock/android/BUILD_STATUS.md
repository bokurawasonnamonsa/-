# Build Status

## 2026-06-10

## Version 0.1.7 Work

Status:

- Debug build: Success
- Emulator verification: Success
- Release AAB build: Success
- Signed AAB: Success
- Google Play internal test release: Pending verification

Changed:

- Fixed floating overlay permission flow: the button no longer shows ON before permission is granted.
- Added Android 13+ restricted settings guidance message.
- Overlay service now stops cleanly when the overlay cannot be added.
- `refreshPermissionState` now clears `overlayEnabled` if permission was revoked.

Verified on emulator:

- With overlay permission denied, the app shows `FLOATING COUNTDOWN: OFF` and `ALLOW FLOATING DISPLAY`; it does not show ON.
- With overlay permission allowed, tapping `FLOATING COUNTDOWN: OFF` shows the floating countdown on the Android home screen.

Screenshots:

- `verify_017_overlay_permission_state.png`
- `verify_017_overlay_home.png`

Release notes draft:

```text
0.1.7 internal test

Fixed:
- Floating countdown button no longer shows ON before overlay permission is granted
- Added guidance for Android 13+ restricted settings when the overlay toggle is grayed out
- Floating service now stops cleanly if overlay cannot be displayed
```

## 2026-06-09

Command Clock commercial Android shell created.

## Version 0.1.5 Work

Status:

- Debug build: Success
- Emulator verification: Success
- Release AAB build: Success
- Signed AAB: Success

Changed:

- Rebuilt the app around the 3301-style synchronized arrival model.
- Added separate values for my setting time, longest member setting, buffer time, and flowing/rally time.
- Instruction countdown now uses: buffer + (longest member setting - my setting time).
- Arrival time now uses: instruction time + buffer + longest member setting + flowing/rally time.
- Added fixed labels above all input fields so prefilled values are understandable.
- Kept the language selector at the top and made it visibly framed.
- Fixed floating OFF so the overlay service stops instead of staying as a foreground service.
- Moved the initial floating display lower so it does not cover the language selector.

Verified on emulator:

- Initial screen shows framed language selector and labeled inputs.
- Default 60/60/15/300 instruction starts a 15-second press-start countdown.
- My 30 / longest 60 / buffer 15 instruction starts a 45-second press-start countdown.
- Floating display appears over the Android home screen and continues countdown outside the app.
- Floating OFF removes the overlay and stops `CommandOverlayService`.

Output:

```text
commercial/apps/command_clock/android/app/build/outputs/bundle/release/app-release.aab
```

## Version 0.1.3 Work

Status:

- Debug build: Success
- Release AAB build: Success
- Signed AAB: Success

Changed:

- Replaced language buttons with a top-screen language dropdown.
- Added no-server team share codes.
- Added operation fields for target minutes, prep seconds, and travel seconds.
- Start countdown now means action start time, calculated from target minus prep and travel.
- Floating display now uses operation/action countdown wording.
- Fixed floating countdown ownership so the overlay service updates the clock/countdown itself after the app goes behind another app.
- Changed the foreground service type from media playback to special use for a user-enabled floating countdown.

## Package

```text
com.tactnodelabs.commandclock
```

## Debug Build

Status:

- Success
- Rechecked after signing setup: Success

Command:

```text
BUILD_DEBUG.bat
```

Output:

```text
commercial/apps/command_clock/android/app/build/outputs/apk/debug/app-debug.apk
```

## Current App State

The debug shell includes:

- App name: Command Clock
- UTC time display
- Countdown to next hour
- Basic home screen
- In-app language switch: English, Japanese, Korean, Chinese, Thai, Indonesian, Spanish, Portuguese, French, German
- User-created countdown name
- Countdown minutes input
- Countdown preset buttons: 5m, 15m, 30m, 60m
- Saved countdown target using local preferences
- Team share code creation and import
- Floating timer ON/OFF
- Overlay permission button
- Draggable floating timer service
- Initial launcher icon

Not yet included:

- Voice alerts
- Templates
- Store listing screenshots

## Signing Setup

Prepared:

- `CREATE_UPLOAD_KEY.bat`
- `BUILD_SIGNED_AAB.bat`
- `SIGNING_README.md`

Generated:

- `app/build/outputs/bundle/release/app-release.aab`
- Signed internal test AAB: Success
- Google Play internal test release: Submitted by owner
- Google Play internal test install on Android device: Success
- Version `0.1.1` signed AAB: Success
- Google Play internal test release `0.1.1`: Published
- Version `0.1.2` signed AAB: Success
- Google Play internal test release `0.1.2`: Published

Signing rule:

- Use a separate Command Clock upload key.
- Keep passwords out of files and chat.
- Store keystore files under `commercial/secrets`.

## Next Technical Steps

1. Test `0.1.3` from Google Play on Android.
2. Add voice alerts.
3. Add template storage.
4. Add live team rooms after no-server code testing.
5. Prepare store listing screenshots.
6. Prepare tester feedback form and support flow.

## Next Internal Test Release

Version:

- `0.1.1`

AAB:

- `commercial/apps/command_clock/android/app/build/outputs/bundle/release/app-release.aab`

Release note draft:

```text
0.1.1 internal test

Added:
- In-app language switch between English and Japanese
- Improved countdown labels for global testing
```

Published:

- 2026-06-09
- Track: internal testing
- Release: `0.1.1 internal test`

## Next Internal Test Release

Version:

- `0.1.2`

Release note draft:

```text
0.1.2 internal test

Added:
- Expanded language switch to 10 languages
- Added 5m / 15m / 30m / 60m preset countdown buttons
- Added floating timer ON/OFF
- Added overlay permission shortcut
- Added draggable floating timer display

Changed:
- Renamed Start and Reset actions for clearer use
```

Published:

- 2026-06-09
- Track: internal testing
- Release: `3 (0.1.2)`

## Next Internal Test Release

Version:

- `0.1.3`

AAB:

- `commercial/apps/command_clock/android/app/build/outputs/bundle/release/app-release.aab`

Release note draft:

```text
0.1.3 internal test

Added:
- Language selector moved to a top-screen dropdown
- Team share code creation and import
- Operation timing with target time, prep seconds, and travel seconds
- Start action countdown calculated from target minus prep and travel

Fixed:
- Floating countdown now updates inside the overlay service after the app goes behind another app
- Foreground service type changed for the floating countdown use case
```

Built:

- 2026-06-09
- Version code: `4`
- Signed AAB: Success

Published:

- 2026-06-09
- Track: internal testing
- Release: `4 (0.1.3)`
- Published to internal testers at 13:25

## Version 0.1.4 Work

Status:

- Debug build: Success
- Emulator install: Success
- Release AAB build: Success
- Signed AAB: Success
- Google Play internal test release: Published

Changed:

- Preset buttons now only fill the target minutes field. They do not start the countdown.
- Countdown remains inactive as `--:--` until Start is tapped.
- Default prep seconds changed from 300 to 0 to avoid instant/zero countdowns.
- Start is blocked if prep seconds plus travel seconds are greater than or equal to target time.
- Language selector is labeled and visible near the top of the screen.
- Share-code copy no longer uses unclear "team" wording on the main screen.
- Floating display is confirmed working on the Android emulator home screen.

Verified on emulator:

- Fresh install opens with language selector visible.
- Fresh install shows no active countdown and `--:--`.
- Tapping `5M` does not start the countdown.
- Tapping `START` after `5M` starts a 5-minute countdown.
- Floating countdown appears over the launcher/home screen.
- Foreground overlay service is running.

Published:

- 2026-06-09
- Track: internal testing
- Release: `5 (0.1.4)`
- Published to internal testers at 13:53

## Version 0.1.7 Overlay Fix

Status:

- Debug build: Success
- Emulator verification: Success

Changed:

- Fixed overlay permission flow so `toggleOverlay()` no longer saves `overlayEnabled = true` before overlay permission is granted.
- `refreshPermissionState()` now resets stale ON state when permission is missing and refreshes the floating button label on resume.
- Added Android 13+ restricted-settings guidance in `openOverlayPermission()`.
- `CommandOverlayService.ensureOverlay()` now clears overlay state, notification, and service when `addView()` fails.

Verified on emulator:

- Scenario A: Tapping floating ON without permission opens settings; button stays `FLOATING COUNTDOWN: OFF` after returning without granting.
- Scenario B: After granting permission, floating ON shows overlay on the home screen.
- Scenario C: Floating OFF removes overlay and home-screen countdown.
- Scenario D: After `Issue instruction`, floating ON keeps arrival countdown on the home-screen overlay.

Screenshots:

```text
commercial/apps/command_clock/android/verify_017_overlay_a_after.png
commercial/apps/command_clock/android/verify_017_overlay_b_home.png
commercial/apps/command_clock/android/verify_017_overlay_c_home.png
commercial/apps/command_clock/android/verify_017_overlay_d_home.png
```

# Cursor Task: Multi-Language Support Fix

**Status:** Done
**Date:** 2026-06-10

## Goal

Command Clock currently claims broad language support, but several languages still fall back to English because `msg(String en, String ja)` only supports English and Japanese.

Fix language switching so all supported languages show localized labels in the app UI.

## Scope

File:

`commercial/apps/command_clock/android/app/src/main/java/com/tactnodelabs/commandclock/MainActivity.java`

Do not change unrelated product behavior.

## Required Languages

Support these language codes:

- `en`: English
- `ja`: Japanese
- `ko`: Korean
- `zh`: Chinese
- `th`: Thai
- `id`: Indonesian
- `es`: Spanish
- `pt`: Portuguese
- `fr`: French
- `de`: German

## Required Work

1. Replace the current 2-language `msg(String en, String ja)` helper with a 10-language helper:

```java
private String msg(String en, String ja, String ko, String zh,
                   String th, String id, String es, String pt,
                   String fr, String de) {
    switch (language) {
        case "ja": return ja;
        case "ko": return ko;
        case "zh": return zh;
        case "th": return th;
        case "id": return id;
        case "es": return es;
        case "pt": return pt;
        case "fr": return fr;
        case "de": return de;
        default:   return en;
    }
}
```

2. Update every `msg(...)` call so each visible UI string has translations for all 10 languages.

3. Make the language selector obvious and easy to find:

- Put it near the top of the screen.
- Use a bordered container or dropdown-like presentation.
- Display human-readable language names, not only short codes.

4. Verify important labels switch language correctly:

- Language
- Operation name
- My setting time
- Longest member setting
- Buffer after instruction
- Flowing time
- Issue instruction
- Clear
- Share code
- Create share code
- Paste share code
- Import shared instruction
- Floating countdown ON/OFF
- Allow floating display
- Waiting for instruction
- Press game Start in
- Arrival in
- UTC

5. Keep generic commercial wording.

Do not use:

- 3301
- WOS
- SVS
- specific game names
- alliance names

## Verification

Run:

```powershell
cd commercial/apps/command_clock/android
cmd /c BUILD_DEBUG.bat
```

If possible, install/run on emulator and capture screenshots for at least:

- English
- Japanese
- Korean or Chinese
- Spanish or Portuguese

## Completion

When complete:

- Update this file to `**Status:** Done`
- Add a short `## Cursor Result` section with build result and changed files.

## Cursor Result

- Debug build: Success
- Emulator verification: Success (English, Japanese, Korean, Spanish screenshots captured)
- Changed files:
  - `commercial/apps/command_clock/android/app/src/main/java/com/tactnodelabs/commandclock/MainActivity.java`
  - `commercial/apps/command_clock/android/BUILD_STATUS.md`

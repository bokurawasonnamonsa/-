# Cursor Task: フローティング表示項目トグル

**Status:** Done
**Date:** 2026-06-11

## 目的

フローティングオーバーレイに表示する項目をユーザーが選択できるようにする。
Androidの設定画面風のON/OFFスイッチ（`Switch`ウィジェット）で切り替え可能にする。

## 実装対象ファイル

- `commercial/apps/command_clock/android/app/src/main/java/com/tactnodelabs/commandclock/MainActivity.java`
- `commercial/apps/command_clock/android/app/src/main/java/com/tactnodelabs/commandclock/CommandOverlayService.java`

## 変更内容

### 1. SharedPreferences キー追加 (両ファイル共通)

```java
private static final String KEY_SHOW_UTC       = "show_utc";
private static final String KEY_SHOW_PHASE     = "show_phase";
private static final String KEY_SHOW_COUNTDOWN = "show_countdown";
```

デフォルト値はすべて `true`。

---

### 2. MainActivity — フローティング表示設定セクションを追加

既存の overlayButton / permissionButton の下に「フローティング表示設定」セクションを追加する。

#### レイアウト構成（コードで動的生成）

```
─────────────────────────────────────
  フローティング表示設定       ← セクションラベル（既存スタイルに合わせる）
─────────────────────────────────────
  UTC時刻          [Switch ON/OFF]
  フェーズ          [Switch ON/OFF]
  カウントダウン    [Switch ON/OFF]
```

各行は `LinearLayout (horizontal)` で `TextView` + `Switch` の構成。
`Switch` の色は既存の青テーマ (`0xFF58A6FF`) に合わせる。

#### Switch の初期化

```java
SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
switchUtc.setChecked(prefs.getBoolean(KEY_SHOW_UTC, true));
switchPhase.setChecked(prefs.getBoolean(KEY_SHOW_PHASE, true));
switchCountdown.setChecked(prefs.getBoolean(KEY_SHOW_COUNTDOWN, true));
```

#### Switch のリスナー

変更時に SharedPreferences に保存し、オーバーレイサービスが起動中であれば即時反映する。

```java
switchUtc.setOnCheckedChangeListener((btn, checked) -> {
    prefs.edit().putBoolean(KEY_SHOW_UTC, checked).apply();
    if (overlayEnabled) startOverlayService(CommandOverlayService.ACTION_SHOW, null);
});
// switchPhase, switchCountdown も同様
```

#### ラベルの多言語対応

セクションラベルと各行のラベルも `msg()` で10言語対応する。

| キー | en | ja |
|---|---|---|
| Floating display settings | Floating display settings | フローティング表示設定 |
| UTC time | UTC time | UTC時刻 |
| Phase | Phase | フェーズ |
| Countdown | Countdown | カウントダウン |

---

### 3. CommandOverlayService — buildClockText() を修正

各設定を読み取り、ONの行のみ結合して返す。

```java
private String buildClockText() {
    SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
    boolean showUtc       = prefs.getBoolean(KEY_SHOW_UTC, true);
    boolean showPhase     = prefs.getBoolean(KEY_SHOW_PHASE, true);
    boolean showCountdown = prefs.getBoolean(KEY_SHOW_COUNTDOWN, true);
    String lang = prefs.getString(KEY_LANGUAGE, "en");

    // UTC行
    String utcLine = "UTC " + DateTimeFormatter.ofPattern("HH:mm:ss")
            .withZone(ZoneOffset.UTC).format(Instant.now());

    // フェーズ行・カウントダウン行（既存ロジックを流用）
    // ...（既存のinstructionEpoch計算ロジックをそのまま使う）

    List<String> lines = new ArrayList<>();
    if (showUtc)       lines.add(utcLine);
    if (showPhase)     lines.add(phaseLine);   // 例: "待機中…" or "開始: label"
    if (showCountdown) lines.add(countdownLine); // 例: "05:30" or "--:--"

    if (lines.isEmpty()) return utcLine; // 全OFF時は最低限UTCを表示
    return String.join("\n", lines);
}
```

全てOFFの場合は最低限 `utcLine` を表示する（空白オーバーレイ防止）。

---

### 4. build.gradle — バージョン更新

```
versionCode 17
versionName "0.1.16"
```

---

## 完了の定義

- [ ] MainActivity にON/OFFスイッチが3つ表示される
- [ ] スイッチのON/OFFがSharedPreferencesに保存される
- [ ] フローティング表示がスイッチの状態に即時反映される
- [ ] 全OFFでも最低限UTCが表示される（空白にならない）
- [ ] 言語切り替え時にスイッチのラベルも更新される
- [ ] versionCode 17 / versionName "0.1.16" に更新済み

## 注意

- 既存の overlayButton / permissionButton のレイアウトスタイルに合わせること
- Switch の thumb/track カラーは青テーマ (`#58A6FF`) を使う
- commercial/secrets/ は触らない

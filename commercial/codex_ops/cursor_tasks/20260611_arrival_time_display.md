# Cursor Task: 到着時刻表示

**Status:** Done
**Date:** 2026-06-11

## 目的

ユーザーが設定している時間（バッファ + 最長所要時間 + 作戦時間）を元に、
何時に到着するかをUTC時刻で常に表示する。

- **メイン画面**: 設定フォームの下に到着予定時刻ラベルを追加
- **フローティングオーバーレイ**: 到着時刻行を追加（トグルON/OFFで制御）

## 実装対象ファイル

- `commercial/apps/command_clock/android/app/src/main/java/com/tactnodelabs/commandclock/MainActivity.java`
- `commercial/apps/command_clock/android/app/src/main/java/com/tactnodelabs/commandclock/CommandOverlayService.java`

---

## 変更内容

### 1. 到着時刻の計算ロジック

#### 指示発令中（instructionEpochSeconds > 0）のとき
```
到着時刻 = instructionEpochSeconds + bufferSeconds + longestSeconds + flowSeconds
```
→ 既存の `arrivalEpochSeconds()` をそのまま使う。

#### 未発令時（instructionEpochSeconds == 0）のとき
```
到着時刻 = Instant.now().getEpochSecond() + bufferSeconds + longestSeconds + flowSeconds
```
→ 「今すぐ開始した場合の到着時刻プレビュー」

---

### 2. MainActivity — 到着時刻ラベルの追加

#### SharedPreferences キー追加
```java
private static final String KEY_SHOW_ARRIVAL = "show_arrival";
```
デフォルト値: `true`

#### UI要素
既存のフローティング表示設定セクション（switchUtc / switchPhase / switchCountdown）の下に追加：

```
─────────────────────────────────────
  到着時刻          [Switch ON/OFF]
─────────────────────────────────────
```

```java
// 到着時刻スイッチ
switchArrival.setChecked(prefs.getBoolean(KEY_SHOW_ARRIVAL, true));
switchArrival.setOnCheckedChangeListener((btn, checked) -> updateOverlayDisplaySetting(KEY_SHOW_ARRIVAL, checked));
```

#### 到着時刻プレビューテキスト

設定フォームの下（Startボタンの上付近）に TextView を追加する。
毎秒更新ハンドラ（既存の `handler.postDelayed` ループ）の中で更新する。

```java
private TextView arrivalPreviewLabel;

// updateTimerDisplay() 内に追加
private void updateArrivalPreview() {
    long base = (instructionEpochSeconds > 0)
        ? instructionEpochSeconds
        : Instant.now().getEpochSecond();
    long arrivalEpoch = base + bufferSeconds + longestSeconds + flowSeconds;
    String arrivalStr = DateTimeFormatter.ofPattern("HH:mm 'UTC'")
        .withZone(ZoneOffset.UTC)
        .format(Instant.ofEpochSecond(arrivalEpoch));
    arrivalPreviewLabel.setText(msg("Arrival") + ": " + arrivalStr);
}
```

スタイル: 白文字、fontSize 14sp、既存の `fieldLabel()` テキストカラーに合わせる。

---

### 3. CommandOverlayService — 到着時刻行を追加

`buildClockText()` に到着時刻行を追加する。

```java
private static final String KEY_SHOW_ARRIVAL = "show_arrival";
```

```java
// buildClockText() 内
boolean showArrival = prefs.getBoolean(KEY_SHOW_ARRIVAL, true);

long base = (instructionEpoch > 0)
    ? instructionEpoch
    : Instant.now().getEpochSecond();
long arrivalEpoch = base + bufferSecs + longestSecs + flowSecs;
String arrivalLine = msg("Arrival", lang) + ": "
    + DateTimeFormatter.ofPattern("HH:mm 'UTC'")
        .withZone(ZoneOffset.UTC)
        .format(Instant.ofEpochSecond(arrivalEpoch));

if (showArrival) lines.add(arrivalLine);
```

全OFFでも最低限UTCを表示するガード（既存）はそのまま維持する。

---

### 4. 多言語ラベル `msg("Arrival")` の追加

| lang | テキスト |
|------|---------|
| en   | Arrival |
| ja   | 到着時刻 |
| zh   | 到达时间 |
| ko   | 도착 시간 |
| fr   | Arrivée |
| de   | Ankunft |
| es   | Llegada |
| pt   | Chegada |
| ru   | Прибытие |
| ar   | وقت الوصول |

フローティング表示設定セクションのスイッチラベルも同様に多言語対応する。

---

### 5. build.gradle — バージョン更新

```
versionCode 18
versionName "0.1.17"
```

---

## 完了の定義

- [ ] メイン画面に「到着時刻: HH:mm UTC」が表示される（未発令時はプレビュー）
- [ ] 指示発令中は実際の到着予定時刻に切り替わる
- [ ] フローティングオーバーレイに到着時刻行が表示される
- [ ] フローティング表示設定に「到着時刻」スイッチが追加される
- [ ] 全10言語でラベルが正しく表示される
- [ ] versionCode 18 / versionName "0.1.17" に更新済み

## 注意

- 既存の `arrivalEpochSeconds()` メソッドを流用すること
- 到着時刻は HH:mm UTC 形式（秒は不要）
- commercial/secrets/ は触らない

# Arrival time format fix

**Status:** Done
**Date:** 2026-06-11

## 変更内容

到着時刻の表示フォーマットと表示ラベルを修正する。

### 対象箇所

- `MainActivity.java` — `updateArrivalPreview()` 内の表示文字列
- `CommandOverlayService.java` — `buildClockText()` 内の到着行

### 変更前
```
到着時刻: HH:mm UTC
Arrival: HH:mm UTC
```

### 変更後
```
到着 HH:mm:ss
Arrival HH:mm:ss
```

- フォーマット: `HH:mm:ss`（秒あり、UTCサフィックスなし）
- ラベル: `msg("Arrival")` の各言語を以下に統一

| lang | テキスト |
|------|---------|
| en   | Arrival |
| ja   | 到着 |
| zh   | 到达 |
| ko   | 도착 |
| fr   | Arrivée |
| de   | Ankunft |
| es   | Llegada |
| pt   | Chegada |
| ru   | Прибытие |
| ar   | وصول |

ラベルと時刻の間はスペース1つのみ（コロンなし）。

例: `到着 15:42:08`

### build.gradle
```
versionCode 20
versionName "0.1.19"
```

## 完了の定義

- [ ] メイン画面の到着表示が `到着 HH:mm:ss` 形式になっている
- [ ] フローティングオーバーレイも同じ形式
- [ ] versionCode 20 / versionName "0.1.19" に更新済み
- [ ] 内部テスト公開済み

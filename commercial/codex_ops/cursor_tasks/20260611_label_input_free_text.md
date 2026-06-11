# Label input: free text field

**Status:** Done
**Date:** 2026-06-11

## 変更内容

「作戦名」ラベルとプレースホルダーを汎用的な自由記載フィールドに変更する。
事前入力なし・空欄スタート。

## 対象ファイル

`MainActivity.java` — `applyLanguage()` 内の2行

### 変更前

```java
labelInputLabel.setText(msg("Operation name", "作戦名", "작전 이름", "任务名称", "ชื่อปฏิบัติการ", "Nama operasi", "Nombre de operación", "Nome da operação", "Nom de l'opération", "Einsatzname"));
labelInput.setHint(msg("Operation name", "作戦名", "작전 이름", "任务名称", "ชื่อปฏิบัติการ", "Nama operasi", "Nombre de operación", "Nome da operação", "Nom de l'opération", "Einsatzname"));
```

### 変更後

```java
labelInputLabel.setText(msg("Note", "メモ", "메모", "备注", "บันทึก", "Catatan", "Nota", "Nota", "Note", "Notiz"));
labelInput.setHint(msg("Free text", "自由記載", "자유 입력", "自由填写", "ข้อความอิสระ", "Teks bebas", "Texto libre", "Texto livre", "Texte libre", "Freitext"));
```

- ラベル: `作戦名` → `メモ`（各言語: Note / 메모 / 备注 等）
- プレースホルダー: `作戦名` → `自由記載`（各言語: Free text 等）
- `labelInput` の初期値は空欄のまま（setText しない）

## build.gradle

```
versionCode 21
versionName "0.1.20"
```

## 完了の定義

- [ ] ラベルが「メモ」（ja）/ "Note"（en）になっている
- [ ] プレースホルダーが「自由記載」（ja）/ "Free text"（en）になっている
- [ ] フィールドは空欄でスタート
- [ ] versionCode 21 / versionName "0.1.20" に更新済み
- [ ] 内部テスト公開済み

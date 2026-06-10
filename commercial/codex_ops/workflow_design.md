# TactNode Labs — Claude→Cursor→Codex ワークフロー設計書

Last updated: 2026-06-10

---

## 概要

一人で複数アプリを展開するアプリスタジオとして、3つのAIツールを役割分担して使う。
設計→実装→仕上げ の流れを毎回同じ手順で回すことで、再現性ある開発体制を作る。

---

## 役割分担

| ツール | 役割 | 何をする場所か |
|--------|------|----------------|
| **Claude（Claude Code）** | 設計・判断・レビュー | ローカルフォルダを直接見て、要件定義・設計方針・タスク分解・コードレビューを行う |
| **Cursor** | 実装 | IDE上でClaudeが作った設計書を読み、コードを書く・直す |
| **Codex** | 自動化・仕上げ・量産 | SNS文案、ストア文言、競合調査、バッチ修正、定例タスクをこなす |

---

## 1フィーチャーあたりの標準フロー

```
[人間] 何を作りたいか・何を直したいかを決める
         ↓
[Claude Code] 設計フェーズ
  - 要件を整理する
  - 影響するファイルを特定する
  - 設計方針を決める（どう実装するか）
  - Cursor向けの実装指示書を書く → commercial/codex_ops/cursor_tasks/ に保存
  - TASK_BOARD.md を更新する
         ↓
[Cursor] 実装フェーズ
  - cursor_tasks/ の指示書を読む
  - AGENTS.md と CLAUDE.md のルールに従う
  - コードを実装する
  - ビルド・動作確認する
  - 完了したら cursor_tasks/ の指示書に「Done」を記録する
         ↓
[Claude Code] レビューフェーズ
  - 実装内容を確認する
  - ルール違反（3301名称の混入など）がないか確認する
  - 問題があればCursorへ差し戻し指示を書く
  - 問題なければ「Review OK」を記録し、Codexフェーズへ
         ↓
[Codex] 仕上げフェーズ（必要な場合のみ）
  - ストア文言・リリースノートの更新
  - SNS投稿案の作成
  - テスター向け案内文の更新
  - 翻訳・多言語対応
         ↓
[人間] 最終確認・承認・公開
```

---

## Cursor向け実装指示書のフォーマット

`commercial/codex_ops/cursor_tasks/` 以下に、1タスク1ファイルで作成する。
ファイル名: `YYYYMMDD_<タスク名>.md`

```markdown
# Cursor Task: <タスク名>

作成日: YYYY-MM-DD
ステータス: Pending / In Progress / Done / Cancelled

## 目的
何のためにこの変更をするか（1〜2行）

## 対象ファイル
- `パス/ファイル名.kt` — 変更内容の概要
- `パス/ファイル名.xml` — 変更内容の概要

## 実装指示
1. ○○する
2. ○○する
3. ○○する

## 制約・注意事項
- 3301/WOS/SVS/アライアンス名をコードや文字列に入れない
- ゲーム専用の変数名を市販アプリに持ち込まない
- Androidの場合、変更後にデバッグビルドして動作確認すること

## 完了の定義
- [ ] ビルドが通る
- [ ] エミュレーターまたは実機で動作確認済み
- [ ] レビュー用スクリーンショットを保存した（UI変更の場合）

## 参照資料
- `AGENTS.md`
- `commercial/codex_ops/TEAM_HANDOFF.md`
- （その他必要なドキュメント）
```

---

## Codex向け依頼フォーマット

Codexに渡す時は以下を冒頭に書く。

```
あなたはTactNode Labsの[部門名] Agentです。
まず commercial/codex_ops/TEAM_HANDOFF.md と AGENTS.md を読んでください。
今回の依頼: [作業内容]
制約: [3301/WOS名称禁止など]
成果物: [何を作るか・どこに保存するか]
```

部門別のプロンプト雛形は `commercial/codex_ops/department_prompts.md` を参照。

---

## ファイル構成ルール

```
commercial/
  codex_ops/
    workflow_design.md       ← このファイル（ワークフロー設計書）
    TASK_BOARD.md            ← 進行中タスクの一覧
    TEAM_HANDOFF.md          ← 現状のコンテキスト引き継ぎ
    agent_org.md             ← エージェント組織図
    codex_runbook.md         ← Codexへの定例依頼リスト
    department_prompts.md    ← 部門エージェント用プロンプト
    cursor_tasks/            ← Cursor向け実装指示書（1タスク1ファイル）
      YYYYMMDD_<タスク名>.md
```

---

## ブランチ戦略

| 状況 | ブランチ運用 |
|------|------------|
| 小さな修正（1ファイル以内） | `master` に直接コミット |
| 機能追加・複数ファイル変更 | `feature/<タスク名>` ブランチを切る |
| 大きなリファクタ | `refactor/<タスク名>` ブランチを切る |
| 緊急修正 | `hotfix/<内容>` ブランチを切る |

- Cursorが実装したコードは必ず人間かClaudeがレビューしてからマージ
- 3301専用版（`main.py`周辺）と市販版（`commercial/apps/`）は絶対に混ぜない

---

## コミットメッセージ規則

```
<種別>: <内容（英語または日本語）>

feat:     新機能追加
fix:      バグ修正
refactor: リファクタリング
docs:     ドキュメント更新
chore:    ビルド・設定変更
```

例:
```
feat: Add language selector dropdown to Command Clock main screen
fix: Fix floating overlay not showing during countdown phase
docs: Update TASK_BOARD with overlay verification task
```

---

## 判断フロー — どのツールに頼むか

```
何かをやりたい
    │
    ├─ 「何を作るか・どう設計するか」が決まっていない
    │       → Claude Code に相談する
    │
    ├─ 設計は決まっている。コードを書く・直す
    │       → Cursor に cursor_tasks/ の指示書を渡す
    │
    ├─ コードは完成。文章・翻訳・SNS・ストア文言が必要
    │       → Codex に department_prompts.md のプロンプトを使って依頼する
    │
    └─ どれでもない（リリース・課金・SNS公開）
            → 人間が判断・実行する
```

---

## よくあるミスと防止策

| ミス | 防止策 |
|------|--------|
| 3301/WOS名称が市販アプリに混入 | Cursor Rulesに禁止ワードを明記済み |
| 3301本番ツールを壊す | `main.py`周辺は明示的な指示なく触らない |
| 秘密情報をコミット | `.gitignore` で `.env`, `*.jks`, `keystore.properties` を除外済み |
| 設計なしにCursorで実装が進む | `cursor_tasks/`の指示書なしにCursorを動かさない |
| レビューなしに公開 | 人間確認必須リストを `AGENTS.md` に明記済み |

# 本番 QA チェックリスト（操作者目線）



対象: `https://3301-svs.jp/`



## 修正項目の実画面ループ（依頼あり時・必須）

- [ ] `python scripts/qa_drill_browser.py` または browser MCP で本番を実操作
- [ ] 依頼どおりの画面・DOM・スクリーンショットで PASS（不合格なら修正→再デプロイ→再実行）
- [ ] UI: `#alliancePresenceLine` に 参謀/集結主/乗り手（同盟名直下・訓練・SVS共通）



## 自動実行（デプロイ後はフックが毎回実行）



```bash

python scripts/qa_feature_check.py --full

python scripts/qa_feature_check.py --scope-from-edits

python scripts/qa_drill_loop.py

```



**訓練ルーム E2E（実WS・毎回）:** 参謀がルーム作成 → 別接続が一覧に見える → 参加コードで join  

| ID | 内容 |
|----|------|
| `ws_drill_list_creator` | 作成直後の一覧に自ルーム名がある |
| `ws_drill_list_joiner` | 参加側の一覧に同じルーム名がある |
| `ws_drill_join` | join が mode_ok |

`production_auto_pipeline.py full` の verify でも上記を実行する。



**毎回必須:** `operator` スコープ（差込・入替・集結・占領抜き — 他ファイル未編集でも監視）  

**合否:** `op_operator_mandatory_bundle` が ok のときのみ合格  

**仕様:** `.cursor/rules/operator-logic-guard.mdc`



## 操作者目線ロジック — 毎回必須（変更されていないか含む）

**毎ターン、コード編集の有無に関係なく実行。** 合否は `op_operator_mandatory_bundle` のみ。

| 層 | 何を見るか | 自動ID |
|----|------------|--------|
| **仕様ロック** | ソースに固定パターンが残っているか（無断変更検知） | `op_spec_ins_*` `op_spec_swap_*` `op_spec_gorei_*` `op_spec_wd_*` `op_spec_main_*` |
| **ロジック再現** | 操作者目線の時刻・CD・並行動作が仕様どおりか | `op_ins_*` `op_swap_*` `op_gorei_*` `op_wd_*` |
| **本番WS** | 号令がサーバ状態に反映されるか | `op_ws_*` |
| **管理画面** | 差込号令が staff_mode 付きで送れるか | `op_admin_insert_send_staff` |

```bash
python scripts/operator_spec_guard.py   # 仕様ロックのみ
python scripts/qa_feature_check.py --full   # 上記すべて + HTTP/WS
```

仕様書: `.cursor/rules/operator-logic-guard.mdc`

## 操作者ロジック — 毎回確認



| 機能 | 自動ID（例） | 手動 |

|------|-------------|------|

| **差込**（利用: 占領同盟のみ） | `op_ins_swap_like_start`, `op_ins_immediate_cd_to_landing`, `op_spec_ins_*` | `manual_op_ins_screen` |

| **占領入替** | `op_swap_*`, `op_spec_swap_*`, `op_ws_manual_swap` | `manual_op_swap_screen` |

| **集結号令** | `op_gorei_*`, `op_spec_gorei_*`, `op_ws_gorei_*` | `manual_op_gorei_screen` |

| **占領抜き** | `op_wd_*`, `op_spec_wd_*`, `op_ws_wd_vs_swap` | `manual_op_wd_screen` |



### 占領抜き（要約）



| 区分 | 仕様 |

|------|------|

| 音声 | 18秒前予告、10〜1秒、0で「抜いてください」 |

| 表示 | 入替同様・指示後すぐ CD、ゼロ時刻まで一本 |

| NG | 10秒境界で0→再カウント |



## 手動（使用者目線）



| ID | 確認内容 |

|----|----------|

| manual_op_ins_screen | 差込: 集結終了後も着弾までカウント |

| manual_op_swap_screen | 入替: 着弾UTC・意図どおりのタイミング |

| manual_op_gorei_screen | 集結: 号令〜着弾・2隊/1隊 |

| manual_op_wd_screen | 占領抜き: 指示直後CD・18秒/10秒音声 |

| manual_voice / manual_countdown | 音声テスト・デモCD |

| manual_staff_panel | 参謀パネル |



結果: `logs/qa_last_result.json`


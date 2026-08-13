---
type: review
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources:
  - "[[raw/...]]"
tags:
  - 子育て
  - 確認待ち
related: []
status: review
sensitivity: internal
priority: medium   # low | medium | high | urgent
proposed_action: Create Page   # Create Page | Update Existing | Defer | Discard
source: "[[raw/...]]"
context: ""
person_id: "P_XXX"   # 該当する場合
---

# R_{{連番}}: {{要約タイトル}}

> 確認待ち（review）は ingest 中に人間判断が必要な項目を積む場所です。アクションタイプは事前定義の4つのみ — AI が勝手に発明しません（AGENTS.md §4）。

## 発生条件

このレビューが発生した理由（AGENTS.md §4 から該当するもの）：

- [ ] 本人の状態に関する重要な変化
- [ ] 既存記録と矛盾する情報
- [ ] Sensitivity Level 判定が曖昧
- [ ] 加害・被害が疑われる記述
- [ ] 触法行為に関する記述
- [ ] 本人が他者の決定権を理解する過程で生じた深刻な困難
- [ ] 法律相談が必要な論点
- [ ] 制度改正の検知（制度ウォッチ）
- [ ] 振り分けの判断根拠に自信がない
- [ ] A-9 違反の疑い
- [ ] **「おもったこと」欄の記述を wiki に上げるか**（本Vault固有。上げる場合は原則 origin-only）
- [ ] **A-10 違反の疑い**（親の思いが事実系ページに混入しかけている）
- [ ] **koe の改訂提案**（蓄積された証拠が既存プロファイルと食い違う）

## 状況

（何が、どの raw ソースから検出されたか）

## 提案アクション

**`{{proposed_action}}`** （Create Page / Update Existing / Defer / Discard のいずれか）

### Create Page の場合
- 提案するページタイプ: ...
- 提案するファイル名: ...
- 主要内容: ...

### Update Existing の場合
- 対象ページ: [[...]]
- 追記・修正内容: ...

### Defer の場合
- 保留理由: ...
- 再判断の目安時期: YYYY-MM-DD

### Discard の場合
- 不採用理由: ...
- `wiki/reviews/discarded/` に移動して履歴は残す

## 親の判断

- [ ] 承認 → 上記アクションを実行
- [ ] 別案 → 下記コメントに記載
- [ ] さらに情報が必要

### コメント

（親の判断・指示を記録）

## 解消後の処理

- 解消日: YYYY-MM-DD
- 結果リンク: [[...]]

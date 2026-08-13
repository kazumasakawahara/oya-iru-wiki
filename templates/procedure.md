---
type: procedure
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources:
  - "[[raw/...]]"
tags:
  - 子育て
  - 手続き
related: []
status: draft
sensitivity: internal
person_id: "P_XXX"   # 個別フローの場合。汎用フローは省略可
procedure_type: application   # application | crisis | handover
---

# {{手続き名}}

> 手続きの流れ（procedure）ページは「困ったときに最短で動けるための手順書」です。本文は箇条書き・フローチャート中心で、解説は最小限に。
> 公的機関の代表番号・相談窓口はここに書いてよい（緊急時に必要）。個人に到達する連絡先だけは raw/ に置く。

## 適用条件

（いつこの手続きが必要になるか）

## 必要なもの・前提

- 書類: ...
- 連絡先: （公的窓口はここに直接。個人連絡先は → raw/）
- 想定所要時間: ...

## 手順

```mermaid
flowchart TD
    Start[開始] --> Step1[ステップ1]
    Step1 --> Decision{判断}
    Decision -->|Yes| Step2A[ステップ2A]
    Decision -->|No| Step2B[ステップ2B]
    Step2A --> End[完了]
    Step2B --> End
```

### ステップ詳細

1. **ステップ1**: ...
2. **ステップ2**: ...

## 緊急連絡先（crisis 用フローの場合）

（最優先の連絡先順）

1. ...
2. ...

## 関連する 公的制度

- [[PS_...]]

## 関連する かかわり先

- [[E_...]]

## 過去の事例・申し送り

（過去にこの手続きを行った際の trial / 学び）

- [[T_..._P_XXX]]

---
type: ecomap
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources:
  - "[[raw/...]]"
tags:
  - 子育て
  - つながりマップ
related: []
status: draft
sensitivity: internal
person_id: "P_XXX"
ecomap_purpose: current     # current | handover | crisis | meeting
mermaid_or_svg: "mermaid"
last_confirmed: YYYY-MM-DD   # この図が現状と一致すると確かめた日（目安30日）
confirmed_by: 親が確認
provided_by: 親
share_scope: consent-required
---

# {{呼び名}} のつながりマップ — {{用途}} ({{YYYY-MM}})

> つながりマップ（ecomap）は支援ネットワークのスナップショットです。月単位で更新し、本人を取り巻く関係性の変化を時系列で追えるようにします。

## 用途

- [ ] current — 現況把握
- [ ] handover — 引き継ぎ用
- [ ] crisis — 緊急時連絡網
- [ ] meeting — 支援会議・懇談資料

## ネットワーク図

```mermaid
graph TD
    Person[P_XXX 本人]

    %% 家族
    Parent[親]
    Sibling[きょうだい]

    %% 園・学校・療育
    School[園・学校 ○○]
    DayService[放デイ △△]

    %% 相談・医療
    Consultant[相談支援 □□]
    Hospital[主治医]

    %% 行政
    City[市区町村窓口]

    Person --- Parent
    Person --- Sibling
    Person --- School
    Person --- DayService
    Person --- Hospital
    Parent --- Consultant
    DayService --- Consultant
    Consultant --- City
```

## 関係性の質（凡例）

- 太線: 強い関係（日常的に密に関わる）
- 細線: 通常の関係
- 点線: 弱い関係 / 緊張関係
- 双方向矢印: 相互的な関係
- 一方向矢印: 一方的な支援・依存

## ノード詳細

### 本人 P_XXX
→ [[P_XXX_呼び名]]

### 関わる人物・組織

- [[E_...]]: 園・学校
- [[E_...]]: 放デイ等
- ...

## 変化点（前回スナップショットからの差分）

（前月との変更がある場合に記載。新規追加・関係性変化・終了等）

## 想定される将来の移行

（今後追加・変更が予想されるノード。例: 進学先・keikaku-soudan 側の相談支援専門員）

---
type: sentaku
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources:
  - "[[raw/10_日記/2026/YYYY-MM]]"
tags:
  - 子育て
  - せんたく
related: []
status: draft
sensitivity: internal   # internal 以上
person_id: "P_XXX"
sentaku_date: YYYY-MM-DD   # 必須（出来事型）
sentaku_domain: 日常   # 日常 | 食 | 衣類 | 余暇 | 対人 | 健康 | 学び | 金銭 | 住まい | 仕事
lifestage: 幼児期   # 幼児期 | 学齢期 | 思春期 | 移行期 | 成人期
outcome: 尊重された   # 尊重された | 一部尊重 | 持ち越し | 通らなかった
override_reason: ""   # outcome: 通らなかった のとき必須（lint ERROR）
provided_by: 親
share_scope: consent-required
---

# {{要約タイトル}}

> sentaku（せんたく）は、本人が選んだ・決めた・表明した・拒否した場面の記録です。親が書く型ではなく、AI が日記の「あったこと」欄から抽出します（purpose.md §3-11）。
> 「本人のようす（事実）」と「まわりの受けとめ」の分離が A-10 の実装です。両見出しは削除しないでください（lint が検査します）。

## 場面

（いつ・どこで・何の選択だったか）

## 本人のようす（事実）

（日記の事実欄から。選択肢の提示のしかた・本人の表明。見えたこと・聞こえたことだけを書く）

## まわりの受けとめ

（親・支援者の解釈。「〜したいのだと思う」はこちらに書く。事実と分離する）

## その後

（選択がどう扱われたか。通らなかった場合は override_reason に理由を必ず残す——本人の選択が通らなかった記録こそ、後の支援者が検証すべき素材です）

## 学び（次はどう提示するか）

（現時点での仮説として。koe の更新材料になる）

# schema-common — 姉妹 Vault 共通の構造ルール

このファイルは、oya-inai-keikaku-soudan（計画相談版）と oya-iru-wiki（親いる版）が**同じ意味で**持つ構造ルールを定義します。両 Vault で同一内容であり、**正本は計画相談版**です。同一性は各 Vault の `scripts/release.sh` が sha256 で照合します（`scripts/okf_core.py` と同じ扱い）。

- ここに書くもの: `scripts/okf_core.py` が**定数として**持つ宣言（必須項目・status・sensitivity・share_scope・鮮度の基底値・時点の2軸）と、その意味
- ここに書かないもの: 型の一覧、`tags` の例、`confirmed_by` / `provided_by` の語彙、どの型が「現在の主張」に属するか、鮮度更新の定期便の実装。これらは okf_core に **Config で注入**されるものであり、各 Vault の `schema.md` に書く
- 直したいときは計画相談版で直し、テスト（`scripts/test_okf_core.py`）を通してから親いる版へ同じ内容を届ける。片方だけ変えると反対側の release.sh が「ずれ」を報告する

各 Vault の `schema.md` は本ファイルを参照し、**共通からの差分だけ**を書く。

---

## A. 共通フロントマター

### A-1 必須7項目と共通の任意項目

```yaml
---
type: <各 Vault の schema.md §1 の一覧から>
created: YYYY-MM-DD          # 記録日。この記述が Vault に入った日（知得時間の始点・不変）
updated: YYYY-MM-DD          # 最終更新日
sources:
  - "[[raw/path/ファイル名]]"
tags:
  - <各 Vault の例に従う>
related:
  - "[[wiki/カテゴリ/ページ名]]"
status: draft | active | review | stale
sensitivity: public | internal | sensitive | restricted
person_id: "P_001"           # 該当しないページは省略
last_confirmed: YYYY-MM-DD   # この情報が「まだ正しい」と確かめた日（§B）。現在の主張型では推奨
confirmed_by: <各 Vault の語彙>   # 確認の手段
valid_from: YYYY-MM-DD       # この事実が成立した日（事実時間の始点。§C）。不明なら書かない
valid_until: YYYY-MM-DD      # この事実が当てはまらなくなった日（事実時間の終点。§C）。人の裁定でのみ記入
valid_until_reason: "終了の理由1行"   # valid_until を書くとき、superseded_by が無ければ必須
superseded_by: "[[...]]"     # status: stale のとき。どの記録に置き換わったか
provided_by: <各 Vault の語彙>   # 情報の出所。AI が保存先の棚から推定して付与
provided_by_detail: "○○（[[E_○○]] 参照）"   # 任意。具体名は entity 参照で
share_scope: team | consent-required | origin-only   # 宛先境界。欠落時は consent-required とみなす
source_hash: "64桁の16進（sha256）"   # 任意。sources の raw/ 原本のハッシュ
---
```

### A-2 フィールドの意味

| フィールド | 必須 | 説明 |
|------------|------|------|
| `type` | ○ | ページ型。配置ディレクトリと一致させる。一覧は各 Vault の schema.md |
| `created` | ○ | **記録日**（YYYY-MM-DD）。この記述が Vault に入った日であり、後から書き換えない。事実がいつから成立していたかは `valid_from` に書く（§C） |
| `updated` | ○ | 最終更新日（YYYY-MM-DD） |
| `sources` | ○ | 参照した `raw/` のソース。複数可 |
| `tags` | ○ | 横断検索用。最低1つは付与 |
| `related` | △ | 関連する `wiki/` ページ。空配列可 |
| `status` | ○ | `draft` / `active` / `review` / `stale` の4値（A-4） |
| `sensitivity` | ○ | アクセス制御レベル4段階（各 Vault の schema.md の Sensitivity 節） |
| `person_id` | △ | 匿名化ID。姉妹 Vault・支援DB と共有する |
| `last_confirmed` | △ | **この情報がまだ正しいと確かめた日**。`updated`（編集した日）とは別物。現在の主張型（§B）では欠落・期限超過が lint の WARN 対象。旧名 `last_validated` は同義として lint が受理 |
| `confirmed_by` | △ | 確認の手段。語彙は各 Vault。「記録のみ」が最も弱く、本人・実地での確認が最も強い |
| `valid_from` | △ | 事実が成立した日（§C）。不明なら書かない。`created` より後にはならない |
| `valid_until` | △ | 事実が当てはまらなくなった日（§C）。人が裁定して書く。AI が推定して書かない |
| `valid_until_reason` | △ | 終了の理由1行。`valid_until` を書くとき、`superseded_by` が無ければ必須 |
| `superseded_by` | △ | `status: stale` のページで、置き換え先への `[[リンク]]`。stale 化の連鎖を追えるようにする。指し先は存在するページであること |
| `provided_by` | △ | **この情報は誰から来たか**。出所の記録。語彙は各 Vault。AI が振り分け先の棚から推定して付与する（黙認方式） |
| `provided_by_detail` | △ | 提供元の具体名。entity ページ参照で書く（個人名は書かない） |
| `share_scope` | △ | **誰に渡してよいか**。`team`（支援チーム内共有可）/ `consent-required`（本人・家族・後見人の同意要）/ `origin-only`（提供元と管理者の間に留める）。欠落時は安全側の `consent-required` 扱い |
| `source_hash` | △ | **任意**。`sources` の raw/ 原本の sha256（64桁の16進）。同一原本から出たことを識別子だけで突き合わせるための橋。lint はあれば形式のみ検査し、無ければ何もしない |

### A-3 二つのコールアウト

> **sensitivity は「深さ」・share_scope は「宛先」の直交2軸。** 会議で共有済みの行動障害の詳細は sensitivity: sensitive かつ share_scope: team でありうる。`origin-only` のページは sensitivity によらず外部共有一覧（`--allowlist`）から無条件に除外される（fail-closed）。

> **`updated` と `last_confirmed` は別物。** 誤字修正でも `updated` は動くが、それは「この情報が今も正しい」ことを何も保証しない。逆に、読み返して「まだこの通り」と確かめたなら、本文を1文字も変えなくても `last_confirmed` を更新する。**確かめていないのに更新してはならない。** 後の支援者が信じてよいのは `last_confirmed` のほうである。

### A-4 status の遷移

- `draft` — 作成中。レビュー前
- `active` — 現役で使われている記録。`valid_until` が書かれた事実は `active` にできない（§C-3）
- `review` — 管理者（計画相談版は作者、親いる版は親）の判断待ち（`wiki/reviews/` と連動）
- `stale` — 過去の仮説。本人の変化等で現状と乖離。**削除せず保持する**。置き換え先があれば `superseded_by` で示す。`superseded_by` を書くページは `stale` であること

---

## B. 鮮度 — 確認日と賞味期限（証拠・鮮度モデル）

この Wiki は「作った瞬間」ではなく「**読まれる瞬間**」に正しくなければ意味がない。本人の状態は変化するため、**現在の状態を主張する型**には賞味期限の考え方を入れる。

### B-1 型の二分類（原理）

| 分類 | 性質 | 鮮度検査 |
|------|------|---------|
| **現在の主張**（陳腐化する） | 「今の本人はこうだ」を述べるページ。時間が経つと当てはまらなくなる | **対象**。`last_confirmed` の欠落・期限超過を lint が WARN。ただし `valid_until` が書かれたページ（終了した事実）は対象外（§C） |
| **出来事の記録**（証拠。日付に固定される） | 「この日にこれがあった」を述べるページ。型別の必須日付が時点を固定する | **対象外** |

どの型がどちらに属するかは各 Vault の schema.md §6-1 に書く。lint では、現在の主張型は「型別の目安（B-2）を持つ型」として Config で注入される。

### B-2 型別の確認の目安（staleAfter）— 基底値

| type | 目安 | 理由 |
|------|------|------|
| `person` | **90日** | 現況（住まい・日中活動等）は変わる |
| `protocol` | **90日** | 「今も機能している手順」でなければ手順の意味がない |
| `trigger` | **180日** | 本人の状態は変化する。喜び・苦痛の引き金も入れ替わる |
| `sensitive` | **180日** | 半年ごとに読み直す |
| `ecomap` | **30日** | 月単位スナップショットが前提 |

- 対象は `status: active` / `review` のみ（`draft`・`stale` は対象外）
- 数値を変えるときは**この表と `scripts/okf_core.py` の `BASE_STALE_AFTER_DAYS` を同時に**直す。Vault 固有の型の目安は各 schema.md と `scripts/okf_lint.py` の Config（`stale_after_days`）に置く
- `concept`・`entity`・`public-system`・`procedure` は知識ページであり対象外。制度の鮮度は `last_updated_law` と制度ウォッチで追う。`verified_on` が365日を超えた public-system は WARN（見張りの見張り）

### B-3 確認・否定の連鎖（confirms / contradicts / superseded_by）— 原理

出来事の記録は、既存の「現在の主張」に対する**証拠**として働く。

- `confirms`（まだ有効と裏づけた）→ 指し先の `last_confirmed` を出来事の日付に更新してよい（知得時間の更新）
- `contradicts`（もう合わないと示した）→ 指された側を見直す（`status: review`・改訂・`stale` ＋ `superseded_by`）。同時に、その事実がいつまで当てはまっていたかを人が裁定し `valid_until` を書く契機になる（§C）。**AI が自動では書かない**
- `superseded_by` → 置き換え先を示す。張り替えではなく「終了日＋新しい記録」で残す

どの出来事が定期便として鮮度を回すか（法定モニタリング／定期 ingest）は各 Vault の schema.md §6-3 に書く。

### B-4 三分法 — 鮮度は WARN、機微は ERROR、構造矛盾は ERROR

- **鮮度切れは WARN**。古い記録は危険信号だが、機微情報の漏出とは性質が違う。`--gate` は ERROR の有無だけを終了コードに反映するため、鮮度で pre-commit・起動時ゲートは止まらない。止めない代わりに、lint と AI の声かけ（「この情報、最近確かめましたか？」）で利用時点に見えるようにする
- **機微情報の漏出は ERROR**。個人紐づけ型の public・PII の混入・restricted の配置違反など
- **構造矛盾は ERROR**（§C-3）。時点の2軸や置き換えの連鎖が互いに食い違っている状態は、読む人を誤らせるため止める。欠落は止めない（任意項目）

**確かめていないのに `last_confirmed` を更新してはならない。** 既存ページへの一括バックフィルをしないのも同じ理由による。`valid_from` も同様に、分からないものを埋めない。

---

## C. 時点の2軸 — 事実時間と知得時間

### C-1 原理

一つのページには二つの時間がある。

| 軸 | 問い | フィールド |
|---|---|---|
| **事実時間** | その事実は、いつからいつまで当てはまっていたか | `valid_from` / `valid_until`（現在の主張型）。出来事型では型別の発生日（trial_date 等） |
| **知得時間** | その事実を、いつ記録し、いつ確かめたか | `created`（記録日・不変）/ `last_confirmed` / `confirms` / `contradicts` |

「発生日と記録日の分離」は、出来事型におけるこの2軸の現れである（発生日＝事実時間、`created`＝知得時間）。**知得と事実の混同がこの2軸の敵**である。原本に日付がなければ発生日は空欄にし、受付日で代用しない。

支援DB（Neo4j）の事実時間軸と同義で、対訳は各 Vault の操作文書（CLAUDE.md / AGENTS.md）に置く（created↔registeredAt、last_confirmed↔lastConfirmedAt、valid_from↔validFrom、valid_until↔validTo）。

### C-2 フィールド（現在の主張型に任意で追加）

| フィールド | 意味 | 必須 | 書く人 |
|---|---|---|---|
| `valid_from` | この事実が成立した日（事実時間の始点）。不明なら書かない | 任意 | 人（親いる版は AI 提案→親が確定） |
| `valid_until` | この事実が当てはまらなくなった日（事実時間の終点）。人の裁定でのみ記入 | 任意 | 人 |
| `valid_until_reason` | 終了の理由1行。`superseded_by` があれば省略可 | valid_until 記入時にどちらか必須 | 人 |
| `superseded_by` | 既存。置き換え先ページへの `[[リンク]]` | 任意 | 人 |

対象は現在の主張型のうち person / protocol / trigger / sensitive（親いる版は koe も）。ecomap は時点固定のスナップショットとして2軸を持たない。出来事型は既存の型別日付が事実時間であり、新フィールドは不要。

### C-3 検査（okf_core）

| 検査 | 重さ | 対象 |
|---|---|---|
| `valid_from` ＞ `valid_until` | ERROR | 現在の主張型 |
| `valid_from` ＞ `created`（記録より先に成立していない事実は書けない） | ERROR | 現在の主張型 |
| `superseded_by` の指し先が存在しない、または指す側の status が stale でない | ERROR | 全型 |
| `valid_until` ありで `status: active` | ERROR | 現在の主張型 |
| `valid_until` ありで `superseded_by` も `valid_until_reason` も無い | ERROR | 現在の主張型 |
| `contradicts` で指されているが `valid_until` が空 | WARN | 現在の主張型 |
| 鮮度（staleAfter 超過） | WARN | 現在の主張型のうち `valid_until` が空のものに限る |
| 日付書式（YYYY-MM-DD） | WARN | 新フィールド |

出来事型の発生日と `created` の前後関係は検査しない（計画の交付日など将来日付が正常のため）。新フィールドの欠落は何も出さない。

### C-4 読むときの約束（AI 起動ゲートの共通節）

- `valid_until` が記入された事実を「現在の事実」として答えない。答えるときは「〜まで有効だった」と期間を添える
- 鮮度切れ（staleAfter 超過・`valid_until` 空）のページから答えるときは、最終確認日を添える
- `valid_until` は AI が推定して書かない。終了は人が裁定する

---

*作成: 2026-09-04（共通基盤・柱2 Step 1。経緯は計画相談版 docs/phase-common-2-implementation-plan.md）*

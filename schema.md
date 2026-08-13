# schema — 構造ルール

このファイルは Vault の構造ルール（日記の書式・フロントマター仕様・ページ型・対訳語彙・Sensitivity Level・命名規約・鮮度）を定義します。AI への操作指示の正典は AGENTS.md、存在理由の正典は purpose.md です。AGENTS.md と矛盾が生じた場合は AGENTS.md を優先し、本ファイルを更新してください。

---

## 0. 日記の書式 — 本Vaultの第一の書式規律

日記は本Vaultの心臓であり、親に求める唯一の記録である。書式はこの節がすべてであり、これ以上の規律を親に課してはならない。

### 0-1 置き場所・ファイル単位・記入経路

- 置き場所: `raw/10_日記/<年>/` （例: `raw/10_日記/2026/`）
- **1ヶ月1ファイル**: `YYYY-MM.md`（例: `2026-08.md`）。日付見出しで追記していく
- 日記ファイルに**フロントマターは不要**（親の手間を増やさない。raw/ は lint のフロントマター検査対象外）
- **記入経路は2つ。原則は (a)**（2026-08-13 確定）:
  - **(a) チャットで語る（原則）**: 親が「今日こんなことがあった」と AI に話す。AI が事実と思いを聞き分け、本節の書式で当月ファイルへの追記を宣言→承認→実行する。親は Obsidian も Markdown も知らなくてよい
  - **(b) ファイルに直接書く（オプション）**: Obsidian に慣れた親は templates/日記.md の書式で直接書いてよい。どちらの経路でも同じ日記ファイルに、同じ書式で落ちる
- 外部資料（連絡帳の写真・書類等）は日記ファイルに貼らず、受付箱経由で 20〜90 の棚へ

### 0-2 1日分の書式（templates/日記.md）

```markdown
## 2026-08-13

### あったこと
（事実。何があり、本人がどうしたか・どう伝えてきたか。1行でもよい）

### おもったこと
（親の思い。解釈・心配・嬉しさ・迷い。何を書いてもよい。空欄でもよい）
```

- 日付見出しは `## YYYY-MM-DD`（機械処理のため ISO 形式。後ろに曜日等を添えてよい: `## 2026-08-13 水`）
- 2欄の見出しは `### あったこと` / `### おもったこと` で固定（A-10 の実装。AI はこの見出しで事実と思いを区別する）
- 分量は1行でもよい。「今日は何もなかった」も記録である。書かない日があってもよい
- 「おもったこと」欄は空欄でもよい。逆に「おもったこと」だけの日もあってよい（その日は事実欄を空欄にする）

### 0-3 編集と凍結（append-only との折り合い）

- **書いた月のうちは編集可**（誤字修正・書き足し自由）
- **月が変わったら凍結**: 以後そのファイルは追記専用。過去の記述を書き換えない（過去の観察は、後から見れば間違いでも、その時点の記録として価値を持つ）
- 凍結後に訂正したいことができたら、今月の日記に「○月○日の件、実は…」と書く。それが正しい訂正の形である

---

## 1. 共通フロントマター（wiki/ 全ページ必須）

```yaml
---
type: person | koe | sentaku | fushime | trial | protocol | trigger | concept | entity | ecomap | sensitive | public-system | procedure | query | review
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources:
  - "[[raw/path/ファイル名]]"
tags:
  - 子育て
  - 知的障害
related:
  - "[[wiki/カテゴリ/ページ名]]"
status: draft | active | review | stale
sensitivity: public | internal | sensitive | restricted
person_id: "P_001"   # 該当しないページは省略
lifestage: 幼児期 | 学齢期 | 思春期 | 移行期 | 成人期   # 個人紐づけ型で推奨
last_confirmed: YYYY-MM-DD   # この情報が「まだ正しい」と確かめた日（§6）。現況を主張する型では推奨
confirmed_by: 記録のみ | 本人に確認 | 親が確認 | 支援者に確認 | 実地で確認   # 確認の手段
superseded_by: "[[...]]"     # status: stale のとき。どの記録に置き換わったか
provided_by: 本人 | 親 | 家族 | 園・学校 | 事業所 | 医療機関 | 行政 | 会議 | 相談支援   # 情報の出所（§7）。AI が保存先の棚から推定して付与
provided_by_detail: "放デイ○○（[[E_放デイ○○]] 参照）"   # 任意。具体名は entity 参照で
share_scope: team | consent-required | origin-only   # 宛先境界。欠落時は consent-required とみなす
source_hash: "64桁の16進（sha256）"   # 任意。keikaku-soudan と同一原本を突き合わせるための橋
---
```

### 姉妹版（oya-inai-keikaku-soudan）からの変更点

| 項目 | 姉妹版 | 本Vault |
|------|--------|---------|
| 型の構成 | 15型（plan / monitoring / meeting / 他12型） | **15型（koe / sentaku / fushime ＋ 継承12型）**。plan / monitoring / meeting は非搭載（並走する keikaku-soudan 側の正本と重複記録しない） |
| `confirmed_by` の語彙 | 家族に確認 | **親が確認**（本Vaultの一人称は親。「家族に確認」も互換のため受理） |
| `provided_by` の語彙 | 後見人を含む8値 | **親・園・学校を含む9値**（上記）。移行期以降に後見人が現れたら追加する |
| `lifestage` | なし | **追加**（個人紐づけ型で推奨。幼児期〜成人期の5値） |

> **sensitivity は「深さ」・share_scope は「宛先」の直交2軸。** `origin-only` のページは sensitivity によらず外部共有一覧（--allowlist）から無条件に除外される（fail-closed）。日記の「おもったこと」欄由来の記述を wiki に上げる場合は原則 `origin-only`（親元に留める）から始める。
>
> **`updated` と `last_confirmed` は別物。** 誤字修正でも `updated` は動くが、それは「この情報が今も正しい」ことを保証しない。読み返して「まだこの通り」と確かめたなら、本文を変えなくても `last_confirmed` を更新する。**確かめていないのに更新してはならない。**

### status の遷移

- `draft` — 作成中。レビュー前
- `active` — 現役で使われている記録
- `review` — 親の判断待ち（`wiki/reviews/` と連動）
- `stale` — 過去の仮説。本人の成長・変化で現状と乖離。**削除せず保持する**。置き換え先があれば `superseded_by` で示す

---

## 2. 対訳語彙表 — 型ID と人が読む面のことば

型ID・接頭辞・frontmatter キーは機械処理（lint・git・クロスプラットフォーム）のためアルファベットとする。ただし**人が読む面（宣言・報告・説明・docs）では必ず日本語の対訳を使う**。新設3型の ID は日本語のローマ字であり、対訳は自明である。

| 型ID | 対訳（人が読む面での呼称） | 確定状況 |
|------|--------------------------|---------|
| `koe` | **こえ（意思表出プロファイル）** | 確定（2026-08-13） |
| `sentaku` | **せんたく（選択の記録）** | 確定（2026-08-13） |
| `fushime` | **ふしめ（節目の記録）** | 確定（2026-08-13） |
| `protocol` | **手順書** | 確定（姉妹版から継承） |
| `trial` | **ためしたこと** | 確定（2026-08-13） |
| `trigger` | **きっかけ**（姉妹版の「引き金」ではなく本Vaultでは「きっかけ」。joy / distress の両方向に自然な語のため） | 確定（2026-08-13） |
| `person` | **ひと（本人・家族・支援者のページ）** | 確定（2026-08-13） |
| `concept` | **ことばの解説** | 確定（2026-08-13） |
| `entity` | **かかわり先（園・学校・事業所・窓口）** | 確定（2026-08-13） |
| `ecomap` | **つながりマップ** | 確定（2026-08-13） |
| `sensitive` | **とりあつかい注意** | 確定（2026-08-13） |
| `public-system` | **公的制度** | 確定（2026-08-13） |
| `procedure` | **手続きの流れ** | 確定（2026-08-13） |
| `query` | **問いと答え** | 確定（2026-08-13） |
| `review` | **確認待ち** | 確定（2026-08-13） |

継承12型の ID 自体は keikaku-soudan 互換のため変更しない（識別子の変更は DRIFT を生む。対訳のみ）。

---

## 3. 新設3型の仕様

### 3-1 sentaku（せんたく — 選択・意思表明の記録）

「本人が選んだ・決めた・表明した・拒否した」場面の記録。**親が書く型ではなく、AI が日記の「あったこと」欄から抽出する型**。幼児期の「2つのおやつから選んだ」から成人期の「住まいを決めた」まで同じ型で貫く。

```yaml
type: sentaku                 # 接頭辞 ST_、wiki/sentaku/
sentaku_date: YYYY-MM-DD      # 必須（出来事型・鮮度検査対象外）
person_id: "P_001"            # 必須
sentaku_domain: 日常 | 食 | 衣類 | 余暇 | 対人 | 健康 | 学び | 金銭 | 住まい | 仕事
lifestage: 幼児期 | 学齢期 | 思春期 | 移行期 | 成人期
outcome: 尊重された | 一部尊重 | 持ち越し | 通らなかった
override_reason: "…"          # outcome: 通らなかった のとき必須（lint ERROR）
sensitivity: internal         # internal 以上
```

**本文構造**（見出し固定。★の2見出しの存在は lint が検査＝A-10 の構造検査）

- `## 場面`（いつ・どこで・何の選択だったか）
- ★`## 本人のようす（事実）`（日記の事実欄から。選択肢の提示のしかた・本人の表明）
- ★`## まわりの受けとめ`（親・支援者の解釈。事実と分離して書く）
- `## その後`（選択がどう扱われたか）
- `## 学び（次はどう提示するか）`

> `outcome: 通らなかった` の `override_reason` 必須は、意思決定支援ガイドライン（本人の意思と異なる判断をした場合の記録義務）の実装。本人の選択が通らなかった記録こそ、後の支援者が検証すべき素材である（purpose.md G-3）。

### 3-2 koe（こえ — 意思表出プロファイル）— バイブルの心臓

本人が「はい・いいえ・嫌・好き・困った」をどう表すかの**現在**プロファイル。sentaku・trial の蓄積から AI が帰納して起草し、親の承認を経て維持する。

```yaml
type: koe                     # 接頭辞 KO_、wiki/koe/
person_id: "P_001"            # 必須
lifestage: …
last_confirmed: YYYY-MM-DD    # 現在の主張型・鮮度検査対象（staleAfter 90日）
confirmed_by: 親が確認 | 本人に確認 | 支援者に確認 | 実地で確認
evidence: ["[[ST_...]]", "[[T_...]]"]   # 根拠となる sentaku / trial へのリンク
sensitivity: internal         # internal 以上を lint が強制
```

**本文構造**

- `## はい・いいえ・嫌の表し方`
- `## 伝わりやすい示し方`（実物・写真・絵カード・二択・体験してから 等）
- `## 表出を妨げるもの`（急かし・選択肢過多・特定の場面 等）
- `## 誤読されやすいサイン`（例:「笑っている＝同意」ではない）
- `## この記録を読む支援者へ`

### 3-3 fushime（ふしめ — 節目の記録）

就園・就学・進学・卒業・サービス開始/終了・手帳更新・18歳・20歳等の記録。当時の**判断の過程**（何を諦め何を優先したか、本人はどう関わったか）を残す。keikaku-soudan の plan「この計画にした理由」に相当する内容の受け皿。

```yaml
type: fushime                 # 接頭辞 FS_、wiki/fushime/
person_id: "P_001"            # 必須
occurred_on: YYYY-MM-DD       # 必須（出来事型・鮮度検査対象外）
fushime_kind: 就園・就学 | 進級・進学 | 卒業 | サービス開始 | サービス終了 | 制度切替 | 転居 | 家族の変化 | その他
lifestage: …
sensitivity: internal         # internal 以上
```

**本文構造**

- `## 何があったか`
- `## 判断の過程`（何を比べ、何を諦め、何を優先したか）
- `## 本人はどう関わったか`（見学した・選んだ・嫌がった・関われなかった、も含めて）
- `## いま振り返って`（任意。後から追記してよい）

---

## 4. 継承型の追加フィールド（姉妹版からの差分のみ記す）

姉妹版 schema.md §2 を基礎とし、本Vaultでの差分だけをここに記す。差分のない型（concept / entity / ecomap / sensitive / public-system / procedure / query / review）は姉妹版の仕様のまま移植する（Phase 2 で本節に展開）。

### 4-1 person（ひと）

姉妹版仕様＋以下の差分:

- frontmatter に `lifestage` を追加
- 本文構造に以下の2見出しを追加:
  - `## 意思表明のスタイル` → `[[koe/KO_...]]` へのリンク（詳細は koe が正本）
  - `## 選択の歴史` → `[[sentaku/ST_...]]` へのリンク集（時系列）

### 4-2 trial（ためしたこと）/ protocol（手順書）/ trigger（きっかけ）

姉妹版仕様どおり（trial_outcome の4値・confirms / contradicts・サブドメイン・protocol_domain・trigger_type 等すべて継承）。差分:

- protocol_domain に子育て場面の追加を Phase 2 で確定（候補: `school-morning`（登園・登校）、`homework`、`play` 等）
- trial の confirms / contradicts の指し先に koe を含める（「この示し方で選べた」は koe の証拠になる）

### 4-3 plan / monitoring / meeting / season — 非搭載

これらの型は本Vaultに存在しない。lint は `type: plan` 等を**未知の型として ERROR** にする。会議録・計画の写しは raw/70_会議・面談 に落とし、内容は fushime・sentaku・protocol 等に編む。

---

## 5. Sensitivity Level・命名規約・配置

### 5-1 Sensitivity 4段階（姉妹版を全面継承）

| Level | 内容 | 本Vaultでの例 | 配置 |
|-------|------|------|------|
| `public` | 一般的な情報 | 公的制度の解説、ことばの解説 | `wiki/concepts/`, `wiki/public-systems/` |
| `internal` | 支援に必要だが本人特定可能 | 手順書、きっかけ、**koe・sentaku・fushime**（下限） | `wiki/protocols/` ほか |
| `sensitive` | 慎重な扱いが必要 | 性に関する基礎情報、行動の詳細、トラウマ | `wiki/sensitive/` |
| `restricted` | 極めて慎重な扱いが必要 | 被害・加害が現実化した具体記録、医療上の機微情報 | `wiki/sensitive/restricted/` |

- **個人に紐づく型**（public 禁止・pre-commit 関所2の対象）: person / **koe / sentaku / fushime** / trial / protocol / trigger / ecomap / sensitive / procedure（個別フロー）
- sensitive 領域の記述原則（目的の明示・双方向性・「この記録を読む支援者へ」併記等）は姉妹版 §3-2 を全面継承
- 本Vault追加原則（purpose.md §5 参照）: きょうだい児の記述は本人の支援に必要な範囲に留める（A-2 系）。写真・動画等のバイナリで顔が写るものは raw/ のみ、wiki/ からは参照リンクのみ
- **20年後の本人が読む前提**: 記述レビューの基準は「成人した本人の前で読み上げて恥ずかしくないか」

### 5-2 命名規約（本Vaultの型のみ）

| 要素 | 接頭辞 | 例 | 備考 |
|------|--------|-----|------|
| Person | `P_` | `P_001_山田花子.md` | ID は keikaku-soudan と互換。実名は raw/ のみの原則も同じ |
| **Koe** | `KO_` | `KO_P_001_こえのプロファイル.md` | 1人につき現役1枚（改訂は同ファイル更新＋log） |
| **Sentaku** | `ST_` | `ST_2026-08-10_おやつの二択_P_001.md` | 日付込み |
| **Fushime** | `FS_` | `FS_2026-04-01_就学_P_001.md` | 日付・種別込み |
| Trial | `T_` / `TD_` | `T_2026-08-05_絵カードでの二択_P_001.md` | TD_ は decision-rights-learning 専用（継承） |
| Protocol | `PR_` / `PRD_` / `PRW_` | `PR_morning_朝のしたく_P_001.md` | 継承 |
| Trigger | `TG_` | `TG_joy_電車と時刻表_P_001.md` | 継承 |
| Ecomap | `EM_` | `EM_current_P_001_2026-08.md` | 継承 |
| Concept / Entity | `C_` / `CD_` / `E_` | `C_感覚過敏.md`, `E_放デイたんぽぽ.md` | 継承 |
| Sensitive | `SE_` / `SED_` | 継承 | |
| Public System / Procedure | `PS_` / `PC_` | `PS_特別児童扶養手当.md` | 継承 |
| Query / Review | `Q_` / `R_` | 継承 | |

ファイル名の説明部・見出し・人が読む面はすべて日本語（`TG_joy_電車と時刻表_P_001.md` 方式）。

### 5-3 type と配置ディレクトリの対応

継承12型は姉妹版どおり。新設3型:

| type | ディレクトリ |
|------|--------------|
| koe | `wiki/koe/` |
| sentaku | `wiki/sentaku/` |
| fushime | `wiki/fushime/` |

`type` フィールドと配置ディレクトリの不整合は lint の検出対象。

---

## 6. 鮮度 — 確認日と賞味期限

このWikiは「作った瞬間」ではなく「**読まれる瞬間**」——新しい支援者が本人と出会う場面——に正しくなければ意味がない。子どもは大人よりずっと速く変化するため、**現在の状態を主張する型**には賞味期限の考え方を入れる。

### 6-1 型の二分類

| 分類 | 型 | 鮮度検査 |
|------|-----|---------|
| **現在の主張**(陳腐化する) | person / **koe** / protocol / trigger / ecomap / sensitive | **対象**。`last_confirmed` の欠落・期限超過を lint が WARN |
| **出来事の記録**（証拠。日付に固定される） | **sentaku / fushime** / trial / query | **対象外**。必須日付（sentaku_date / occurred_on / trial_date / query_date）が時点を固定する |

### 6-2 型別の確認の目安（staleAfter）

| type | 目安 | 理由 |
|------|------|------|
| `person` | **90日** | 現況（生活・園学校等）は変わる |
| `koe` | **90日** | 意思表出のしかたは成長とともに変わる。バイブルの心臓が古いのが一番危険 |
| `protocol` | **90日** | 「今も機能している手順」でなければ手順の意味がない |
| `trigger` | **180日** | 好き・苦手のきっかけも入れ替わる |
| `sensitive` | **180日** | 半年ごとに読み直す |
| `ecomap` | **30日** | 月単位スナップショットが前提 |

- 子どもは変化が速いため、実運用で「90日でも遅い」と分かった型は短縮する（Phase 2 の lint 定数確定時、および実証フェーズで見直し）
- 対象は `status: active` / `review` のみ。数値を変えるときは**この表と `scripts/okf_lint.py` の `STALE_AFTER_DAYS` を同時に**直す

### 6-3 鮮度更新の定期便は「定期 ingest」に同乗する

姉妹版では法定モニタリングが鮮度更新の定期便だったが、本Vaultに monitoring 型はない。代わりに**AI の定期 ingest の締め**が定期便になる:

1. ingest の締めに AI は必ず尋ねる:「この1ヶ月の日記から、◯◯の手順書と△△のきっかけは今も合っていそうです。まだこの通りですか？」
2. 親が「確かめた・まだこの通り」と答えたものだけ `last_confirmed` を更新する（confirmed_by: 親が確認）
3. 日記・trial が「もう合わない」ことを示していたら `contradicts` に記録し、指された側を見直す（`status: review`・改訂・`stale`＋`superseded_by`）

**確かめていないのに `last_confirmed` を更新してはならない**（既存ページへの一括バックフィル禁止も同じ理由）。独立した「振り返り儀式」を親に課さない——鮮度は日記と ingest のリズムの中で回る。

### 6-4 鮮度は WARN、機微は ERROR

鮮度切れは ERROR にしない（古い記録は危険信号だが、機微情報の漏出とは性質が違う）。`--gate` は ERROR の有無だけを終了コードに反映するため、鮮度で pre-commit・起動時ゲートは止まらない。止めない代わりに、lint と AI の声かけで利用時点に見えるようにする。

---

*作成日: 2026-08-13（Phase 1 起草）*
*土台: oya-inai-keikaku-soudan/schema.md を PLAN.md v1.1 §4・§6 の方針で改稿*
*起草: Claude（作者の指示に基づく）。2026-08-13 作者レビュー済み・確定（対訳語彙9件・日記見出し階層を含む）*

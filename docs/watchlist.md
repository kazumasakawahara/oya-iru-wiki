# watchlist — 制度ウォッチ監視対象台帳

- 作成: 2026-08-13（姉妹版 oya-inai-keikaku-soudan の watchlist R4 を土台に、児童期の制度を追加して移植）
- **このファイルが制度ウォッチの正典**です。監視ツール（firecrawl monitor 等）はこの台帳に従属し、いつでも差し替え可能です（ツール中立）
- この台帳は「**外の変化**（法改正・制度変更）」を見張ります。「**本人の時間**（何歳で何が来るか）」は `docs/年齢イベント表.md` が見張ります。制度改正を検知したら年齢イベント表への波及も点検します
- 巡回頻度: **月次を基本**とし、報酬改定期・法改正施行期（例年 1〜4月）は週次に密度を上げる
- 点検で変更を検知したら: ① 取得内容を `raw/50_行政・制度/` に保存（出所 URL・取得日付き）→ ② review（確認待ち）を起票 → ③ **親の判断で**該当ページ・年齢イベント表を更新。**機械は起票まで、判断と反映は人間**

---

## 1. 全国共通の監視対象（初期セット）

URL は姉妹版で 2026-08-10 に実在確認済み。児童期の追加分（#A1〜A4）と主要5件は 2026-08-13 に再確認済み。

**monitor の登録（任意・導入後でよい）**: firecrawl monitor を使う場合の実地の知見です（他ツールでも可）。
1. 下表の URL を1つの monitor にまとめて登録する
2. **作成時の scheduleText は "daily at 9:00" 等しか受け付けない**ため、いったん daily で作成し、直後に cron `0 9 1 * *`（毎月1日 9:00）へ変更する。daily のままだと費用が約30倍かかる
3. goal 判定をオンにし、「法改正・報酬改定・新しい通知/資料の追加・制度運用の変更・様式の改定」を意味のある変更とする（誤字・レイアウト変更は除外）
4. 登録後、monitor ID 列と「最終点検」列を記入する
5. 初回実行はベースライン取得。**差分検知が発火するのは2巡目以降**

### 児童期の制度（本 Vault で追加）

| # | 監視対象（一次情報源） | URL | monitor ID | 最終点検 |
|---|------------------------|-----|-----------|----------|
| A1 | こども家庭庁: 障害児支援（児童発達支援・放課後等デイサービス等） | https://www.cfa.go.jp/policies/shougaijishien/ | （未登録） | — |
| A2 | 厚労省: 特別児童扶養手当 | https://www.mhlw.go.jp/bunya/shougaihoken/jidou/huyou.html | （未登録） | — |
| A3 | 厚労省: 障害児福祉手当 | https://www.mhlw.go.jp/bunya/shougaihoken/jidou/hukushi.html | （未登録） | — |
| A4 | 文科省: 特別支援教育（就学相談・就学先決定を含む） | https://www.mext.go.jp/a_menu/shotou/tokubetu/main.htm | （未登録） | — |

> 療育手帳は**自治体運用**のため全国共通枠に一次情報源がありません（厚労省の手帳ページ #1 が上位の受け皿）。お住まいの自治体のページを §2 の地域枠に登録するのが実効的です。

### 全年齢の制度（姉妹版から継承）

| # | 監視対象（一次情報源） | URL | monitor ID | 最終点検 |
|---|------------------------|-----|-----------|----------|
| 1 | 厚労省: 障害者手帳 | https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/hukushi_kaigo/shougaishahukushi/shougaishatechou/index.html | （未登録） | — |
| 2 | 日本年金機構: 障害年金の制度 | https://www.nenkin.go.jp/service/jukyu/seido/shougainenkin/index.html | （未登録） | — |
| 2b | 厚労省: 特別障害者手当（20歳以降） | https://www.mhlw.go.jp/bunya/shougaihoken/jidou/tokubetsu.html | （未登録） | — |
| 3 | 厚労省: 障害福祉サービス等（総合） | https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/hukushi_kaigo/shougaishahukushi/service/index.html | （未登録） | — |
| 3b | e-Gov: 障害者総合支援法（条文） | https://elaws.e-gov.go.jp/document?lawid=417AC0000000123 | （未登録） | — |
| 4 | 厚労省: 自立支援医療 | https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/hukushi_kaigo/shougaishahukushi/jiritsu/index.html | （未登録） | — |
| 5 | 厚労省: 成年後見はやわかり（制度ポータル） | https://guardianship.mhlw.go.jp/ | （未登録） | — |
| 6 | 厚労省: 日常生活自立支援事業 | https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/hukushi_kaigo/seikatsuhogo/chiiki-fukusi-yougo/index.html | （未登録） | — |
| 7 | 厚労省: 障害者虐待防止法 | https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/hukushi_kaigo/shougaishahukushi/gyakutaiboushi/index.html | （未登録） | — |
| 8 | 内閣府: 障害者差別解消法 | https://www8.cao.go.jp/shougai/suishin/law_h25-65.html | （未登録） | — |

> 姉妹版にある報酬改定・通知類・基本方針の細分 URL は、専門職向けのため本 Vault の初期セットから外しました。相談支援専門員が付いている家庭では、そちらの watchlist が細部を見張っています（`docs/連携マッピング表.md`）。

## 2. 地域枠（初期は空 — 導入時にあなたの自治体を登録してください）

お住まいの自治体に関する監視対象は配布物に焼き込みません。AI と一緒に次の形式で追加してください（→ 手順は §4）。**療育手帳（判定基準・再判定周期）と医療費助成・就学相談の窓口は自治体差が大きく、地域枠こそが実用の中心です。**

| 対応ページ | 監視対象 | URL | monitor ID | 最終点検 |
|-----------|----------|-----|-----------|----------|
| （記入例）◯◯市の障害福祉 | ◯◯市: 障害福祉のページ | https://…（あなたの自治体の該当ページ） | — | — |

<!-- 地域枠の行はこの下に追加 -->

## 3. 月次点検の手順

1. monitor の検知結果を確認する（未登録の間は各 URL を AI に巡回依頼）
2. 変更があった対象は、取得内容を `raw/50_行政・制度/` に保存（ファイル名に取得日、冒頭に出所 URL）
3. `templates/review.md` で確認待ちを起票（発生条件: 制度改正の検知）
4. 親が判断 → 影響先を更新: 該当する wiki ページ（あれば）と **`docs/年齢イベント表.md` の該当行**
5. 本台帳の「最終点検」列を更新

> 本 Vault は公的制度ページ（PS_）を同梱していません。制度の知識ページが必要になったら `templates/public-system.md` から作れます（作った PS_ ページは lint の鮮度検査対象になります）。

## 4. 地域枠の追加手順（約10分）

1. あなたの自治体名＋「障害福祉」「療育手帳」「就学相談」で公式サイトの該当ページを探す（AI に「◯◯市の障害福祉のページを watchlist に登録して」と頼めば、検索→URL 確認→本台帳への追記まで行います）
2. §2 の表に1行追加
3. monitor を使う場合は登録し、monitor ID を記入

## 5. 変更履歴

- （導入日を記入）: 本 Vault に導入。地域枠の登録を実施
- 2026-08-13: 配布版初版。姉妹版 watchlist（R4・URL 実在確認 2026-08-10）を土台に、児童期4件（こども家庭庁 障害児支援・特別児童扶養手当・障害児福祉手当・特別支援教育）を追加。追加分と主要5件の URL 到達・ページ題名を 2026-08-13 に確認済み

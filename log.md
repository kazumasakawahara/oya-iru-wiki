# log — 操作ログ（append-only）

> すべての ingest・振り分け・wiki 書き込みを AI が1エントリずつ追記します。raw/ は git 管理外のため、この log が振り分けの唯一の履歴です。

## 2026-08-13 | build | Phase 1〜2（テンプレート構築）
- Phase 1: purpose.md / schema.md / AGENTS.md（正典）＋CLAUDE.md・GEMINI.md シム / templates/日記.md を起草、作者レビューで確定（A-10 文言・対訳語彙15件・日記書式を含む）
- Phase 2: ディレクトリ骨格 / templates 16枚 / okf_lint.py（新設3型ゲート・A-10 構造検査・日記凍結ハッシュ台帳）/ pre-commit（関所2 を koe・sentaku・fushime に差し替え）/ 回帰テスト移植
- 検証: test_okf_lint.py 32ケース＋4シナリオ green。空 Vault で lint 終了コード 0
- DoD 検証（2026-08-13）: 壊したページ（sentaku `通らなかった`＋override_reason 欠落）を wiki/sentaku/ に実際に置いて ERROR（exit 2）を目視確認 → 撤去後 --gate 0・全チェック 0。pre-commit 関所テスト 5/5（関所1で日本語棚名の quotepath すり抜けを検出し修正済み）

## 2026-08-13 | build | Phase 3（記入例パッケージ）
- 架空人物 P_900 そら（5歳・ASD）/ P_901 かえで（16歳・知的障害）の記入例 23ファイル: 日記2本（7月・凍結月の実例）＋園連絡帳＋進路面談メモ＋仕分け宣言、wiki 型ページ16枚（persons 2 / koe 1 / sentaku 3 / fushime 1 / trials 3 / triggers 3 / protocol 1 / sensitive 1 / review 1）
- DoD 検証: 記入例16ページを一時 Vault の wiki/ にコピーして lint → 違反なし（exit 0）。ST_2026-07-18 から override_reason を削って ERROR（exit 2）を実確認。「通らなかった」例・失敗 trial 例・TD（第二の柱の幼児期例）・A-10 review 起票例を含む

## 2026-08-13 | build | Phase 4（docs 6本）
- docs/ 6本を執筆: 導入手順（30分・チャット原則＋AI 選択チェックリスト＋スケジュール環境別レシピ＋手動運用の下限）/ 親のための完全導入マニュアル（非技術者向け・Markdown 説明ゼロ）/ 年齢イベント表（生年月1箇所登録・一般論明記・watchlist と役割分担）/ 意思決定支援者のための読み方 / 連携マッピング表（並走共有＋全面引き継ぎ）/ watchlist（姉妹版 R4 移植＋児童期4件追加。追加 URL は 2026-08-13 到達・題名確認済み）
- DoD 検証: 一時ディレクトリに clone し導入手順の機械 Step を再現 → 12項目 PASS（遮断・chmod・lint 0・--gate 0・P_001 作成後 lint 0・日記追記後 lint 0・関所通過 commit・raw 強制ステージを関所1が阻止）。親向け2文書に Markdown 操作の説明が無いことを grep で確認

## 2026-08-13 | build | Phase 5（β配布準備）
- README.md（一文定義・「仕組みは検証済み・実務適合は未検証」明記・動作確認済み AI 表・手動運用下限・C 案は言及のみ・姉妹版/oya-inai への参照）・LICENSE（MIT）を作成
- 公開前 PII 最終点検（git 追跡88ファイル機械走査）: raw=棚README のみ／wiki=.gitkeep のみ／記入例 person_id=P_9xx のみ／電話・メール・郵便パターンなし／gate 0 — すべて PASS。検出1件: PLAN.md・HANDOVER.md（開発メタ文書）に作者ローカルパス → 公開範囲の論点としてレビューへ
- レビュー決着（2026-08-13 河原さん）: 著作権者=特定非営利活動法人 nest／開発メタ文書は公開物に含めない（クリーンエクスポート方式で公開する。手順は docs/phase5-implementation-plan.md）／公開タイミングは別途判断（今回は公開せず）

## 2026-08-13 | publish | GitHub 公開＋nest-webpage 掲載（河原さん承認）
- nest-webpage「親なき後」ツール・しくみへの掲載構成案を河原さんが承認 → 公開実行
- クリーンエクスポート（85ファイル・開発メタ6件除外）→ エクスポート先で PII 再点検（作者パス含めゼロ、lint テストの意図的フィクスチャのみ）→ https://github.com/kazumasakawahara/oya-iru-wiki を public で作成・push
- 親のための完全導入マニュアルの clone URL を実 URL に更新（両リポジトリ）
- nest-webpage（ブランチ feat/oya-iru-wiki-family）: ツールページ2部構成化（ご家族の方へ=話す→編まれる→手渡す＋「日記からつくる、わが子のバイブル」カード／橋渡し文／支援者3段は不変）・マニュアル HTML 同梱・ハブ予告文更新・免責ページ追記。ビルド green・成果物検証 10項目 OK・スクリーンショット目視確認。本番デプロイは河原さんの指示待ち

## 2026-08-13 | build | くわしい手順書4冊（初心者向けテーマ別ガイド。河原さん指示）
- docs/くわしい手順/ に4冊新設: ①テンプレートを手に入れる（GitHub・ZIP中心・登録不要）②Obsidianを入れてVaultとして開く ③Claudeを用意してフォルダを見せる（学習ポリシー確認・MCP・完全終了）④黒い画面をこわがらない（lint・chmod・hooksPath をコピペで）
- 親のための完全導入マニュアル（読み方＋3-1・3-2・第4章・5-1）と導入手順（冒頭＋Step 1〜3）に 🔰 リンクを差し込み
- HTML 版5本（マニュアル再生成＋手順書4冊）を nest-webpage /internal/ に生成。文書間 .md リンクは .html へ機械的に書き換え（残存ゼロを検証）・スクリーンショット目視確認

## 2026-08-14 | build | ラッパースキル同梱（河原さん発案・承認）
- `.claude/skills/` と `.codex/skills/` に同一内容の薄いスキル3つを新設: oya-iru-ingest / oya-iru-query / oya-iru-lint
- スキルは AGENTS.md の該当節（§3-1・§3-2・§3-3）へ誘導するだけの着火装置。手順の正典は AGENTS.md 一箇所のまま（PLAN §12-9 に設計判断を記録）
- AGENTS.md §9 と README「AI について」に同梱の旨を追記

## （導入日を記入） | setup | Vault 導入
- oya-iru-wiki テンプレートから導入。
- 実施: lint 初回実行 / pre-commit 有効化 / AGENTS.md 環境調整（スケジュールタスク登録）→ docs/導入手順.md

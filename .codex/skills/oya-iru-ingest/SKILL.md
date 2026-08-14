---
name: oya-iru-ingest
description: oya-iru-wiki Vault の取り込み（ingest）。親の日記や受付箱の資料を wiki に整理するとき、「取り込んで」と頼まれたとき、定期（月次）の ingest を実行するときに必ず使う。
---

# oya-iru-wiki: ingest（取り込み）

このスキルは着火装置です。**手順の正典は Vault 直下の AGENTS.md** にあり、ここには複製しません。

1. Vault 直下の `AGENTS.md` を開き、**§2（絶対遵守のガードレール）と §3-1（ingest）**を読む
2. 作業前に `python3 scripts/okf_lint.py --gate` を実行する（§5。終了コード 2 なら作業に入らず親に報告）
3. §3-1 の **Step 0〜3 を順序どおり・省略なし**で実行する。とくに:
   - 仕分け宣言のあと、**「wiki に保存してよいですか？」の明示承認を得るまで書き込まない**
   - 日記の書式（あったこと／おもったこと）を守るのは AI の仕事。親に書式の説明を求めない

このスキルと AGENTS.md が食い違って見えたら、**AGENTS.md が正しい**。手順の変更は AGENTS.md だけを編集すること。

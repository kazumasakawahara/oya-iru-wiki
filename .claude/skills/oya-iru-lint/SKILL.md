---
name: oya-iru-lint
description: oya-iru-wiki Vault の健全性チェック（lint）。点検・検査を頼まれたとき、公開・共有・エクスポートの前、lint の ERROR/WARN の意味を聞かれたときに必ず使う。
---

# oya-iru-wiki: lint（健全性チェック）

このスキルは着火装置です。**手順の正典は Vault 直下の AGENTS.md** にあり、ここには複製しません。

1. **必ず最初に `python3 scripts/okf_lint.py` を実行する。** 目視や記憶による点検から始めてはならない
2. オプションと終了コード（0=違反なし／1=WARN のみ／2=ERROR）の扱いは `AGENTS.md` **§3-3（lint）**に従う
3. ERROR は機微情報の漏出リスクである。解消するまで ingest・共有・公開に進まない

このスキルと AGENTS.md が食い違って見えたら、**AGENTS.md が正しい**。手順の変更は AGENTS.md だけを編集すること。

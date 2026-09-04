#!/usr/bin/env python3
"""
okf_lint.py — schema.md の構造ルールを機械的に検証する（oya-iru-wiki 版）

依存ゼロ（Python3 標準ライブラリのみ）。PyYAML も不要。
共通検査は同じフォルダの okf_core.py（姉妹 Vault と同一内容。正本は
oya-inai-keikaku-soudan。同一性は scripts/release.sh がハッシュで照合する）。
このファイルには**本 Vault 固有の型・語彙・検査だけ**を書く。

使い方:
    python3 scripts/okf_lint.py                 # 全チェック
    python3 scripts/okf_lint.py --gate          # 配布ゲートのみ（終了コードで判定）
    python3 scripts/okf_lint.py --allowlist     # 外部配布可能ファイル一覧を出力

終了コード:
    0 = 違反なし
    1 = WARN のみ（鮮度切れ・推奨事項。作業は止めないが確認を促す）
    2 = ERROR あり（機微情報の漏出リスク。pre-commit・起動時ゲートで止める想定）
    ※ --gate は ERROR の有無だけを返す（WARN では 0）。鮮度・凍結で commit は止めない

本 Vault 固有（PLAN.md §7-2 / docs/phase2-implementation-plan.md T4）:
    - plan / monitoring / meeting 型を持たない（keikaku-soudan 側の正本。未知型として ERROR になる）
    - koe / sentaku / fushime 型
    - sentaku: outcome 語彙・「通らなかった」の override_reason 必須（ERROR）・
      A-10 構造検査（本文2見出し。WARN）
    - fushime: occurred_on 必須・fushime_kind 語彙
    - koe: 鮮度検査対象（90日）
    - lifestage 語彙検査（あれば照合）
    - 日記凍結検査（ハッシュ台帳方式。2026-08-13 河原さん承認）
    - 原本と読み取りの対応検査（schema.md §7）

作成: 2026-08-13 / 改訂: 2026-09-04 共通部分を okf_core.py へ分離
"""

import hashlib
import json
import os
import re
import sys

import okf_core as core

VAULT = core.vault_root(__file__)
DIARY = os.path.join(VAULT, "raw", "10_日記")
FREEZE_LEDGER = os.path.join(VAULT, "scripts", "diary_freeze.json")

# 日記凍結検査のスイッチ（撤退線: WARN がうるさければ False に。
# 凍結は schema.md §0-3 の運用ルールとして残る）
DIARY_FREEZE_CHECK = True

# 後方互換の再公開
PII_PATTERNS = core.PII_PATTERNS
parse_frontmatter = core.parse_frontmatter

# --- 本 Vault 固有の型と語彙（schema.md §3）-----------------------------

VAULT_TYPES = ("koe", "sentaku", "fushime")

VALID_OUTCOME = {"尊重された", "一部尊重", "持ち越し", "通らなかった"}
VALID_FUSHIME_KIND = {"就園・就学", "進級・進学", "卒業", "サービス開始", "サービス終了",
                      "制度切替", "転居", "家族の変化", "その他"}
VALID_LIFESTAGE = {"幼児期", "学齢期", "思春期", "移行期", "成人期"}

# A-10 の構造検査: sentaku 本文に必須の2見出し（存在しなければ WARN）
SENTAKU_REQUIRED_HEADINGS = ["## 本人のようす（事実）", "## まわりの受けとめ"]

DIARY_FILE_RE = re.compile(r"^(\d{4})-(\d{2})\.md$")

# schema.md §7 原本と読み取りの分離
RAW_BINARY_EXT = {
    ".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp",
    ".tiff", ".tif", ".gif", ".bmp", ".pdf",
}


def unknown_type_hint(t):
    if t in ("plan", "monitoring", "meeting", "season"):
        return "（plan / monitoring / meeting は keikaku-soudan 側の型。本Vaultには搭載しない）"
    return ""


def check_vault_types(page, report):
    """sentaku / fushime / lifestage の本 Vault 固有検査。"""
    t, fm, r, body = page.type, page.fm, page.rel, page.body
    warns, errors = report.warns, report.errors

    # --- ★ sentaku: outcome と A-10 構造検査（schema.md §3-1）---
    if t == "sentaku":
        oc = fm.get("outcome", "")
        if not oc:
            warns.append(f"[sentaku] {r}: `outcome` がない"
                         f"（尊重された / 一部尊重 / 持ち越し / 通らなかった）")
        elif oc not in VALID_OUTCOME:
            warns.append(f"[sentaku] {r}: `outcome` が未定義の値 `{oc}`"
                         f"（尊重された / 一部尊重 / 持ち越し / 通らなかった）")
        if oc == "通らなかった" and not fm.get("override_reason"):
            errors.append(
                f"[sentaku] {r}: outcome `通らなかった` に `override_reason` がない。"
                f"本人の意思と異なる判断をした理由の記録は必須"
                f"（意思決定支援ガイドライン / purpose.md G-3）")
        for h in SENTAKU_REQUIRED_HEADINGS:
            if h not in body:
                warns.append(
                    f"[A-10] {r}: 見出し `{h}` がない。事実と受けとめの分離が"
                    f"構造で守られていない（schema.md §3-1）")

    # --- ★ fushime: 種別語彙（schema.md §3-3）-------------------
    if t == "fushime":
        fk = fm.get("fushime_kind", "")
        if not fk:
            warns.append(f"[fushime] {r}: `fushime_kind` がない")
        elif fk not in VALID_FUSHIME_KIND:
            warns.append(f"[fushime] {r}: `fushime_kind` が未定義の値 `{fk}`")

    # --- ★ lifestage 語彙（schema.md §1。あれば照合）------------
    ls = fm.get("lifestage", "")
    if ls and ls not in VALID_LIFESTAGE:
        warns.append(f"[lifestage] {r}: 未定義の値 `{ls}`"
                     f"（幼児期 / 学齢期 / 思春期 / 移行期 / 成人期）")


def check_diary_freeze(vault, report, today):
    """日記凍結検査（ハッシュ台帳方式。schema.md §0-3）。

    raw/10_日記/ 配下の YYYY-MM.md のうち「月が変わった」ファイルは凍結対象。
    凍結時点の sha256 を台帳（scripts/diary_freeze.json）に記録し、
    以後ハッシュが変わっていたら WARN で親に確認を促す。
    raw/ は git 管理外のため、この台帳が唯一の凍結記録である。
    """
    warns, infos = report.warns, report.infos
    diary = os.path.join(vault, "raw", "10_日記")
    ledger_path = os.path.join(vault, "scripts", "diary_freeze.json")
    if not DIARY_FREEZE_CHECK or not os.path.isdir(diary):
        return
    try:
        with open(ledger_path, encoding="utf-8") as f:
            ledger = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        ledger = {}

    changed = False
    for root, dirs, files in os.walk(diary):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in sorted(files):
            m = DIARY_FILE_RE.match(name)
            if not m:
                continue
            y, mo = int(m.group(1)), int(m.group(2))
            if (y, mo) >= (today.year, today.month):
                continue  # 当月以降は凍結対象外（編集可）
            path = os.path.join(root, name)
            r = os.path.relpath(path, vault)
            with open(path, "rb") as f:
                digest = hashlib.sha256(f.read()).hexdigest()
            if r not in ledger:
                ledger[r] = digest
                changed = True
                infos.append(f"[凍結] {r}: 凍結台帳に記録した（以後の変更は WARN になる）")
            elif ledger[r] != digest:
                warns.append(
                    f"[凍結] {r}: 凍結済みの日記が変更されている（schema.md §0-3）。"
                    f"意図した追記なら親に確認のうえ台帳を更新する"
                    f"（scripts/diary_freeze.json の該当エントリを削除して再実行）")

    if changed:
        try:
            with open(ledger_path, "w", encoding="utf-8") as f:
                json.dump(ledger, f, ensure_ascii=False, indent=1, sort_keys=True)
        except OSError as e:
            warns.append(f"[凍結] 台帳の書き込みに失敗: {e}")


def check_raw_readings(vault, report, today):
    """raw/20〜90 の非テキスト原本に読み取りファイルが対であるかを見る（schema.md §7）。

    raw/ は git 管理外のため、この検査はローカル実行時にのみ意味を持つ。
    取りこぼしの発見が目的であり、機微情報の漏出ではないので WARN 止まり。
    日記（raw/10_日記）は §7-2 により対象外。
    """
    warns, infos = report.warns, report.infos
    raw = os.path.join(vault, "raw")
    if not os.path.isdir(raw):
        return
    missing = 0
    orphan = 0
    for shelf in sorted(os.listdir(raw)):
        if shelf.startswith(".") or shelf.startswith("10_"):
            continue
        d = os.path.join(raw, shelf)
        if not os.path.isdir(d):
            continue
        for root, _dirs, files in os.walk(d):
            names = set(files)
            for f in sorted(files):
                if f.startswith("."):
                    continue
                rel = os.path.relpath(os.path.join(root, f), vault)
                if f.endswith(".読み取り.md"):
                    origin = f[: -len(".読み取り.md")]
                    if origin not in names:
                        warns.append(
                            f"[読み取り] {rel}: 対応する原本 `{origin}` がない"
                            "（原本のない読み取りは出所のない伝聞。schema.md §7-5）"
                        )
                        orphan += 1
                    continue
                if os.path.splitext(f)[1].lower() not in RAW_BINARY_EXT:
                    continue
                if f + ".読み取り.md" not in names:
                    warns.append(
                        f"[読み取り] {rel}: 読み取り `{f}.読み取り.md` がない（schema.md §7-3）"
                    )
                    missing += 1
    if missing:
        infos.append(f"[読み取り] 読み取り未生成の原本 {missing} 件 — 次の ingest で生成する")
    if orphan:
        infos.append(f"[読み取り] 原本のない読み取り {orphan} 件 — 原本の所在を確認する")


CONFIG = core.Config(
    types=core.BASE_TYPES + VAULT_TYPES,
    type_to_dir={**core.BASE_TYPE_TO_DIR, "koe": "koe", "sentaku": "sentaku", "fushime": "fushime"},
    person_bound_types=core.BASE_PERSON_BOUND_TYPES + VAULT_TYPES,   # pre-commit 関所2 の対象と一致
    require_person_id=VAULT_TYPES,
    date_field={"sentaku": "sentaku_date", "fushime": "occurred_on"},
    # 後見人は keikaku-soudan 互換で受理
    provided_by=("本人", "親", "家族", "園・学校", "事業所", "医療機関", "行政", "会議", "相談支援", "後見人"),
    # 「親が確認」が本Vaultの標準（「家族に確認」は姉妹版互換で受理）
    confirmed_by=("記録のみ", "本人に確認", "親が確認", "家族に確認", "支援者に確認", "実地で確認"),
    stale_after_days={**core.BASE_STALE_AFTER_DAYS, "koe": 90},   # 意思表出のしかたは成長とともに変わる
    allowlist_note="→ 意思決定支援ブリーフ等の外部共有に出せるのはこの範囲のみ",
    confirm_advice="本人・現場で確認を",
    unknown_type_hint=unknown_type_hint,
    page_check=check_vault_types,
    vault_checks=(check_diary_freeze, check_raw_readings),
)


def lint():
    rep = core.lint(VAULT, CONFIG)
    return rep.errors, rep.warns, rep.infos, rep.allowlist, rep.stats


def main():
    return core.main(VAULT, CONFIG)


if __name__ == "__main__":
    sys.exit(main())

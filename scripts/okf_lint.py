#!/usr/bin/env python3
"""
okf_lint.py — schema.md の構造ルールを機械的に検証する（oya-iru-wiki 版）

依存ゼロ（Python3 標準ライブラリのみ）。PyYAML も不要。
schema.md §0〜§6 のルールを実行可能な形にしたもの。
土台: oya-inai-keikaku-soudan/scripts/okf_lint.py（2026-08-09 版）

使い方:
    python3 scripts/okf_lint.py                 # 全チェック
    python3 scripts/okf_lint.py --gate          # 配布ゲートのみ（終了コードで判定）
    python3 scripts/okf_lint.py --allowlist     # 外部配布可能ファイル一覧を出力

終了コード:
    0 = 違反なし
    1 = WARN のみ（鮮度切れ・推奨事項。作業は止めないが確認を促す）
    2 = ERROR あり（機微情報の漏出リスク。pre-commit・起動時ゲートで止める想定）
    ※ --gate は ERROR の有無だけを返す（WARN では 0）。鮮度・凍結で commit は止めない

移植差分（PLAN.md §7-2 / docs/phase2-implementation-plan.md T4）:
    - plan / monitoring / meeting 型を除去（keikaku-soudan 側の正本。未知型として ERROR になる）
    - koe / sentaku / fushime 型を追加
    - sentaku: outcome 語彙・「通らなかった」の override_reason 必須（ERROR）・
      A-10 構造検査（本文2見出し。WARN）
    - fushime: occurred_on 必須・fushime_kind 語彙
    - koe: 鮮度検査対象（90日）
    - lifestage 語彙検査（あれば照合）
    - 日記凍結検査（ハッシュ台帳方式。2026-08-13 河原さん承認）

作成: 2026-08-13
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from collections import Counter

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(VAULT, "wiki")
DIARY = os.path.join(VAULT, "raw", "10_日記")
FREEZE_LEDGER = os.path.join(VAULT, "scripts", "diary_freeze.json")

# 日記凍結検査のスイッチ（撤退線: WARN がうるさければ False に。
# 凍結は schema.md §0-3 の運用ルールとして残る）
DIARY_FREEZE_CHECK = True

# --- schema.md §1 / §5 -------------------------------------------------

VALID_TYPES = {
    "person", "trial", "protocol", "trigger", "concept", "entity",
    "ecomap", "sensitive", "public-system", "procedure", "query", "review",
    "koe", "sentaku", "fushime",
}

TYPE_TO_DIR = {
    "person": "persons", "trial": "trials", "protocol": "protocols",
    "trigger": "triggers", "concept": "concepts", "entity": "entities",
    "ecomap": "ecomaps", "sensitive": "sensitive",
    "public-system": "public-systems", "procedure": "procedures",
    "query": "queries", "review": "reviews",
    "koe": "koe", "sentaku": "sentaku", "fushime": "fushime",
}

VALID_STATUS = {"draft", "active", "review", "stale"}
VALID_SENSITIVITY = {"public", "internal", "sensitive", "restricted"}
SENSITIVITY_ORDER = {"public": 0, "internal": 1, "sensitive": 2, "restricted": 3}

REQUIRED_FIELDS = ["type", "created", "updated", "sources", "tags", "status", "sensitivity"]

# 個人に紐づく型。public を名乗ってはならない（pre-commit 関所2 の対象と一致）
PERSON_BOUND_TYPES = {"person", "trial", "protocol", "trigger", "ecomap", "sensitive",
                      "koe", "sentaku", "fushime"}

# person_id が必須の型
REQUIRE_PERSON_ID = {"koe", "sentaku", "fushime"}

# 型ごとに必須の日付フィールド（出来事型。時系列を追うため）
DATE_FIELD = {"sentaku": "sentaku_date", "fushime": "occurred_on"}

# --- 新設3型の語彙（schema.md §3）---------------------------------------

VALID_OUTCOME = {"尊重された", "一部尊重", "持ち越し", "通らなかった"}
VALID_FUSHIME_KIND = {"就園・就学", "進級・進学", "卒業", "サービス開始", "サービス終了",
                      "制度切替", "転居", "家族の変化", "その他"}
VALID_LIFESTAGE = {"幼児期", "学齢期", "思春期", "移行期", "成人期"}

# A-10 の構造検査: sentaku 本文に必須の2見出し（存在しなければ WARN）
SENTAKU_REQUIRED_HEADINGS = ["## 本人のようす（事実）", "## まわりの受けとめ"]

# --- 出所と宛先（schema.md §1）------------------------------------------

VALID_PROVIDED_BY = {"本人", "親", "家族", "園・学校", "事業所", "医療機関", "行政",
                     "会議", "相談支援", "後見人"}  # 後見人は keikaku-soudan 互換で受理
VALID_SHARE_SCOPE = {"team", "consent-required", "origin-only"}

# --- 鮮度（schema.md §6）------------------------------------------------

STALE_AFTER_DAYS = {
    "person": 90,      # 現況（生活・園学校等）は変わる
    "koe": 90,         # 意思表出のしかたは成長とともに変わる（バイブルの心臓）
    "protocol": 90,    # 「今も機能している手順」でなければ手順の意味がない
    "trigger": 180,    # 好き・苦手のきっかけも入れ替わる
    "sensitive": 180,  # 半年ごとに読み直す
    "ecomap": 30,      # 月次スナップショットが前提
}

# 確認の手段。「親が確認」が本Vaultの標準（「家族に確認」は姉妹版互換で受理）
VALID_CONFIRMED_BY = {"記録のみ", "本人に確認", "親が確認", "家族に確認",
                      "支援者に確認", "実地で確認"}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SOURCE_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")
DIARY_FILE_RE = re.compile(r"^(\d{4})-(\d{2})\.md$")

# --- PII パターン（wiki/ に出現してはならないもの。実名・個人到達情報は raw/ のみ）

_PERSONAL_MAIL = (
    r"gmail\.com|yahoo\.(co\.jp|com)|outlook\.com|hotmail\.(com|co\.jp)|"
    r"icloud\.com|me\.com|live\.jp|docomo\.ne\.jp|ezweb\.ne\.jp|au\.com|"
    r"softbank\.ne\.jp|i\.softbank\.jp|ymobile\.ne\.jp|nifty\.com|excite\.co\.jp"
)

PII_PATTERNS = [
    (r"\b0[789]0-?\d{4}-?\d{4}\b", "携帯番号（個人に到達する）"),
    (r"\b[\w.+-]+@(" + _PERSONAL_MAIL + r")\b", "個人メール（キャリア・フリーメール）"),
    (r"(19|20)\d{2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日\s*生", "生年月日（日まで）"),
    (r"療育手帳\s*(番号|No\.?)\s*[:：]?\s*[\dA-Z-]{4,}", "手帳番号"),
    (r"受給者証\s*(番号|No\.?)\s*[:：]?\s*[\d-]{6,}", "受給者証番号"),
    (r"\d{1,4}-\d{1,4}-\d{1,4}\s*(番地|号室)", "住居表示"),
    (r"[一-鿿゠-ヿ]{2,10}(マンション|アパート|ハイツ|コーポ)\s*\d{1,4}\s*号?室?", "集合住宅の部屋番号"),
]


def parse_frontmatter(path):
    """先頭の --- ブロックを浅くパースする。ネストは値をそのまま文字列で返す。"""
    fm, body_start = {}, 0
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return None, "", f"読み取り失敗: {e}"

    if not lines or lines[0].strip() != "---":
        return None, "".join(lines), "フロントマターがない"

    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body_start = i + 1
            break
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip().strip('"').strip("'")
            fm[key] = val
        elif line.startswith(("  -", "- ", "\t-")):
            # リスト項目。直前のキーに要素があることだけ記録する
            if fm:
                last = list(fm.keys())[-1]
                if fm[last] == "":
                    fm[last] = "[list]"
    else:
        return None, "".join(lines), "フロントマターが閉じていない"

    return fm, "".join(lines[body_start:]), None


def rel(path):
    return os.path.relpath(path, VAULT)


def check_diary_freeze(warns, infos, today):
    """日記凍結検査（ハッシュ台帳方式。schema.md §0-3）。

    raw/10_日記/ 配下の YYYY-MM.md のうち「月が変わった」ファイルは凍結対象。
    凍結時点の sha256 を台帳（scripts/diary_freeze.json）に記録し、
    以後ハッシュが変わっていたら WARN で親に確認を促す。
    raw/ は git 管理外のため、この台帳が唯一の凍結記録である。
    """
    if not DIARY_FREEZE_CHECK or not os.path.isdir(DIARY):
        return
    try:
        with open(FREEZE_LEDGER, encoding="utf-8") as f:
            ledger = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        ledger = {}

    changed = False
    for root, dirs, files in os.walk(DIARY):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in sorted(files):
            m = DIARY_FILE_RE.match(name)
            if not m:
                continue
            y, mo = int(m.group(1)), int(m.group(2))
            if (y, mo) >= (today.year, today.month):
                continue  # 当月以降は凍結対象外（編集可）
            path = os.path.join(root, name)
            r = rel(path)
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
            with open(FREEZE_LEDGER, "w", encoding="utf-8") as f:
                json.dump(ledger, f, ensure_ascii=False, indent=1, sort_keys=True)
        except OSError as e:
            warns.append(f"[凍結] 台帳の書き込みに失敗: {e}")


def lint():
    errors, warns, infos = [], [], []
    allowlist = []
    stats = Counter()
    today = datetime.date.today()

    if not os.path.isdir(WIKI):
        print(f"wiki/ が見つかりません: {WIKI}", file=sys.stderr)
        return ["[致命] wiki/ が見つからない"], [], [], [], Counter()

    for root, dirs, files in os.walk(WIKI):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in sorted(files):
            if not name.endswith(".md") or name in ("index.md", "log.md"):
                continue
            path = os.path.join(root, name)
            r = rel(path)
            fm, body, err = parse_frontmatter(path)
            n_errors_before = len(errors)

            if err:
                errors.append(f"[FM] {r}: {err}")
                continue

            # --- 必須フィールド -----------------------------------------
            for field in REQUIRED_FIELDS:
                if field not in fm or fm[field] == "":
                    errors.append(f"[必須] {r}: `{field}` がない")

            t = fm.get("type", "")
            sens = fm.get("sensitivity", "")
            status = fm.get("status", "")
            stats[f"type:{t}"] += 1
            stats[f"sensitivity:{sens}"] += 1

            # --- 値の妥当性 ---------------------------------------------
            if t and t not in VALID_TYPES:
                errors.append(f"[type] {r}: 未定義の type `{t}`"
                              + ("（plan / monitoring / meeting は keikaku-soudan 側の型。"
                                 "本Vaultには搭載しない）" if t in ("plan", "monitoring", "meeting", "season") else ""))
            if sens and sens not in VALID_SENSITIVITY:
                errors.append(f"[sensitivity] {r}: 未定義の値 `{sens}`")
            if status and status not in VALID_STATUS:
                warns.append(f"[status] {r}: 未定義の値 `{status}`")

            # --- type と配置ディレクトリの一致（schema.md §5-3）---------
            if t in TYPE_TO_DIR:
                expected = TYPE_TO_DIR[t]
                parts = os.path.relpath(path, WIKI).split(os.sep)
                if parts[0] != expected:
                    errors.append(
                        f"[配置] {r}: type `{t}` は wiki/{expected}/ に置く（現在 wiki/{parts[0]}/）"
                    )

            # --- ★ 機微ゲート（本スクリプトの中核）----------------------
            # 個人に紐づく型が public を名乗るのは設計上ありえない
            if t in PERSON_BOUND_TYPES and sens == "public":
                errors.append(
                    f"[ゲート] {r}: type `{t}` は個人に紐づくため sensitivity: public にできない"
                )

            # person_id を持つページが public を名乗るのも同様
            if fm.get("person_id") and sens == "public":
                errors.append(f"[ゲート] {r}: person_id を持つが sensitivity: public になっている")

            # restricted は wiki/sensitive/restricted/ 配下のみ
            if sens == "restricted" and "sensitive/restricted" not in r.replace(os.sep, "/"):
                errors.append(f"[ゲート] {r}: restricted は wiki/sensitive/restricted/ に置く")

            # sensitive 以上は sensitive_purpose 必須
            if SENSITIVITY_ORDER.get(sens, 0) >= 2 and not fm.get("sensitive_purpose"):
                errors.append(f"[ゲート] {r}: sensitive 以上は `sensitive_purpose` の明記が必須")

            # --- ★ 新設3型の必須項目（schema.md §3）---------------------
            if t in REQUIRE_PERSON_ID and not fm.get("person_id"):
                errors.append(f"[必須] {r}: type `{t}` には `person_id` が必須")
            df = DATE_FIELD.get(t)
            if df:
                dv = fm.get(df, "")
                if not dv:
                    errors.append(f"[必須] {r}: type `{t}` には `{df}` が必須。時系列を追えない")
                elif not DATE_RE.match(dv):
                    warns.append(f"[日付] {r}: `{df}` が YYYY-MM-DD 形式でない: `{dv}`")

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

            # --- ★ 出所と宛先（schema.md §1）----------------------------
            pb = fm.get("provided_by", "")
            if pb and pb not in VALID_PROVIDED_BY:
                warns.append(
                    f"[出所] {r}: `provided_by` が未定義の値 `{pb}`"
                    f"（本人 / 親 / 家族 / 園・学校 / 事業所 / 医療機関 / 行政 / 会議 / 相談支援）")
            ss_val = fm.get("share_scope", "")
            if ss_val and ss_val not in VALID_SHARE_SCOPE:
                warns.append(
                    f"[宛先] {r}: `share_scope` が未定義の値 `{ss_val}`"
                    f"（team / consent-required / origin-only）")
            if fm.get("person_id") and not pb:
                warns.append(f"[出所] {r}: 個人に紐づくページに `provided_by` がない（新規ページから徐々に）")

            # --- ★ source_hash の形式検査（任意）------------------------
            sh = fm.get("source_hash", "")
            if sh and not SOURCE_HASH_RE.match(sh):
                warns.append(
                    f"[出所] {r}: `source_hash` が sha256 の形式（64桁の16進）でない: `{sh}`")

            # --- ★ 鮮度検査（schema.md §6）------------------------------
            # 編集した日(updated)ではなく「確かめた日(last_confirmed)」を見る。
            # last_validated は旧フィールド名の後方互換エイリアス。
            if t in STALE_AFTER_DAYS and status in ("active", "review"):
                limit = STALE_AFTER_DAYS[t]
                lc = fm.get("last_confirmed") or fm.get("last_validated")
                if not lc:
                    warns.append(
                        f"[鮮度] {r}: `last_confirmed`（最終確認日）がない。"
                        f"type `{t}` の目安は{limit}日ごとの確認")
                elif not DATE_RE.match(lc):
                    warns.append(f"[鮮度] {r}: `last_confirmed` が YYYY-MM-DD 形式でない: `{lc}`")
                else:
                    try:
                        age = (today - datetime.date.fromisoformat(lc)).days
                    except ValueError:
                        age = None
                        warns.append(f"[鮮度] {r}: `last_confirmed` が日付として不正: `{lc}`")
                    if age is not None and age > limit:
                        warns.append(
                            f"[鮮度] {r}: 最終確認から{age}日（目安 {limit}日）。"
                            f"内容がまだ正しいか、本人・現場で確認を")
            cb = fm.get("confirmed_by", "")
            if cb and cb not in VALID_CONFIRMED_BY:
                warns.append(
                    f"[確認手段] {r}: `confirmed_by` が未定義の値 `{cb}`"
                    f"（記録のみ / 本人に確認 / 親が確認 / 支援者に確認 / 実地で確認）")

            # --- PII パターン検出 ---------------------------------------
            # public / internal のみ検査。型による除外はしない。
            if SENSITIVITY_ORDER.get(sens, 0) <= 1:
                for pat, label in PII_PATTERNS:
                    if re.search(pat, body):
                        errors.append(f"[PII] {r}: {label} が本文にある（raw/ に置くべき内容）")

            # --- 外部配布ゲート -----------------------------------------
            # 外部に出してよいのは public のみ。ERROR が1件でも出たページ、
            # および share_scope: origin-only のページは無条件で除外（fail-closed）。
            if sens == "public" and status in ("active", "review") \
                    and fm.get("share_scope", "") != "origin-only" \
                    and len(errors) == n_errors_before:
                allowlist.append(r)

            # --- public-system の制度鮮度 -------------------------------
            if t == "public-system" and not fm.get("last_updated_law"):
                warns.append(f"[鮮度] {r}: public-system に `last_updated_law` がない")
            if t == "public-system":
                vo = fm.get("verified_on", "")
                if vo and DATE_RE.match(vo):
                    try:
                        vo_age = (today - datetime.date.fromisoformat(vo)).days
                        if vo_age > 365:
                            warns.append(
                                f"[鮮度] {r}: `verified_on` から{vo_age}日。制度ウォッチの"
                                f"点検漏れの可能性（docs/watchlist.md を確認）")
                    except ValueError:
                        pass
            if status == "stale":
                if fm.get("superseded_by"):
                    infos.append(f"[stale] {r} → 置き換え先: {fm['superseded_by']}")
                else:
                    infos.append(f"[stale] {r}（`superseded_by` 未記載 — どの記録に置き換わったか追えない）")

    # --- ★ 日記凍結検査（ハッシュ台帳方式。wiki/ ではなく raw/10_日記/ を見る唯一の検査）
    check_diary_freeze(warns, infos, today)

    # --- ★ 原本と読み取りの対応検査（schema.md §7。raw/20〜90 を見る）
    check_raw_readings(warns, infos)

    return errors, warns, infos, allowlist, stats


# --- schema.md §7 原本と読み取りの分離 -----------------------------------
RAW_BINARY_EXT = {
    ".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp",
    ".tiff", ".tif", ".gif", ".bmp", ".pdf",
}


def check_raw_readings(warns, infos):
    """raw/20〜90 の非テキスト原本に読み取りファイルが対であるかを見る（schema.md §7）。

    raw/ は git 管理外のため、この検査はローカル実行時にのみ意味を持つ。
    取りこぼしの発見が目的であり、機微情報の漏出ではないので WARN 止まり。
    日記（raw/10_日記）は §7-2 により対象外。
    """
    raw = os.path.join(VAULT, "raw")
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
                rel = os.path.relpath(os.path.join(root, f), VAULT)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true", help="機微ゲートの結果だけを終了コードで返す")
    ap.add_argument("--allowlist", action="store_true", help="外部配布可能ファイル一覧を出力")
    args = ap.parse_args()

    errors, warns, infos, allowlist, stats = lint()

    if args.allowlist:
        for p in allowlist:
            print(p)
        return 0

    total = sum(v for k, v in stats.items() if k.startswith("type:"))
    print(f"=== okf_lint: {total} ページを検査 ===\n")

    if errors:
        print(f"■ ERROR ({len(errors)}件) — 機微情報の漏出リスク。要修正")
        for e in errors:
            print(f"  {e}")
        print()
    if warns and not args.gate:
        print(f"■ WARN ({len(warns)}件)")
        for w in warns:
            print(f"  {w}")
        print()
    if infos and not args.gate:
        print(f"■ INFO ({len(infos)}件)")
        for i in infos:
            print(f"  {i}")
        print()

    if not args.gate:
        print("■ 内訳")
        for k in sorted(stats):
            print(f"  {k}: {stats[k]}")
        print(f"\n■ 外部配布可能（sensitivity: public かつ active/review）: {len(allowlist)} 件")
        print("  → 意思決定支援ブリーフ等の外部共有に出せるのはこの範囲のみ")

    if errors:
        return 2
    if args.gate:
        # ゲートは機微情報（ERROR）だけを見る。鮮度・凍結等の WARN で
        # commit や起動時ゲートを止めない（schema.md §6-4）
        return 0
    if warns:
        return 1
    print("\n違反なし。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

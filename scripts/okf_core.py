#!/usr/bin/env python3
"""
okf_core.py — OKF 共通検査（姉妹 Vault 共有部分）

依存ゼロ（Python3 標準ライブラリのみ）。PyYAML も不要。

正本は oya-inai-keikaku-soudan/scripts/okf_core.py。姉妹版（oya-iru-wiki）は
このファイルを**同一内容で**コピーして持つ。同一性は各 Vault の scripts/release.sh が
sha256 で照合する（記憶ではなく検査に置き換える）。**Vault 固有の型・語彙・検査を
このファイルに書かない。** それらは各 Vault の okf_lint.py が Config で注入する。

ここにあるもの（両 Vault で同じ意味を持つ検査）:
    - フロントマターの浅いパース
    - 必須7項目 / type・status・sensitivity の定義域 / type と配置ディレクトリの一致
    - 機微ゲート（個人紐づけ型の public 禁止・person_id×public・restricted の配置・
      sensitive_purpose 必須）
    - person_id 必須型・日付必須型（型の集合は Config）
    - 出所と宛先（provided_by / share_scope。語彙は Config）
    - source_hash の形式
    - 鮮度（last_confirmed / last_validated 互換・型別の目安日数・confirmed_by 語彙。
      valid_until が書かれた事実は対象外）
    - 時点の2軸（valid_from / valid_until / superseded_by の構造矛盾は ERROR、
      contradicts で指されたページの valid_until 未記入は WARN。schema-common.md）
    - PII パターン（判別軸は「型」ではなく「到達先」）
    - 外部配布 allowlist（fail-closed・origin-only 除外）
    - public-system の制度鮮度 / stale の superseded_by
    - CLI（--gate / --allowlist と終了コード）

終了コード:
    0 = 違反なし
    1 = WARN のみ（鮮度切れ・推奨事項。作業は止めないが確認を促す）
    2 = ERROR あり（機微情報の漏出リスク・構造矛盾。pre-commit・起動時ゲートで止める想定）
    ※ --gate は ERROR の有無だけを返す（WARN では 0）。鮮度で commit は止めない

作成: 2026-09-04 共通基盤一本化 Step 1（docs/phase-common-implementation-plan.md）。
改訂: 2026-09-04 柱2 Step 1 時点の2軸（docs/phase-common-2-implementation-plan.md §4-3）。
土台: oya-inai-keikaku-soudan/scripts/okf_lint.py（2026-08-11 版）と
oya-iru-wiki/scripts/okf_lint.py（2026-08-14 版）の共通部分。
"""

import argparse
import datetime
import os
import re
import sys
from collections import Counter

# --- 両 Vault で同一の宣言（schema.md §1 / §3 / §5 / §6）----------------

VALID_STATUS = ("draft", "active", "review", "stale")
VALID_SENSITIVITY = ("public", "internal", "sensitive", "restricted")
SENSITIVITY_ORDER = {"public": 0, "internal": 1, "sensitive": 2, "restricted": 3}

REQUIRED_FIELDS = ("type", "created", "updated", "sources", "tags", "status", "sensitivity")

# 継承12型。各 Vault はこれに固有の型を足す
BASE_TYPES = ("person", "trial", "protocol", "trigger", "concept", "entity",
              "ecomap", "sensitive", "public-system", "procedure", "query", "review")

BASE_TYPE_TO_DIR = {
    "person": "persons", "trial": "trials", "protocol": "protocols",
    "trigger": "triggers", "concept": "concepts", "entity": "entities",
    "ecomap": "ecomaps", "sensitive": "sensitive",
    "public-system": "public-systems", "procedure": "procedures",
    "query": "queries", "review": "reviews",
}

# 個人に紐づく型。public を名乗ってはならない
BASE_PERSON_BOUND_TYPES = ("person", "trial", "protocol", "trigger", "ecomap", "sensitive")

VALID_SHARE_SCOPE = ("team", "consent-required", "origin-only")

# 鮮度の目安（schema.md §6）。現在の状態を主張する型のみ。
# 出来事の記録（trial / query / 各 Vault の出来事型）は対象外
BASE_STALE_AFTER_DAYS = {
    "person": 90,      # 現況は変わる
    "protocol": 90,    # 「まだ機能しているか」を3ヶ月ごとに確認
    "trigger": 180,    # 本人の状態は変化する
    "sensitive": 180,  # 半年ごとに読み直す
    "ecomap": 30,      # 月次スナップショットが前提
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SOURCE_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")

# --- PII パターン（wiki/ に出現してはならないもの。実名・個人到達情報は raw/ のみ）
#
# 判別軸は「型」ではなく「到達先」。公的機関の代表番号・相談窓口は
# 緊急時に必要な情報なので検出しない。個人に到達するものだけを検出する。
# これにより entity ページに個人の携帯番号が混入しても検出できる。

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


class Config:
    """Vault が注入する型・語彙・追加検査。

    types / type_to_dir / person_bound_types / require_person_id / date_field:
        型の集合。BASE_* に Vault 固有の型を足して渡す
    provided_by / confirmed_by:
        語彙（順序つき。エラー文の一覧表示にそのまま使う）
    stale_after_days:
        鮮度の目安。BASE_STALE_AFTER_DAYS に固有型を足して渡す
    allowlist_note:
        --allowlist の件数の下に出す1行（外部に出してよい先の説明）
    confirm_advice:
        鮮度超過 WARN の末尾（誰に確かめるか）
    unknown_type_hint(t) -> str:
        未定義 type のエラー文に付ける補足（姉妹版の型を案内する等）
    page_check(page, report):
        1ページごとの Vault 固有検査。機微ゲートの直後に呼ばれる
    vault_checks: [fn(vault, report, today)]:
        wiki/ 走査後に呼ぶ Vault 全体の検査（raw/ を見る検査など）
    """

    def __init__(self, *, types, type_to_dir, person_bound_types, require_person_id,
                 date_field, provided_by, confirmed_by, stale_after_days, allowlist_note,
                 confirm_advice="本人・家族・現場で確認を", unknown_type_hint=None,
                 page_check=None, vault_checks=()):
        self.types = tuple(types)
        self.type_to_dir = dict(type_to_dir)
        self.person_bound_types = tuple(person_bound_types)
        self.require_person_id = tuple(require_person_id)
        self.date_field = dict(date_field)
        self.provided_by = tuple(provided_by)
        self.confirmed_by = tuple(confirmed_by)
        self.stale_after_days = dict(stale_after_days)
        self.allowlist_note = allowlist_note
        self.confirm_advice = confirm_advice
        self.unknown_type_hint = unknown_type_hint or (lambda t: "")
        self.page_check = page_check or (lambda page, report: None)
        self.vault_checks = tuple(vault_checks)


class Page:
    """検査中の1ページ。page_check に渡す。lists はフロントマターのリスト値の要素。"""

    def __init__(self, path, rel, fm, body, lists=None):
        self.path = path
        self.rel = rel
        self.fm = fm
        self.body = body
        self.lists = lists or {}
        self.type = fm.get("type", "")
        self.sens = fm.get("sensitivity", "")
        self.status = fm.get("status", "")


class Report:
    def __init__(self):
        self.errors, self.warns, self.infos = [], [], []
        self.allowlist = []
        self.stats = Counter()


def vault_root(script_file):
    """scripts/xxx.py から Vault ルートを求める。"""
    return os.path.dirname(os.path.dirname(os.path.abspath(script_file)))


def parse_frontmatter(path):
    """先頭の --- ブロックを浅くパースする。ネストは値をそのまま文字列で返す。"""
    fm, body, err, _ = _parse_frontmatter_full(path)
    return fm, body, err


def _parse_frontmatter_full(path):
    """parse_frontmatter に加えて、リスト値の要素を {key: [items]} で返す。

    fm の値は従来どおり（リストは "[list]" のまま）。要素は confirms / contradicts の
    指し先を辿る検査（§6-3・時点の2軸）だけが使う。
    """
    fm, lists, body_start, last = {}, {}, 0, None
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return None, "", f"読み取り失敗: {e}", {}

    if not lines or lines[0].strip() != "---":
        return None, "".join(lines), "フロントマターがない", {}

    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body_start = i + 1
            break
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
        if m:
            key, raw = m.group(1), m.group(2).strip()
            val = raw.strip('"').strip("'")
            fm[key] = val
            last = key
            # インライン配列 `[a, b]`。空配列 `[]` は要素なし
            if raw.startswith("[") and raw.endswith("]") and raw[1:-1].strip():
                lists[key] = [x.strip().strip('"').strip("'") for x in raw[1:-1].split(",")]
        elif line.startswith(("  -", "- ", "\t-")):
            # リスト項目。直前のキーに要素があることを記録し、要素も控える
            if last is not None:
                if fm[last] == "":
                    fm[last] = "[list]"
                lists.setdefault(last, []).append(line.split("-", 1)[1].strip().strip('"').strip("'"))
    else:
        return None, "".join(lines), "フロントマターが閉じていない", {}

    return fm, "".join(lines[body_start:]), None, lists


_LINK_RE = re.compile(r"^\[\[(.+?)\]\]$")


def _link_basename(value):
    """`[[wiki/protocols/PR_x|別名]]` → `PR_x`。wikilink でなければそのまま basename。"""
    m = _LINK_RE.match(value.strip())
    inner = m.group(1) if m else value.strip()
    inner = inner.split("|", 1)[0].split("#", 1)[0].strip()
    base = inner.rsplit("/", 1)[-1]
    return base[:-3] if base.endswith(".md") else base


def lint(vault, config, today=None):
    """wiki/ を走査して Report を返す。"""
    wiki = os.path.join(vault, "wiki")
    rep = Report()
    today = today or datetime.date.today()
    errors, warns, infos = rep.errors, rep.warns, rep.infos

    if not os.path.isdir(wiki):
        print(f"wiki/ が見つかりません: {wiki}", file=sys.stderr)
        errors.append("[致命] wiki/ が見つからない")
        return rep

    # 先に全ページを読む。ページ間の参照（superseded_by の指し先・contradicts で
    # 指されたページ）を検査するため。走査順は従来と同じ
    entries, names, contradicted = [], {}, set()
    for root, dirs, files in os.walk(wiki):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in sorted(files):
            if not name.endswith(".md") or name in ("index.md", "log.md"):
                continue
            path = os.path.join(root, name)
            r = os.path.relpath(path, vault)
            fm, body, err, lists = _parse_frontmatter_full(path)
            entries.append((path, r, fm, body, err, lists))
            names.setdefault(name[:-3], []).append(r)
    for _, _, fm, _, err, lists in entries:
        if not err:
            for v in lists.get("contradicts", []):
                contradicted.update(names.get(_link_basename(v), []))

    for path, r, fm, body, err, lists in entries:
        n_errors_before = len(errors)

        if err:
            errors.append(f"[FM] {r}: {err}")
            continue

        page = Page(path, r, fm, body, lists)
        t, sens, status = page.type, page.sens, page.status

        # --- 必須フィールド -----------------------------------------
        for field in REQUIRED_FIELDS:
            if field not in fm or fm[field] == "":
                errors.append(f"[必須] {r}: `{field}` がない")

        rep.stats[f"type:{t}"] += 1
        rep.stats[f"sensitivity:{sens}"] += 1

        # --- 値の妥当性 ---------------------------------------------
        if t and t not in config.types:
            errors.append(f"[type] {r}: 未定義の type `{t}`" + config.unknown_type_hint(t))
        if sens and sens not in VALID_SENSITIVITY:
            errors.append(f"[sensitivity] {r}: 未定義の値 `{sens}`")
        if status and status not in VALID_STATUS:
            warns.append(f"[status] {r}: 未定義の値 `{status}`")

        # --- type と配置ディレクトリの一致（schema.md §5）-----------
        if t in config.type_to_dir:
            expected = config.type_to_dir[t]
            parts = os.path.relpath(path, wiki).split(os.sep)
            if parts[0] != expected:
                errors.append(
                    f"[配置] {r}: type `{t}` は wiki/{expected}/ に置く（現在 wiki/{parts[0]}/）"
                )

        # --- ★ 機微ゲート（本スクリプトの中核）----------------------
        # 個人に紐づく型が public を名乗るのは設計上ありえない
        if t in config.person_bound_types and sens == "public":
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

        # --- ★ Vault 固有の検査 -------------------------------------
        config.page_check(page, rep)

        # --- ★ person_id 必須型・日付必須型（型の集合は Config）------
        if t in config.require_person_id and not fm.get("person_id"):
            errors.append(f"[必須] {r}: type `{t}` には `person_id` が必須")
        df = config.date_field.get(t)
        if df:
            dv = fm.get(df, "")
            if not dv:
                errors.append(f"[必須] {r}: type `{t}` には `{df}` が必須。時系列を追えない")
            elif not DATE_RE.match(dv):
                warns.append(f"[日付] {r}: `{df}` が YYYY-MM-DD 形式でない: `{dv}`")

        # --- ★ 出所と宛先（schema.md §1・§7）------------------------
        pb = fm.get("provided_by", "")
        if pb and pb not in config.provided_by:
            warns.append(
                f"[出所] {r}: `provided_by` が未定義の値 `{pb}`"
                f"（{' / '.join(config.provided_by)}）")
        ss_val = fm.get("share_scope", "")
        if ss_val and ss_val not in VALID_SHARE_SCOPE:
            warns.append(
                f"[宛先] {r}: `share_scope` が未定義の値 `{ss_val}`"
                f"（{' / '.join(VALID_SHARE_SCOPE)}）")
        if (fm.get("person_id") or fm.get("person_ids")) and not pb:
            warns.append(f"[出所] {r}: 個人に紐づくページに `provided_by` がない（新規ページから徐々に）")

        # --- ★ source_hash の形式検査（schema.md §1。任意）----------
        sh = fm.get("source_hash", "")
        if sh and not SOURCE_HASH_RE.match(sh):
            warns.append(
                f"[出所] {r}: `source_hash` が sha256 の形式（64桁の16進）でない: `{sh}`")

        # --- ★ 鮮度検査（schema.md §6）------------------------------
        # 編集した日(updated)ではなく「確かめた日(last_confirmed)」を見る。
        # last_validated は旧フィールド名の後方互換エイリアス。
        # valid_until が書かれた事実（終了した事実）は鮮度を問わない（§6・時点の2軸）
        if t in config.stale_after_days and status in ("active", "review") \
                and not fm.get("valid_until"):
            limit = config.stale_after_days[t]
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
                        f"内容がまだ正しいか、{config.confirm_advice}")
        cb = fm.get("confirmed_by", "")
        if cb and cb not in config.confirmed_by:
            warns.append(
                f"[確認手段] {r}: `confirmed_by` が未定義の値 `{cb}`"
                f"（{' / '.join(config.confirmed_by)}）")

        # --- ★ 時点の2軸（schema-common.md。事実時間 valid_from / valid_until）--
        # 欠落は何も出さない（任意）。矛盾は構造矛盾として ERROR。
        # 対象は現在の主張型（= stale_after_days を持つ型）。出来事型の発生日は
        # 検査しない（計画の交付日など将来日付が正常のため）
        vf, vu = fm.get("valid_from", ""), fm.get("valid_until", "")
        for fld, val in (("valid_from", vf), ("valid_until", vu)):
            if val and not DATE_RE.match(val):
                warns.append(f"[日付] {r}: `{fld}` が YYYY-MM-DD 形式でない: `{val}`")
        if t in config.stale_after_days:
            if vf and vu and DATE_RE.match(vf) and DATE_RE.match(vu) and vf > vu:
                errors.append(f"[時点] {r}: valid_from が valid_until より後（{vf} > {vu}）")
            cr = fm.get("created", "")
            if vf and DATE_RE.match(vf) and DATE_RE.match(cr) and vf > cr:
                errors.append(
                    f"[時点] {r}: valid_from が created より後（{vf} > {cr}）。"
                    f"記録より先に成立していない事実は書けない")
            if vu and status == "active":
                errors.append(
                    f"[時点] {r}: valid_until があるのに status が active。"
                    f"終了した事実は review か stale に")
            if vu and not fm.get("superseded_by") and not fm.get("valid_until_reason"):
                errors.append(
                    f"[時点] {r}: valid_until があるのに `superseded_by` も "
                    f"`valid_until_reason` もない。なぜ終わったかを1行残す")
            if r in contradicted and not vu:
                warns.append(
                    f"[時点] {r}: contradicts で指されているが valid_until が空。"
                    f"もう当てはまらないなら終了日を裁定して書く")
        sb = fm.get("superseded_by", "")
        if sb:
            if not names.get(_link_basename(sb)):
                errors.append(f"[時点] {r}: superseded_by の指し先が存在しない: {sb}")
            if status != "stale":
                errors.append(
                    f"[時点] {r}: superseded_by があるのに status が stale でない（{status}）")

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
            rep.allowlist.append(r)

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

    # --- ★ Vault 全体の検査（raw/ を見る検査など。Vault 固有）------------
    for check in config.vault_checks:
        check(vault, rep, today)

    return rep


def main(vault, config, argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true", help="機微ゲートの結果だけを終了コードで返す")
    ap.add_argument("--allowlist", action="store_true", help="外部配布可能ファイル一覧を出力")
    args = ap.parse_args(argv)

    rep = lint(vault, config)
    errors, warns, infos, allowlist, stats = rep.errors, rep.warns, rep.infos, rep.allowlist, rep.stats

    if args.allowlist:
        for p in allowlist:
            print(p)
        return 0

    total = sum(v for k, v in stats.items() if k.startswith("type:"))
    print(f"=== okf_lint: {total} ページを検査 ===\n")

    if errors:
        print(f"■ ERROR ({len(errors)}件) — 機微情報の漏出リスク・構造矛盾。要修正")
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
        print(f"  {config.allowlist_note}")

    if errors:
        return 2
    if args.gate:
        # ゲートは機微情報（ERROR）だけを見る。鮮度等の WARN で
        # commit や起動時ゲートを止めない（schema.md §6）
        return 0
    if warns:
        return 1
    print("\n違反なし。")
    return 0

#!/usr/bin/env python3
"""
test_okf_core.py — okf_core.py（姉妹 Vault 共通検査）の回帰テスト

依存ゼロ。一時ディレクトリに合成 Vault を組み立て、継承12型だけの最小 Config で
okf_core.lint / okf_core.main をプロセス内で走らせる。Vault 固有の型・語彙は
使わない（それらは各 Vault の test_okf_lint.py が担保する）。

本ファイルは okf_core.py と同じく両 Vault で同一内容。正本は oya-inai-keikaku-soudan。

使い方:
    python3 scripts/test_okf_core.py

担保すること:
    - 公的機関の連絡先を誤検出せず、個人への到達経路を検出する（判別軸は「到達先」）
    - 機微ゲート（public 偽装・restricted の配置・sensitive_purpose・配置違反）
    - allowlist が fail-closed（ERROR ページ・origin-only を載せない）
    - person_id 必須型・日付必須型・日付書式（Config で注入した型に効く）
    - 出所と宛先の語彙、source_hash の形式
    - 鮮度（欠落・超過・不正な確認手段・last_validated エイリアス）
    - 時点の2軸（valid_from / valid_until の矛盾は ERROR、contradicts で指された
      ページの valid_until 未記入は WARN、終了した事実は鮮度を問わない）
    - 終了コード（ERROR=2 / WARN のみ=1 / --gate は WARN で 0 / 空 Vault は 0）
    - page_check / vault_checks / unknown_type_hint のフックが呼ばれる
"""

import contextlib
import io
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import okf_core as core  # noqa: E402

FM = """---
type: {type}
created: 2026-09-04
updated: 2026-09-04
sources:
  - "[[raw/test]]"
tags:
  - test
status: active
sensitivity: {sens}
{extra}---
"""


def page(type_, sens, body, extra=""):
    return FM.format(type=type_, sens=sens, extra=extra) + body + "\n"


# 継承12型だけの最小 Config。event 型（日付必須）として trial に trial_date を課してみる
def make_config(**over):
    base = dict(
        types=core.BASE_TYPES,
        type_to_dir=core.BASE_TYPE_TO_DIR,
        person_bound_types=core.BASE_PERSON_BOUND_TYPES,
        require_person_id=("trial",),
        date_field={"trial": "trial_date"},
        provided_by=("本人", "家族", "事業所"),
        confirmed_by=("記録のみ", "本人に確認", "実地で確認"),
        stale_after_days=core.BASE_STALE_AFTER_DAYS,
        allowlist_note="→ テスト",
    )
    base.update(over)
    return core.Config(**base)


# (相対パス, 内容, そのページで検出されるべきラベルの集合)
CASES = [
    # --- 検出してはならない（公的機関の連絡先）---
    ("wiki/entities/E_公的機関.md",
     page("entity", "public",
          "北九州市障害者基幹相談支援センター 093-861-3045（24時間）。\n"
          "問い合わせ info@city.kitakyushu.lg.jp"),
     set()),
    ("wiki/procedures/PC_相談窓口フロー.md",
     page("procedure", "public", "緊急時はワンストップ支援センター 093-582-2424 へ連絡する。"),
     set()),
    # --- 検出しなければならない（個人への到達経路）---
    ("wiki/entities/E_個人混入.md",
     page("entity", "public", "担当者の携帯 090-1234-5678。連絡は taro@gmail.com へ。"),
     {"携帯番号", "個人メール"}),
    ("wiki/procedures/PC_個人混入.md",
     page("procedure", "internal", "本人の携帯 080-9999-0000。サンシャインマンション 305号室。"),
     {"携帯番号", "集合住宅の部屋番号"}),
    ("wiki/concepts/C_生年月日混入.md",
     page("concept", "public", "対象者は1980年5月3日生まれ。"),
     {"生年月日"}),
    # --- 機微ゲート ---
    ("wiki/persons/P_001_public偽装.md",
     page("person", "public", "本文", extra='person_id: "P_001"\n'),
     {"個人に紐づくため", "person_id を持つが"}),
    ("wiki/sensitive/SE_purpose欠落.md",
     page("sensitive", "restricted", "本文"),
     {"restricted は", "sensitive_purpose"}),
    ("wiki/persons/T_配置違反.md",
     page("trial", "internal", "本文",
          extra='person_id: "P_001"\ntrial_date: 2026-01-01\nprovided_by: "家族"\n'),
     {"wiki/trials/ に置く"}),
    ("wiki/concepts/X_未定義型.md",
     page("encounter", "internal", "本文"),
     {"未定義の type", "HINT"}),
    # --- person_id 必須型・日付必須型（Config で注入）---
    ("wiki/trials/T_正常.md",
     page("trial", "internal", "本文",
          extra='person_id: "P_001"\ntrial_date: 2020-01-01\nprovided_by: "家族"\n'),
     set()),
    ("wiki/trials/T_id欠落.md",
     page("trial", "internal", "本文", extra="trial_date: 2026-01-01\n"),
     {"person_id"}),
    ("wiki/trials/T_日付欠落.md",
     page("trial", "internal", "本文", extra='person_id: "P_001"\nprovided_by: "家族"\n'),
     {"trial_date"}),
    ("wiki/trials/T_日付書式.md",
     page("trial", "internal", "本文",
          extra='person_id: "P_001"\ntrial_date: 2026/01/01\nprovided_by: "家族"\n'),
     {"YYYY-MM-DD 形式でない"}),
    # --- 鮮度 ---
    ("wiki/triggers/TG_確認日なし.md",
     page("trigger", "internal", "本文"),
     {"last_confirmed"}),
    ("wiki/protocols/PR_確認超過.md",
     page("protocol", "internal", "本文",
          extra='last_confirmed: 2020-01-01\nconfirmed_by: "実地で確認"\n'),
     {"最終確認から"}),
    ("wiki/protocols/PR_旧フィールド.md",
     page("protocol", "internal", "本文", extra="last_validated: 2999-01-01\n"),
     set()),
    ("wiki/protocols/PR_確認手段不正.md",
     page("protocol", "internal", "本文",
          extra='last_confirmed: 2999-01-01\nconfirmed_by: "たぶん大丈夫"\n'),
     {"confirmed_by"}),
    # --- 出所と宛先 ---
    ("wiki/protocols/PR_出所不正.md",
     page("protocol", "internal", "本文",
          extra='last_confirmed: 2999-01-01\nprovided_by: "知人"\n'),
     {"provided_by"}),
    ("wiki/protocols/PR_宛先不正.md",
     page("protocol", "internal", "本文",
          extra='last_confirmed: 2999-01-01\nshare_scope: "everyone"\n'),
     {"share_scope"}),
    ("wiki/protocols/PR_出所なし.md",
     page("protocol", "internal", "本文",
          extra='person_id: "P_001"\nlast_confirmed: 2999-01-01\n'),
     {"provided_by"}),
    ("wiki/concepts/C_共有不可.md",
     page("concept", "public", "本文", extra="share_scope: origin-only\n"),
     set()),
    # --- source_hash（任意）---
    ("wiki/concepts/C_hash正常.md",
     page("concept", "internal", "本文", extra="source_hash: " + "a1b2" * 16 + "\n"),
     set()),
    ("wiki/concepts/C_hash不正.md",
     page("concept", "internal", "本文", extra="source_hash: abc123\n"),
     {"source_hash"}),
    # --- public-system / stale ---
    ("wiki/public-systems/PS_法改正日なし.md",
     page("public-system", "public", "本文"),
     {"last_updated_law"}),
    ("wiki/concepts/C_stale.md",
     page("concept", "internal", "本文").replace("status: active", "status: stale"),
     {"superseded_by"}),
    # --- 時点の2軸（valid_from / valid_until / superseded_by。柱2）---
    ("wiki/protocols/PR_2軸正常.md",
     page("protocol", "internal", "本文",
          extra="valid_from: 2026-01-01\nlast_confirmed: 2999-01-01\n"),
     set()),
    ("wiki/protocols/PR_期間逆転.md",
     page("protocol", "internal", "本文",
          extra="valid_from: 2026-05-01\nvalid_until: 2026-04-01\n"
                'superseded_by: "[[PR_確認超過]]"\n').replace("status: active", "status: stale"),
     {"valid_from が valid_until より後"}),
    ("wiki/protocols/PR_始点が記録日より後.md",
     page("protocol", "internal", "本文",
          extra="valid_from: 2027-01-01\nlast_confirmed: 2999-01-01\n"),
     {"valid_from が created より後"}),
    ("wiki/protocols/PR_終了なのにactive.md",
     page("protocol", "internal", "本文",
          extra='valid_until: 2026-01-01\nvalid_until_reason: "GH 転居"\n'),
     {"status が active"}),
    ("wiki/protocols/PR_終了理由なし.md",
     page("protocol", "internal", "本文",
          extra="valid_until: 2026-01-01\n").replace("status: active", "status: stale"),
     {"valid_until_reason"}),
    ("wiki/protocols/PR_置き換え先不在.md",
     page("protocol", "internal", "本文",
          extra='superseded_by: "[[PR_存在しない]]"\n').replace("status: active", "status: stale"),
     {"superseded_by の指し先"}),
    ("wiki/concepts/C_置き換え先ありでactive.md",
     page("concept", "internal", "本文", extra='superseded_by: "[[PR_確認超過]]"\n'),
     {"stale でない"}),
    ("wiki/protocols/PR_2軸書式.md",
     page("protocol", "internal", "本文",
          extra="valid_from: 2026/01/01\nlast_confirmed: 2999-01-01\n"),
     {"YYYY-MM-DD 形式でない"}),
    # 終了した事実は鮮度を問わない（valid_until があれば staleAfter 超過でも WARN しない）
    ("wiki/protocols/PR_終了済みは鮮度不問.md",
     page("protocol", "internal", "本文",
          extra='valid_until: 2020-01-01\nvalid_until_reason: "GH 転居"\n'
                "last_confirmed: 2020-01-01\n").replace("status: active", "status: review"),
     set()),
    # contradicts で指された現在の主張型は valid_until を書く契機（WARN）
    ("wiki/triggers/TG_否定された.md",
     page("trigger", "internal", "本文", extra="last_confirmed: 2999-01-01\n"),
     {"contradicts で指されている"}),
    ("wiki/trials/T_否定する.md",
     page("trial", "internal", "本文",
          extra='person_id: "P_001"\ntrial_date: 2026-01-01\nprovided_by: "家族"\n'
                "contradicts:\n  - \"[[TG_否定された]]\"\n"),
     set()),
]


def _yaml_values(text, key):
    """最初の ```yaml ブロックから `key: a | b | c   # …` の値の集合を返す。無ければ None。"""
    m = re.search(r"```yaml\n(.*?)```", text, re.S)
    for line in (m.group(1) if m else "").splitlines():
        if line.startswith(key + ":"):
            val = line.split(":", 1)[1].split("#", 1)[0]
            return {v.strip() for v in val.split("|") if v.strip()}
    return None


def check_declarations(failures):
    """宣言（schema-common.md / schema.md）と検証（okf_core / okf_lint の Config）の突き合わせ。

    書いてあることと守られていることは別（scripts/README.md）。語彙・目安日数・必須項目が
    文書とコードでずれたら、ここで止まる。Vault 固有の語彙は okf_lint.py の CONFIG と
    その Vault の schema.md §1 を比べる（okf_lint.py が無い環境では省略）。
    """
    vault = core.vault_root(__file__)
    common_path = os.path.join(vault, "schema-common.md")
    if not os.path.isfile(common_path):
        failures.append("schema-common.md が Vault ルートにない（共通宣言の正本。okf_core と同じく姉妹版と同一内容）")
        return
    with open(common_path, encoding="utf-8") as f:
        common = f.read()

    for key, expected in (("status", core.VALID_STATUS),
                          ("sensitivity", core.VALID_SENSITIVITY),
                          ("share_scope", core.VALID_SHARE_SCOPE)):
        declared = _yaml_values(common, key)
        if declared != set(expected):
            failures.append(f"宣言ずれ: schema-common.md の `{key}` {declared} ≠ okf_core {set(expected)}")

    required = set(re.findall(r"^\| `(\w+)` \| ○ \|", common, re.M))
    if required != set(core.REQUIRED_FIELDS):
        failures.append(f"宣言ずれ: schema-common.md の必須項目 {required} ≠ okf_core.REQUIRED_FIELDS")

    stale = {t: int(d) for t, d in re.findall(r"^\| `([\w-]+)` \| \*\*(\d+)日\*\*", common, re.M)}
    if stale != core.BASE_STALE_AFTER_DAYS:
        failures.append(f"宣言ずれ: schema-common.md §B-2 の目安 {stale} ≠ okf_core.BASE_STALE_AFTER_DAYS")

    for fld in ("valid_from", "valid_until", "valid_until_reason", "superseded_by"):
        if f"`{fld}`" not in common:
            failures.append(f"宣言ずれ: schema-common.md に `{fld}` の説明がない")

    # --- Vault 固有: schema.md §1 の語彙 ↔ okf_lint.py の CONFIG ---
    lint_path = os.path.join(HERE, "okf_lint.py")
    schema_path = os.path.join(vault, "schema.md")
    if not (os.path.isfile(lint_path) and os.path.isfile(schema_path)):
        return
    import importlib.util
    spec = importlib.util.spec_from_file_location("okf_lint_under_test", lint_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cfg = getattr(mod, "CONFIG", None)
    if cfg is None:
        failures.append("okf_lint.py に CONFIG がない（Vault の語彙を突き合わせられない）")
        return
    with open(schema_path, encoding="utf-8") as f:
        schema = f.read()
    for key, actual in (("provided_by", cfg.provided_by),
                        ("confirmed_by", cfg.confirmed_by),
                        ("type", cfg.types)):
        declared = _yaml_values(schema, key)
        if declared is None:
            failures.append(f"宣言ずれ: schema.md §1 の yaml 例に `{key}:` の行がない")
        elif declared != set(actual):
            failures.append(
                f"宣言ずれ: schema.md §1 の `{key}` と okf_lint.py の CONFIG が違う "
                f"（schema のみ: {sorted(declared - set(actual))} / CONFIG のみ: {sorted(set(actual) - declared)}）")
    for t, days in cfg.stale_after_days.items():
        if t in core.BASE_STALE_AFTER_DAYS:
            if days != core.BASE_STALE_AFTER_DAYS[t]:
                failures.append(f"宣言ずれ: Config が基底型 `{t}` の目安を {days} 日に上書きしている（基底は schema-common）")
        elif f"| `{t}` | **{days}日**" not in schema:
            failures.append(f"宣言ずれ: Vault 固有型 `{t}` の目安 {days} 日が schema.md §6-2 の表にない")


def make_vault(prefix, cases):
    tmp = tempfile.mkdtemp(prefix=prefix)
    os.makedirs(os.path.join(tmp, "wiki"), exist_ok=True)
    for relpath, content, _ in cases:
        full = os.path.join(tmp, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
    return tmp


def run_main(vault, config, *flags):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = core.main(vault, config, list(flags))
    return code, buf.getvalue()


def main():
    failures = []
    calls = {"page": 0, "vault": 0}

    def page_hook(page, report):
        calls["page"] += 1

    def vault_hook(vault, report, today):
        calls["vault"] += 1
        report.infos.append("[hook] vault_checks が呼ばれた")

    config = make_config(
        unknown_type_hint=lambda t: "（HINT）",
        page_check=page_hook,
        vault_checks=[vault_hook],
    )

    tmp = make_vault("okf_core_test_", CASES)
    try:
        code, out = run_main(tmp, config)
        for relpath, _, expected in CASES:
            name = os.path.basename(relpath)
            lines = [l for l in out.splitlines() if name in l and ("ERROR" not in l)]
            found = "\n".join(lines)
            for label in expected:
                if label not in found:
                    failures.append(f"未検出: {name} に「{label}」が出るはずが出ていない")
            if not expected and lines:
                failures.append(f"誤検出: {name} は違反なしのはずが検出された\n      {found}")

        if code != 2:
            failures.append(f"終了コードが 2 でない（実際: {code}）")
        if "[hook] vault_checks" not in out:
            failures.append("vault_checks が呼ばれていない")
        if calls["page"] == 0:
            failures.append("page_check が呼ばれていない")

        # allowlist が fail-closed であること
        rep = core.lint(tmp, config)
        for bad in ("E_個人混入.md", "C_生年月日混入.md", "P_001_public偽装.md", "C_共有不可.md"):
            if any(bad in a for a in rep.allowlist):
                failures.append(f"fail-open: 違反ページ {bad} が allowlist に載っている")
        if not any("E_公的機関.md" in a for a in rep.allowlist):
            failures.append("allowlist: 清浄な public ページ E_公的機関.md が載っていない")
        code_a, out_a = run_main(tmp, config, "--allowlist")
        if code_a != 0 or "E_公的機関.md" not in out_a:
            failures.append("--allowlist の出力が不正")

        # --gate は ERROR だけを見る（WARN のページはゲート出力に現れない）
        code_g, out_g = run_main(tmp, config, "--gate")
        if code_g != 2:
            failures.append(f"--gate: ERROR ありで 2 を返すべき（実際: {code_g}）")
        for fresh_page in ("TG_確認日なし.md", "PR_確認超過.md"):
            if fresh_page in out_g:
                failures.append(f"--gate: WARN のページ {fresh_page} がゲート出力に混ざっている")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # --- 空 Vault は 0 ---
    tmp2 = make_vault("okf_core_test_empty_", [])
    try:
        code, _ = run_main(tmp2, make_config())
        if code != 0:
            failures.append(f"空Vault: 0 を返すべき（実際: {code}）")
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)

    # --- WARN のみの Vault では --gate は 0、全チェックは 1 ---
    tmp3 = make_vault("okf_core_test_warnonly_",
                      [("wiki/triggers/TG_確認日なし.md", page("trigger", "internal", "本文"), set())])
    try:
        if run_main(tmp3, make_config(), "--gate")[0] != 0:
            failures.append("WARNのみ: --gate は 0 を返すべき")
        if run_main(tmp3, make_config())[0] != 1:
            failures.append("WARNのみ: 全チェックは 1 を返すべき")
    finally:
        shutil.rmtree(tmp3, ignore_errors=True)

    # --- wiki/ が無ければ致命 ERROR ---
    tmp4 = tempfile.mkdtemp(prefix="okf_core_test_nowiki_")
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            rep = core.lint(tmp4, make_config())
        if not any("[致命]" in e for e in rep.errors):
            failures.append("wiki/ 不在で [致命] ERROR が出るべき")
    finally:
        shutil.rmtree(tmp4, ignore_errors=True)

    # --- 宣言と検証の突き合わせ（schema-common.md ↔ okf_core、schema.md ↔ okf_lint CONFIG）---
    check_declarations(failures)

    print("=== okf_core 回帰テスト（姉妹 Vault 共通）===")
    if failures:
        for f in failures:
            print(f"  FAIL  {f}")
        print(f"\n{len(failures)} 件失敗")
        return 1
    print(f"  {len(CASES)} ケース＋5シナリオ全て合格")
    print("  - 公的機関の連絡先を誤検出せず、個人への到達経路を検出する")
    print("  - 機微ゲート・allowlist fail-closed が機能する")
    print("  - Config で注入した person_id 必須型・日付必須型・語彙に効く")
    print("  - 鮮度（欠落・超過・不正な確認手段）を WARN し、last_validated を受理する")
    print("  - 時点の2軸の矛盾を ERROR、contradicts 後の valid_until 未記入を WARN、終了した事実は鮮度不問")
    print("  - 終了コード（ERROR=2 / WARN=1 / --gate は WARN で 0 / 空 Vault は 0）")
    print("  - page_check / vault_checks / unknown_type_hint のフックが呼ばれる")
    print("  - 宣言（schema-common.md / schema.md §1）と検証（okf_core / CONFIG）の語彙・目安・必須項目が一致する")
    return 0


if __name__ == "__main__":
    sys.exit(main())

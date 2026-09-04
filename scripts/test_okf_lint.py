#!/usr/bin/env python3
"""
test_okf_lint.py — okf_lint.py の回帰テスト（oya-iru-wiki 版）

依存ゼロ。一時ディレクトリに合成 Vault を組み立てて lint を走らせ、
「検出すべきものを検出し、検出すべきでないものを検出しない」ことを確認する。
土台: oya-inai-keikaku-soudan/scripts/test_okf_lint.py

使い方:
    python3 scripts/test_okf_lint.py

schema.md や okf_lint.py を変更したら必ず走らせること。
本Vault固有の担保: 新設3型（koe / sentaku / fushime）のゲート、
sentaku の override_reason 必須（ERROR）と A-10 構造検査（WARN）、
撤去した plan / monitoring / meeting が未定義 type として弾かれること、
日記凍結のハッシュ台帳方式。
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LINT = os.path.join(HERE, "okf_lint.py")
CORE = os.path.join(HERE, "okf_core.py")   # okf_lint.py が import する共通核。一緒にコピーする

FM = """---
type: {type}
created: 2026-08-13
updated: 2026-08-13
sources:
  - "[[raw/test]]"
tags:
  - test
status: active
sensitivity: {sens}
{extra}---
"""

SENTAKU_BODY = """## 場面
テスト
## 本人のようす（事実）
二つのおやつからゼリーを指さした。
## まわりの受けとめ
甘いものの気分だったのだと思う。
## その後
ゼリーを食べた。
## 学び（次はどう提示するか）
二択の実物提示が機能する。
"""


def page(type_, sens, body, extra=""):
    return FM.format(type=type_, sens=sens, extra=extra) + body + "\n"


# (相対パス, 内容, そのページで検出されるべきラベルの集合)
CASES = [
    # --- 検出してはならない（公的機関の連絡先）---
    (
        "wiki/entities/E_公的機関.md",
        page("entity", "public",
             "代表 093-861-3045 / よりそいホットライン 0120-279-338 / "
             "問い合わせ info@city.kitakyushu.lg.jp"),
        set(),
    ),
    # --- 検出しなければならない（個人への到達経路）---
    (
        "wiki/entities/E_個人混入.md",
        page("entity", "public", "担当者 090-1234-5678 tanaka@gmail.com"),
        {"携帯番号", "個人メール"},
    ),
    (
        "wiki/concepts/C_生年月日混入.md",
        page("concept", "public", "対象者は2021年5月3日生まれ。"),
        {"生年月日"},
    ),
    # --- 機微ゲート ---
    (
        "wiki/persons/P_001_public偽装.md",
        page("person", "public", "本文", extra='person_id: "P_001"\n'),
        {"個人に紐づくため", "person_id を持つが"},
    ),
    (
        "wiki/sensitive/SE_purpose欠落.md",
        page("sensitive", "restricted", "本文"),
        {"restricted は", "sensitive_purpose"},
    ),
    (
        "wiki/persons/T_配置違反.md",
        page("trial", "internal", "本文"),
        {"wiki/trials/ に置く"},
    ),
    # --- ★ koe: 正常ページが通る / person_id 必須 / public 禁止 ---
    (
        "wiki/koe/KO_正常.md",
        page("koe", "internal", "本文",
             extra='person_id: "P_001"\nlast_confirmed: 2999-01-01\n'
                   'confirmed_by: "親が確認"\nprovided_by: "親"\n'),
        set(),
    ),
    (
        "wiki/koe/KO_id欠落.md",
        page("koe", "internal", "本文",
             extra='last_confirmed: 2999-01-01\n'),
        {"person_id"},
    ),
    (
        "wiki/koe/KO_確認日なし.md",
        page("koe", "internal", "本文", extra='person_id: "P_001"\nprovided_by: "親"\n'),
        {"last_confirmed"},
    ),
    # --- ★ sentaku: 正常 / 通らなかった＋理由あり / 理由なしは ERROR / A-10 見出し ---
    (
        "wiki/sentaku/ST_正常.md",
        page("sentaku", "internal", SENTAKU_BODY,
             extra='person_id: "P_001"\nsentaku_date: 2026-08-10\n'
                   'outcome: 尊重された\nprovided_by: "親"\nlifestage: 幼児期\n'),
        set(),
    ),
    (
        "wiki/sentaku/ST_理由あり.md",
        page("sentaku", "internal", SENTAKU_BODY,
             extra='person_id: "P_001"\nsentaku_date: 2026-08-10\n'
                   'outcome: 通らなかった\noverride_reason: "健康上の理由（主治医指示）"\n'
                   'provided_by: "親"\n'),
        set(),
    ),
    (
        "wiki/sentaku/ST_理由なし.md",
        page("sentaku", "internal", SENTAKU_BODY,
             extra='person_id: "P_001"\nsentaku_date: 2026-08-10\n'
                   'outcome: 通らなかった\nprovided_by: "親"\n'),
        {"override_reason"},
    ),
    (
        "wiki/sentaku/ST_見出し欠落.md",
        page("sentaku", "internal", "## 場面\nテストのみ\n",
             extra='person_id: "P_001"\nsentaku_date: 2026-08-10\n'
                   'outcome: 尊重された\nprovided_by: "親"\n'),
        {"本人のようす", "まわりの受けとめ"},
    ),
    (
        "wiki/sentaku/ST_outcome不正.md",
        page("sentaku", "internal", SENTAKU_BODY,
             extra='person_id: "P_001"\nsentaku_date: 2026-08-10\n'
                   'outcome: 却下\nprovided_by: "親"\n'),
        {"outcome"},
    ),
    (
        "wiki/sentaku/ST_日付欠落.md",
        page("sentaku", "internal", SENTAKU_BODY,
             extra='person_id: "P_001"\noutcome: 尊重された\nprovided_by: "親"\n'),
        {"sentaku_date"},
    ),
    # --- ★ sentaku は出来事型: 古い日付でも鮮度検査の対象外 ---
    (
        "wiki/sentaku/ST_出来事は対象外.md",
        page("sentaku", "internal", SENTAKU_BODY,
             extra='person_id: "P_001"\nsentaku_date: 2020-01-01\n'
                   'outcome: 尊重された\nprovided_by: "親"\n'),
        set(),
    ),
    # --- ★ fushime: 正常 / occurred_on 必須 / kind 語彙 ---
    (
        "wiki/fushime/FS_正常.md",
        page("fushime", "internal", "本文",
             extra='person_id: "P_001"\noccurred_on: 2026-04-01\n'
                   'fushime_kind: 就園・就学\nprovided_by: "親"\n'),
        set(),
    ),
    (
        "wiki/fushime/FS_日付欠落.md",
        page("fushime", "internal", "本文",
             extra='person_id: "P_001"\nfushime_kind: 卒業\nprovided_by: "親"\n'),
        {"occurred_on"},
    ),
    (
        "wiki/fushime/FS_kind不正.md",
        page("fushime", "internal", "本文",
             extra='person_id: "P_001"\noccurred_on: 2026-04-01\n'
                   'fushime_kind: 引越し\nprovided_by: "親"\n'),
        {"fushime_kind"},
    ),
    # --- ★ lifestage 語彙 ---
    (
        "wiki/persons/P_002_lifestage不正.md",
        page("person", "internal", "本文",
             extra='person_id: "P_002"\nlifestage: 青年期\nprovided_by: "親"\n'
                   'last_confirmed: 2999-01-01\n'),
        {"lifestage"},
    ),
    # --- 鮮度 ---
    (
        "wiki/triggers/TG_確認日なし.md",
        page("trigger", "internal", "本文"),
        {"last_confirmed"},
    ),
    (
        "wiki/protocols/PR_確認超過.md",
        page("protocol", "internal", "本文",
             extra='last_confirmed: 2020-01-01\nconfirmed_by: "実地で確認"\n'),
        {"最終確認から"},
    ),
    (
        "wiki/protocols/PR_旧フィールド.md",
        page("protocol", "internal", "本文", extra="last_validated: 2999-01-01\n"),
        set(),
    ),
    (
        "wiki/protocols/PR_確認手段不正.md",
        page("protocol", "internal", "本文",
             extra='last_confirmed: 2999-01-01\nconfirmed_by: "たぶん大丈夫"\n'),
        {"confirmed_by"},
    ),
    # --- ★ 本Vaultの確認手段「親が確認」を受理する ---
    (
        "wiki/protocols/PR_親が確認.md",
        page("protocol", "internal", "本文",
             extra='last_confirmed: 2999-01-01\nconfirmed_by: "親が確認"\n'),
        set(),
    ),
    # --- 出所と宛先 ---
    (
        "wiki/protocols/PR_出所不正.md",
        page("protocol", "internal", "本文",
             extra='person_id: "P_001"\nlast_confirmed: 2999-01-01\n'
                   'provided_by: "知人"\n'),
        {"provided_by"},
    ),
    (
        "wiki/protocols/PR_園学校出所.md",
        page("protocol", "internal", "本文",
             extra='person_id: "P_001"\nlast_confirmed: 2999-01-01\n'
                   'provided_by: "園・学校"\n'),
        set(),
    ),
    # --- ★ 撤去3型（keikaku-soudan の中核文書）は未定義 type として弾かれる ---
    (
        "wiki/concepts/PL_旧型plan.md",
        page("plan", "sensitive", "本文",
             extra='person_id: "P_001"\nsensitive_purpose: "テスト"\nprovided_by: "相談支援"\n'),
        {"未定義の type"},
    ),
    (
        "wiki/concepts/MO_旧型monitoring.md",
        page("monitoring", "sensitive", "本文",
             extra='person_id: "P_001"\nsensitive_purpose: "テスト"\nprovided_by: "相談支援"\n'),
        {"未定義の type"},
    ),
    # --- share_scope: origin-only は public でも allowlist に載らない ---
    (
        "wiki/concepts/C_共有不可.md",
        page("concept", "public", "提供元限定の一般知見",
             extra="share_scope: origin-only\n"),
        set(),
    ),
    # --- source_hash（任意）---
    (
        "wiki/concepts/C_hash正常.md",
        page("concept", "internal", "本文",
             extra="source_hash: " + "a1b2" * 16 + "\n"),
        set(),
    ),
    (
        "wiki/concepts/C_hash不正.md",
        page("concept", "internal", "本文",
             extra="source_hash: deadbeef\n"),
        {"source_hash"},
    ),
]


def run_lint(cwd, *flags):
    return subprocess.run(
        [sys.executable, os.path.join(cwd, "scripts", "okf_lint.py"), *flags],
        capture_output=True, text=True, cwd=cwd,
    )


def make_vault(prefix):
    tmp = tempfile.mkdtemp(prefix=prefix)
    os.makedirs(os.path.join(tmp, "scripts"))
    shutil.copy(LINT, os.path.join(tmp, "scripts", "okf_lint.py"))
    shutil.copy(CORE, os.path.join(tmp, "scripts", "okf_core.py"))
    os.makedirs(os.path.join(tmp, "wiki"), exist_ok=True)
    return tmp


def main():
    failures = []
    tmp = make_vault("okf_lint_test_")
    try:
        for relpath, content, _ in CASES:
            full = os.path.join(tmp, relpath)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)

        proc = run_lint(tmp)
        out = proc.stdout

        for relpath, _, expected in CASES:
            name = os.path.basename(relpath)
            lines = [l for l in out.splitlines() if name in l and ("ERROR" not in l)]
            found = "\n".join(lines)

            for label in expected:
                if label not in found:
                    failures.append(f"未検出: {name} に「{label}」が出るはずが出ていない")

            if not expected and lines:
                failures.append(f"誤検出: {name} は違反なしのはずが検出された\n      {found}")

        # allowlist が fail-closed であること
        allow = run_lint(tmp, "--allowlist").stdout.split()
        for bad in ("E_個人混入.md", "C_生年月日混入.md", "P_001_public偽装.md",
                    "C_共有不可.md", "ST_理由なし.md"):
            if any(bad in a for a in allow):
                failures.append(f"fail-open: 違反ページ {bad} が allowlist に載っている")

        if proc.returncode != 2:
            failures.append(f"終了コードが 2 でない（実際: {proc.returncode}）")

        # --gate は ERROR だけを見る
        proc3 = run_lint(tmp, "--gate")
        if proc3.returncode != 2:
            failures.append(f"--gate: ERROR ありで 2 を返すべき（実際: {proc3.returncode}）")
        for fresh_page in ("TG_確認日なし.md", "KO_確認日なし.md", "ST_見出し欠落.md"):
            if fresh_page in proc3.stdout:
                failures.append(f"--gate: WARN のページ {fresh_page} がゲート出力に混ざっている")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # --- 空 Vault は 0 を返す（Phase 2 DoD）---
    tmp2 = make_vault("okf_lint_test_empty_")
    try:
        p = run_lint(tmp2)
        if p.returncode != 0:
            failures.append(f"空Vault: 0 を返すべき（実際: {p.returncode}）")
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)

    # --- WARN のみの Vault では --gate は 0、全チェックは 1 ---
    tmp3 = make_vault("okf_lint_test_warnonly_")
    try:
        wpath = os.path.join(tmp3, "wiki", "triggers", "TG_確認日なし.md")
        os.makedirs(os.path.dirname(wpath))
        with open(wpath, "w", encoding="utf-8") as f:
            f.write(page("trigger", "internal", "本文"))
        if run_lint(tmp3, "--gate").returncode != 0:
            failures.append("WARNのみ: --gate は 0 を返すべき")
        if run_lint(tmp3).returncode != 1:
            failures.append("WARNのみ: 全チェックは 1 を返すべき")
    finally:
        shutil.rmtree(tmp3, ignore_errors=True)

    # --- ★ 日記凍結（ハッシュ台帳方式）---
    tmp4 = make_vault("okf_lint_test_freeze_")
    try:
        dpath = os.path.join(tmp4, "raw", "10_日記", "2026")
        os.makedirs(dpath)
        frozen = os.path.join(dpath, "2026-01.md")  # 過去月 → 凍結対象
        with open(frozen, "w", encoding="utf-8") as f:
            f.write("## 2026-01-15\n\n### あったこと\n- テスト\n")
        # 1回目: 台帳に記録される（INFO）。WARN はない
        p1 = run_lint(tmp4)
        if "[凍結]" not in p1.stdout or "台帳に記録" not in p1.stdout:
            failures.append("凍結: 初回実行で台帳記録の INFO が出るべき")
        if p1.returncode == 2:
            failures.append("凍結: 初回記録が ERROR になっている")
        # 2回目: 無変更なら何も言わない
        p2 = run_lint(tmp4)
        if "変更されている" in p2.stdout:
            failures.append("凍結: 無変更なのに変更検知された")
        # 3回目: 改変すると WARN
        with open(frozen, "a", encoding="utf-8") as f:
            f.write("\n改変テスト\n")
        p3 = run_lint(tmp4)
        if "変更されている" not in p3.stdout:
            failures.append("凍結: 凍結済み日記の改変が WARN にならない")
        if run_lint(tmp4, "--gate").returncode != 0:
            failures.append("凍結: 凍結 WARN が --gate を止めている（止めない設計）")
        # 当月ファイルは凍結対象外
        import datetime
        cur = datetime.date.today()
        curfile = os.path.join(dpath, f"{cur.year}-{cur.month:02d}.md")
        with open(curfile, "w", encoding="utf-8") as f:
            f.write("## 今日\n\n### あったこと\n- 当月テスト\n")
        p4 = run_lint(tmp4)
        if os.path.basename(curfile) in p4.stdout:
            failures.append("凍結: 当月ファイルが凍結扱いされている")
    finally:
        shutil.rmtree(tmp4, ignore_errors=True)

    print("=== okf_lint 回帰テスト（oya-iru-wiki）===")
    if failures:
        for f in failures:
            print(f"  FAIL  {f}")
        print(f"\n{len(failures)} 件失敗")
        return 1
    print(f"  {len(CASES)} ケース＋4シナリオ全て合格")
    print("  - 公的機関の連絡先を誤検出せず、個人への到達経路を検出する")
    print("  - 機微ゲート・allowlist fail-closed が機能する")
    print("  - koe / sentaku / fushime のゲート（person_id・日付・語彙）が機能する")
    print("  - sentaku「通らなかった」の override_reason 欠落は ERROR")
    print("  - A-10 構造検査（2見出し）は WARN")
    print("  - 撤去した plan / monitoring / meeting は未定義 type として弾かれる")
    print("  - 「親が確認」「園・学校」の本Vault語彙を受理する")
    print("  - 空 Vault は 0（Phase 2 DoD）")
    print("  - 鮮度・凍結の WARN は --gate を止めない")
    print("  - 日記凍結のハッシュ台帳（記録→無変更沈黙→改変WARN・当月対象外）が機能する")
    return 0


if __name__ == "__main__":
    sys.exit(main())

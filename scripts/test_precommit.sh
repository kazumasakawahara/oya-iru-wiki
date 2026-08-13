#!/bin/zsh
# githooks/pre-commit の3つの関所が実際にコミットを止めることを検証する。
# 検証後は必ず元の状態へ戻す（trap でクリーンアップを保証）。
# 前提: 作業ツリーがクリーンであること（コミット済み）。
# 土台: oya-inai-keikaku-soudan/scripts/test_precommit.sh
cd "$(dirname "$0")/.." || exit 1

if [ -n "$(git status --porcelain)" ]; then
  echo "作業ツリーがクリーンではありません。コミットしてから実行してください。"
  exit 1
fi

BEFORE=$(git rev-parse HEAD)
cleanup() {
  git reset -q HEAD -- . 2>/dev/null
  git checkout -q -- . 2>/dev/null
  rm -f wiki/persons/P_TEST_違反.md wiki/persons/P_TEST_清浄.md raw/40_医療から/test_dummy.md
  git remote remove testremote 2>/dev/null
  git reset -q --hard "$BEFORE" 2>/dev/null
  git clean -qfd wiki/persons 2>/dev/null
}
trap cleanup EXIT

pass=0; fail=0
check() { # $1=名前 $2=期待(block|allow) $3=実際の終了コード
  if [ "$2" = "block" ] && [ "$3" -ne 0 ]; then echo "  OK   $1 → 阻止した"; pass=$((pass+1))
  elif [ "$2" = "allow" ] && [ "$3" -eq 0 ]; then echo "  OK   $1 → 通した"; pass=$((pass+1))
  else echo "  FAIL $1 → 期待:$2 だが exit=$3"; fail=$((fail+1)); fi
}

echo "=== pre-commit 関所テスト（oya-iru-wiki）==="

# --- 関所1: raw/ の中身を -f で強制ステージ ---
echo "ダミー診断書" > raw/40_医療から/test_dummy.md
git add -f raw/40_医療から/test_dummy.md 2>/dev/null
git -c commit.gpgsign=false commit -q -m "test raw" >/dev/null 2>&1
check "関所1 raw/ の強制ステージ" block $?
git reset -q HEAD -- raw/ 2>/dev/null
rm -f raw/40_医療から/test_dummy.md

# --- 関所1b: raw/ 棚の README は骨格として通ること ---
echo "" >> raw/40_医療から/README.md
git add raw/40_医療から/README.md
git -c commit.gpgsign=false commit -q -m "test raw readme" >/dev/null 2>&1
check "関所1b 棚README は許可" allow $?
git reset -q --hard "$BEFORE" 2>/dev/null

# --- 関所2: remote × 個人紐づけページ（lint 的には清浄なページ）---
git remote add testremote https://example.invalid/x.git 2>/dev/null
cat > wiki/persons/P_TEST_清浄.md <<'EOF'
---
type: person
created: 2026-08-13
updated: 2026-08-13
sources:
  - "[[raw/test]]"
tags:
  - test
status: draft
sensitivity: internal
person_id: "P_TEST"
provided_by: "親"
---
清浄なテストページ。
EOF
git add wiki/persons/P_TEST_清浄.md
git -c commit.gpgsign=false commit -q -m "test remote" >/dev/null 2>&1
check "関所2 remote × 個人ページ" block $?
git remote remove testremote 2>/dev/null
git reset -q HEAD -- wiki/persons 2>/dev/null
rm -f wiki/persons/P_TEST_清浄.md

# --- 関所3: lint ERROR（機微ゲート違反ページ）---
cat > wiki/persons/P_TEST_違反.md <<'EOF'
---
type: person
created: 2026-08-13
updated: 2026-08-13
sources:
  - "[[raw/test]]"
tags:
  - test
status: active
sensitivity: public
person_id: "P_TEST"
---
本人の携帯 090-0000-1111。2020年5月3日生。
EOF
git add wiki/persons/P_TEST_違反.md
git -c commit.gpgsign=false commit -q -m "test lint" >/dev/null 2>&1
check "関所3 機微ゲート違反" block $?
git reset -q HEAD -- wiki/persons 2>/dev/null
rm -f wiki/persons/P_TEST_違反.md

# --- 正常系: 違反のない変更は通ること ---
echo "" >> log.md
git add log.md
git -c commit.gpgsign=false commit -q -m "test clean commit" >/dev/null 2>&1
check "正常系 違反なしの変更" allow $?

echo
echo "合格 $pass / 失敗 $fail"
[ "$fail" -eq 0 ] && echo "全関所が機能している" || echo "★ 関所に穴がある"
[ "$fail" -eq 0 ]

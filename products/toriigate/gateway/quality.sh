#!/usr/bin/env bash
# ToriiGate 品質ゲート — 毎コミット前に回す決定論的チェック（モデル不要・無料）
#
#   ./quality.sh              # 通常
#   FUZZ=200000 ./quality.sh  # ファジングを厚めに（節目用）
#
# 未インストールのツールはスキップし、インストール方法を表示する。
# モデルによるレビューはこの後の段階（docs/review-protocol.md）。
set -uo pipefail
cd "$(dirname "$0")"

FAIL=0
step() { printf "\n\033[1m== %s\033[0m\n" "$1"; }
ok()   { printf "  \033[32mok\033[0m   %s\n" "$1"; }
bad()  { printf "  \033[31mFAIL\033[0m %s\n" "$1"; FAIL=1; }
skip() { printf "  \033[33mskip\033[0m %s\n" "$1"; }

step "1. テストスイート"
if python3 -m pytest tests/ -q >/tmp/torii-pytest.log 2>&1; then
    ok "$(tail -1 /tmp/torii-pytest.log)"
else
    bad "pytest — 詳細: /tmp/torii-pytest.log"; tail -20 /tmp/torii-pytest.log
fi

step "2. ファジング（攻撃者到達パーサーが fail-closed か）"
ITER="${FUZZ:-20000}"
if python3 -m redteam.fuzz --iterations "$ITER" >/tmp/torii-fuzz.log 2>&1; then
    ok "全ターゲットが hostile input に対し fail-closed（${ITER} 反復）"
else
    bad "ファジングで例外が漏れた — 詳細: /tmp/torii-fuzz.log"
    tail -30 /tmp/torii-fuzz.log
fi

step "3. レッドチーム評価（検知率・誤検知率）"
if python3 -m redteam.run_assessment >/tmp/torii-assess.json 2>/dev/null; then
    python3 - <<'PY'
import json
d = json.load(open("/tmp/torii-assess.json"))
s = d["summary"]
fp = s["fp_rate_avg"]
print(f"  既知型検知 {s['detection_careless_avg']*100:.0f}% / "
      f"高度偽装 {s['detection_sophisticated_avg']*100:.0f}% / "
      f"誤検知 {fp*100:.0f}%")
raise SystemExit(1 if fp > 0 else 0)
PY
    if [ $? -eq 0 ]; then ok "誤検知 0%（正規トラフィックを弾いていない）"
    else bad "誤検知が発生している — 正規ユーザーを弾くのは事業上致命的"; fi
else
    bad "レッドチーム評価が実行できなかった"
fi

step "4. 静的解析（bandit）"
if python3 -c "import bandit" 2>/dev/null; then
    if python3 -m bandit -r toriigate/ -q >/tmp/torii-bandit.log 2>&1; then
        ok "指摘なし"
    else
        bad "bandit の指摘あり"; cat /tmp/torii-bandit.log
    fi
else
    skip "bandit 未インストール（pip install bandit）"
fi

step "5. 依存の脆弱性（pip-audit）"
if python3 -c "import pip_audit" 2>/dev/null; then
    if python3 -m pip_audit -r <(echo "cryptography
PyYAML
redis") >/tmp/torii-audit.log 2>&1; then
        ok "既知の脆弱性なし"
    else
        bad "依存に既知の脆弱性"; tail -20 /tmp/torii-audit.log
    fi
else
    skip "pip-audit 未インストール（pip install pip-audit）"
fi

step "6. 評価スコアカード（指標 vs 閾値）"
if python3 -m redteam.scorecard >/tmp/torii-scorecard.log 2>&1; then
    sed -n '/指標/,/^$/p' /tmp/torii-scorecard.log | sed 's/^/  /' | head -12
    ok "全ブロッカー指標が閾値内"
else
    bad "ブロッカー指標が閾値外 — 詳細: python3 -m redteam.scorecard"
    sed -n '/指標/,/^$/p' /tmp/torii-scorecard.log | sed 's/^/  /' | head -12
fi

printf "\n"
if [ "$FAIL" -eq 0 ]; then
    printf "\033[32m品質ゲート(L0)通過。\033[0m 次の段階に進める状態です。\n"
    printf "  → L1: docs/review-protocol.md の手順で多モデル検証\n"
    printf "  → 解禁される事業ゲートは docs/verification-plan.md の表で確認\n"
    printf "  ※ 合成テストが緑でも「防御できる製品」としての販売は解禁されません\n"
else
    printf "\033[31m品質ゲート(L0)不通過。\033[0m 先に上記を直すこと。\n"
    printf "  エラーを残したままモデルレビューに進むと、指摘が本質から逸れます。\n"
fi
exit "$FAIL"

#!/usr/bin/env bash
# ToriiGate テストキット — ワンコマンド起動（Mac / Linux）
#
#   ./serve.sh                 # 既定ポリシーで enforce 起動
#   POLICY=policies/monitor.json ./serve.sh   # monitor（遮断せず観察）
#   PORT=9000 ./serve.sh       # ポート変更
#
# デモ原本サーバ（:3000）を裏で起動し、その前段に ToriiGate（:8080）を立てる。
# Ctrl-C で両方停止する。コアは標準ライブラリのみ＝pip 不要。
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
GW_DIR="$(cd "$HERE/../gateway" && pwd)"
PORT="${PORT:-8080}"
ORIGIN_PORT="${ORIGIN_PORT:-3000}"
export TORII_SECRET="${TORII_SECRET:-testkit-secret}"

echo "==> demo origin on :$ORIGIN_PORT (serving testkit/site)"
python3 -m http.server "$ORIGIN_PORT" --directory "$HERE/site" \
    >/tmp/toriigate-origin.log 2>&1 &
ORIGIN_PID=$!
cleanup() { kill "$ORIGIN_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

IP="$(ipconfig getifaddr en0 2>/dev/null \
      || ipconfig getifaddr en1 2>/dev/null \
      || hostname -I 2>/dev/null | awk '{print $1}' \
      || echo 127.0.0.1)"

echo ""
echo "  ⛩️  ToriiGate gateway on :$PORT"
echo "  ----------------------------------------------------------"
echo "  他機からのアクセス先 : http://$IP:$PORT/"
echo "  ダッシュボード       : http://$IP:$PORT/_torii/dashboard"
echo "  統計(JSON)          : http://$IP:$PORT/_torii/stats"
echo "  robots.txt(生成)     : http://$IP:$PORT/robots.txt"
echo "  停止                 : Ctrl-C"
echo "  ----------------------------------------------------------"
[ -n "${POLICY:-}" ] && echo "  ポリシー: $POLICY"
echo ""

cd "$GW_DIR"
POLICY_ARG=()
if [ -n "${POLICY:-}" ]; then
    # POLICY はテストキット相対でも絶対でも受ける
    if [ -f "$HERE/$POLICY" ]; then POLICY_ARG=(--policy "$HERE/$POLICY")
    else POLICY_ARG=(--policy "$POLICY"); fi
fi
python3 -m toriigate.proxy --origin "http://localhost:$ORIGIN_PORT" \
    --port "$PORT" "${POLICY_ARG[@]}"

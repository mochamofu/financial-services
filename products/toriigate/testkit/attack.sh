#!/usr/bin/env bash
# ToriiGate テストキット — 攻撃バッテリー（Mac / Linux, curl）
#   ./attack.sh http://192.168.1.50:8080
#
# 各種の「悪い / 自動化された」クライアントを模して、想定どおり止まるか確認する。
# 注意: block も challenge も HTTP 403 を返す。区別はダッシュボードのカテゴリ/
# アクション欄で確認すること（ステータスコードだけでは区別できない）。
set -uo pipefail
GW="${1:?usage: attack.sh <gateway-url>  例: ./attack.sh http://192.168.1.50:8080}"

hit() { # ua path desc expect
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" -A "$1" "$GW$2")
  printf "  [%s] %-38s 期待: %s\n" "$code" "$3" "$4"
}
raw() { # path desc expect
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" "$GW$1")
  printf "  [%s] %-38s 期待: %s\n" "$code" "$2" "$3"
}

echo "== ToriiGate 攻撃バッテリー -> $GW =="
hit "curl/8.5.0"                              "/" "スクレイパー(curl)"        "403 challenge"
hit "python-requests/2.32"                    "/" "スクレイパー(requests)"    "403 challenge"
hit "GPTBot/1.2"                              "/" "GPTBotなりすまし(IP不一致)" "403 block(spoofed)"
hit "ClaudeBot/1.0"                           "/" "学習クローラー"            "403 block"
hit "Bytespider"                              "/" "学習クローラー"            "403 block"
hit "Mozilla/5.0 (compatible; Googlebot/2.1)" "/" "Googlebot(IP不一致)"       "403 block(spoofed)"
hit "MyCustomAgent/1.0"                       "/" "未知の非ブラウザUA"        "403 challenge"
raw "/.env"                     "脆弱性プローブ /.env"        "403 block(malicious)"
raw "/.well-known/torii-trap"   "ハニーポット"               "403 block(malicious)"

echo "== 連打による挙動分析（レート）テスト =="
# ブラウザ風ヘッダ＋UA で高速連打 → 短時間の大量アクセスで human から bot に再分類される。
BR="Mozilla/5.0 (Windows NT 10.0) Chrome/126.0"
H=(-H "Accept: text/html" -H "Accept-Language: ja" -H "Accept-Encoding: gzip")
for _ in $(seq 1 60); do curl -s -o /dev/null "${H[@]}" -A "$BR" "$GW/"; done
code=$(curl -s -o /dev/null -w "%{http_code}" "${H[@]}" -A "$BR" "$GW/")
printf "  [%s] ブラウザ風の高速連打後              期待: 403（レート超過で bot 再分類）\n" "$code"
echo "  ※ 429(throttle) は allow カテゴリ（許可済みIP等）が上限超過した場合のみ。"
echo "     怪しい挙動・スクレイパーは 403（challenge/block）で止まる。"

echo ""
echo "ダッシュボードで分類とアクションを確認: $GW/_torii/dashboard"

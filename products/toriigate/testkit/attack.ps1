# ToriiGate テストキット — 攻撃バッテリー（Windows / PowerShell, curl.exe）
#   .\attack.ps1 -Gateway http://192.168.1.50:8080
#
# 注意: block も challenge も HTTP 403。区別はダッシュボードのカテゴリ/アクション欄で。
# Windows 10 (1803+) には curl.exe が標準搭載。
param([Parameter(Mandatory=$true)][string]$Gateway)

function Hit([string]$ua,[string]$path,[string]$desc,[string]$expect) {
  $code = & curl.exe -s -o NUL -w "%{http_code}" -A $ua "$Gateway$path"
  ("  [{0}] {1,-38} 期待: {2}" -f $code, $desc, $expect) | Write-Host
}
function Raw([string]$path,[string]$desc,[string]$expect) {
  $code = & curl.exe -s -o NUL -w "%{http_code}" "$Gateway$path"
  ("  [{0}] {1,-38} 期待: {2}" -f $code, $desc, $expect) | Write-Host
}

Write-Host "== ToriiGate 攻撃バッテリー -> $Gateway =="
Hit "curl/8.5.0"                              "/" "スクレイパー(curl)"         "403 challenge"
Hit "python-requests/2.32"                    "/" "スクレイパー(requests)"     "403 challenge"
Hit "GPTBot/1.2"                              "/" "GPTBotなりすまし(IP不一致)" "403 block(spoofed)"
Hit "ClaudeBot/1.0"                           "/" "学習クローラー"             "403 block"
Hit "Bytespider"                              "/" "学習クローラー"             "403 block"
Hit "Mozilla/5.0 (compatible; Googlebot/2.1)" "/" "Googlebot(IP不一致)"        "403 block(spoofed)"
Hit "MyCustomAgent/1.0"                       "/" "未知の非ブラウザUA"         "403 challenge"
Raw "/.env"                    "脆弱性プローブ /.env"  "403 block(malicious)"
Raw "/.well-known/torii-trap"  "ハニーポット"          "403 block(malicious)"

Write-Host "== 連打による挙動分析（レート）テスト =="
# ブラウザ風ヘッダ＋UA で高速連打 → 短時間の大量アクセスで human から bot に再分類。
$br = "Mozilla/5.0 (Windows NT 10.0) Chrome/126.0"
$h = @("-H","Accept: text/html","-H","Accept-Language: ja","-H","Accept-Encoding: gzip")
1..60 | ForEach-Object { & curl.exe -s -o NUL @h -A $br "$Gateway/" | Out-Null }
$code = & curl.exe -s -o NUL -w "%{http_code}" @h -A $br "$Gateway/"
("  [{0}] ブラウザ風の高速連打後              期待: 403（レート超過で bot 再分類）" -f $code) | Write-Host
Write-Host "  ※ 429(throttle) は allow カテゴリ（許可済みIP等）が上限超過した場合のみ。"
Write-Host "     怪しい挙動・スクレイパーは 403（challenge/block）で止まる。"

Write-Host ""
Write-Host "ダッシュボードで分類とアクションを確認: $Gateway/_torii/dashboard"

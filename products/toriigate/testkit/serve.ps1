# ToriiGate テストキット — ワンコマンド起動（Windows / PowerShell）
#
#   .\serve.ps1
#   .\serve.ps1 -Policy policies\monitor.json
#   .\serve.ps1 -Port 9000
#
# デモ原本サーバ（:3000）を裏で起動し、前段に ToriiGate（:8080）を立てる。
# コアは標準ライブラリのみ＝pip 不要。停止は Ctrl-C。
param(
  [int]$Port = 8080,
  [int]$OriginPort = 3000,
  [string]$Policy = ""
)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$gw   = Resolve-Path (Join-Path $here "..\gateway")
if (-not $env:TORII_SECRET) { $env:TORII_SECRET = "testkit-secret" }

Write-Host "==> demo origin on :$OriginPort (serving testkit\site)"
$origin = Start-Process python `
  -ArgumentList "-m","http.server","$OriginPort","--directory","$here\site" `
  -PassThru -WindowStyle Hidden

try {
  $ip = (Get-NetIPAddress -AddressFamily IPv4 |
         Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
         Select-Object -First 1).IPAddress
  Write-Host ""
  Write-Host "  ToriiGate gateway on :$Port"
  Write-Host "  ----------------------------------------------------------"
  Write-Host "  他機からのアクセス先 : http://${ip}:$Port/"
  Write-Host "  ダッシュボード       : http://${ip}:$Port/_torii/dashboard"
  Write-Host "  停止                 : Ctrl-C"
  Write-Host "  ----------------------------------------------------------"
  Write-Host ""

  Push-Location $gw
  $args = @("-m","toriigate.proxy","--origin","http://localhost:$OriginPort","--port","$Port")
  if ($Policy) {
    $p = if (Test-Path (Join-Path $here $Policy)) { Join-Path $here $Policy } else { $Policy }
    $args += @("--policy",$p)
  }
  python @args
}
finally {
  Stop-Process -Id $origin.Id -ErrorAction SilentlyContinue
  Pop-Location
}

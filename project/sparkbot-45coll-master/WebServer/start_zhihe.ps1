$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Project = Split-Path -Parent $Root
$Runtime = Join-Path $Root "runtime"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
New-Item -ItemType Directory -Force -Path $Runtime | Out-Null
& (Join-Path $Root "start_hotspot.ps1")

function Test-Port([int]$Port) {
    return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

function Start-Hidden([string]$Name, [string]$File, [string[]]$Arguments, [string]$WorkingDirectory) {
    $stdout = Join-Path $Runtime "$Name.log"
    $stderr = Join-Path $Runtime "$Name.err.log"
    $process = Start-Process -FilePath $File -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory `
        -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
    Set-Content -LiteralPath (Join-Path $Runtime "$Name.pid") -Value $process.Id -Encoding ascii
}

if (-not (Test-Port 18789)) {
    Start-Hidden "openclaw" "openclaw.cmd" @("gateway", "run") $Project
}
if (-not (Test-Port 18790)) {
    Start-Hidden "tool-bridge" $Python @("scripts\windows_tool_bridge.py", "--host", "127.0.0.1", "--port", "18790", "--project-root", $Project) $Root
}
if (-not (Test-Port 18880)) {
    $SmartHome = Join-Path (Split-Path -Parent $Project) "XiaoZhi\RaspberryPiSmartHome"
    Start-Hidden "smart-home" $Python @("app.py", "--simulate", "--host", "127.0.0.1", "--port", "18880") $SmartHome
}
if (-not (Test-Port 8000)) {
    Start-Hidden "xiaozhi-gateway" $Python @("-m", "xiaozhi_gateway") $Root
}

Start-Sleep -Seconds 2
$health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 5
$smartHomeHealth = Invoke-RestMethod -Uri "http://127.0.0.1:18880/api/health" -TimeoutSec 5
Write-Output "Xiaozhi gateway: $($health.ok)"
Write-Output "Smart home: $($smartHomeHealth.ok) (simulate=$($smartHomeHealth.simulate))"
Write-Output "Dashboard: http://127.0.0.1:8000/"

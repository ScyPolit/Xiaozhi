$ErrorActionPreference = "Stop"
$Repository = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $Repository "apps\gateway\start_zhihe.ps1")

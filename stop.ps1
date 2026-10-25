$ErrorActionPreference = "Stop"
$Repository = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $Repository "apps\gateway\stop_zhihe.ps1")

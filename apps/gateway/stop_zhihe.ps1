$Runtime = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "runtime"
Get-ChildItem -LiteralPath $Runtime -Filter "*.pid" -ErrorAction SilentlyContinue | ForEach-Object {
    $processId = [int](Get-Content -LiteralPath $_.FullName -Raw)
    Stop-Process -Id $processId -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
}

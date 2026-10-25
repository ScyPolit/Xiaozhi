$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime

function Await($Operation, [Type]$ResultType) {
    while ($Operation.Status -eq 0) { Start-Sleep -Milliseconds 50 }
    if ($Operation.Status -ne 1) { throw "Windows async operation failed: $($Operation.ErrorCode)" }
    return $Operation.GetResults()
}

[Windows.Networking.Connectivity.NetworkInformation,Windows.Networking.Connectivity,ContentType=WindowsRuntime] | Out-Null
[Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager,Windows.Networking.NetworkOperators,ContentType=WindowsRuntime] | Out-Null
[Windows.Networking.NetworkOperators.NetworkOperatorTetheringAccessPointConfiguration,Windows.Networking.NetworkOperators,ContentType=WindowsRuntime] | Out-Null
[Windows.Networking.NetworkOperators.NetworkOperatorTetheringOperationResult,Windows.Networking.NetworkOperators,ContentType=WindowsRuntime] | Out-Null

$profile = [Windows.Networking.Connectivity.NetworkInformation]::GetInternetConnectionProfile()
if (-not $profile) { throw "No internet connection profile is available." }
$manager = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::CreateFromConnectionProfile($profile)
$config = $manager.GetCurrentAccessPointConfiguration()
$alreadyReady = $manager.TetheringOperationalState.ToString() -eq "On" -and
    $config.Ssid -eq "scypolit" -and $config.Band.ToString() -eq "TwoPointFourGigahertz"
if ($alreadyReady) {
    Write-Output "Mobile hotspot scypolit is already running."
    exit 0
}
$config.Ssid = "scypolit"
$config.Passphrase = "88888888"
$config.Band = [Windows.Networking.NetworkOperators.TetheringWiFiBand]::TwoPointFourGigahertz
if ($manager.TetheringOperationalState.ToString() -eq "On") {
    $manager.StopTetheringAsync() | Out-Null
    $stopDeadline = (Get-Date).AddSeconds(10)
    while ((Get-Date) -lt $stopDeadline -and $manager.TetheringOperationalState.ToString() -ne "Off") { Start-Sleep -Milliseconds 100 }
}
try { Await ($manager.ConfigureAccessPointAsync($config)) ([Windows.Networking.NetworkOperators.NetworkOperatorTetheringOperationResult]) | Out-Null } catch {
    $actual = $manager.GetCurrentAccessPointConfiguration()
    if ($actual.Ssid -ne "scypolit" -or $actual.Band.ToString() -ne "TwoPointFourGigahertz") {
        throw "Unable to configure the mobile hotspot for 2.4 GHz: $($_.Exception.Message)"
    }
}
$manager.StartTetheringAsync() | Out-Null
$deadline = (Get-Date).AddSeconds(15)
while ((Get-Date) -lt $deadline -and -not (Get-NetIPAddress -AddressFamily IPv4 -IPAddress "192.168.137.1" -ErrorAction SilentlyContinue)) {
    Start-Sleep -Milliseconds 250
}
if (-not (Get-NetIPAddress -AddressFamily IPv4 -IPAddress "192.168.137.1" -ErrorAction SilentlyContinue)) {
    throw "Mobile hotspot did not become ready."
}
Write-Output "Mobile hotspot scypolit is running."

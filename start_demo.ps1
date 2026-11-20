param([switch]$WithAirflow)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'setup_demo.ps1') -WithAirflow:$WithAirflow
if ($LASTEXITCODE -ne 0) { throw 'Demo startup failed.' }

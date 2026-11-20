param([switch]$ConfirmReset)
$ErrorActionPreference = 'Stop'
if (-not $ConfirmReset) { throw 'Pass -ConfirmReset to delete only this demo package isolated volumes.' }
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.env.demo')) { throw 'No demo environment has been created.' }
docker compose --env-file .env.demo -f docker-compose.yml -f docker-compose.devops.yml `
    -f docker-compose.demo.yml down --volumes
if ($LASTEXITCODE -ne 0) { throw 'Demo reset failed.' }

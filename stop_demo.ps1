$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.env.demo')) { throw 'Run setup_demo.ps1 first.' }
docker compose --env-file .env.demo -f docker-compose.yml -f docker-compose.devops.yml `
    -f docker-compose.demo.yml down
if ($LASTEXITCODE -ne 0) { throw 'Demo stop failed.' }

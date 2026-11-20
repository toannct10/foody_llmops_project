$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $root
$compose = @('-f', 'docker-compose.yml', '-f', 'docker-compose.devops.yml')
docker compose @compose stop grafana prometheus postgres
if ($LASTEXITCODE -ne 0) { throw 'Could not stop monitoring and database services.' }
Write-Host 'Monitoring and PostgreSQL stopped. Named volumes and the normal demo remain.'

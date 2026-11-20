$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $root
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker CLI is required.' }
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker daemon is unavailable.' }
$compose = @('-f', 'docker-compose.yml', '-f', 'docker-compose.devops.yml')
$baseImage = if ($env:FOODY_BASE_IMAGE) { $env:FOODY_BASE_IMAGE } else { "$(Split-Path $root -Leaf)-rag-backend:latest" }
if (-not $env:FOODY_BASE_IMAGE) {
    docker build -f Dockerfile.rag -t $baseImage .
    if ($LASTEXITCODE -ne 0) { throw 'Base RAG image build failed.' }
}
docker run --rm $baseImage python -c 'import torch, transformers, sentencepiece'
if ($LASTEXITCODE -ne 0) { throw 'Base RAG image lacks PhoBERT dependencies.' }
$env:FOODY_BASE_IMAGE = $baseImage
$env:GIT_SHA = (git rev-parse HEAD).Trim()
docker compose @compose build rag-backend
if ($LASTEXITCODE -ne 0) { throw 'DevOps image build failed.' }
docker compose @compose up -d --wait --wait-timeout 240 postgres qwen rag-backend streamlit prometheus grafana
if ($LASTEXITCODE -ne 0) { throw 'Compose startup failed.' }
docker compose @compose exec -T rag-backend python -c 'from src.warehouse.loader import connection, migrate; c = connection(); print(migrate(c)); c.commit(); c.close()'
if ($LASTEXITCODE -ne 0) { throw 'Warehouse migration failed.' }
$hasTable = (docker compose @compose exec -T postgres psql -U foody -d foody -Atc `
    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='fact_review')").Trim()
$needsLoad = $hasTable -ne 't'
if (-not $needsLoad) {
    $count = [int](docker compose @compose exec -T postgres psql -U foody -d foody -Atc `
        'SELECT COUNT(*) FROM fact_review').Trim()
    $version = (docker compose @compose exec -T postgres psql -U foody -d foody -Atc `
        'SELECT MAX(version) FROM schema_migrations').Trim()
    $needsLoad = $count -eq 0 -or $version -ne '005'
}
if ($needsLoad) {
    docker compose @compose exec -T rag-backend python -m src.cli warehouse-load
    if ($LASTEXITCODE -ne 0) { throw 'Warehouse load failed.' }
} else {
    Write-Host "Warehouse already loaded ($count reviews; migration $version)."
}
if (Test-Path -LiteralPath (Join-Path $root 'data/foody/source/order_cleaning.csv')) {
    docker compose @compose exec -T rag-backend python -m src.cli sales-load
    if ($LASTEXITCODE -ne 0) { throw 'Sales load failed.' }
}
docker compose @compose ps
Write-Host 'Streamlit http://localhost:8501 | Grafana http://localhost:3000 | Prometheus http://localhost:9090'

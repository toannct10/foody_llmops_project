param([switch]$WithAirflow)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker Desktop and Docker Compose are required.'
}
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop is not running.' }

if (-not (Test-Path -LiteralPath '.env.demo' -PathType Leaf)) {
    $suffix = [guid]::NewGuid().ToString('N').Substring(0, 10)
    $dbPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(18)).ToLowerInvariant()
    $grafanaPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(18)).ToLowerInvariant()
    @("COMPOSE_PROJECT_NAME=foody-full-demo-$suffix",
      "FOODY_DEMO_VOLUME_PREFIX=foody_full_demo_$suffix",
      "FOODY_DB_PASSWORD=$dbPassword",
      "FOODY_GRAFANA_PASSWORD=$grafanaPassword",
      'FOODY_BASE_IMAGE=foody-demo-base:local') |
        Set-Content -LiteralPath '.env.demo' -Encoding utf8
}
$compose = @('--env-file', '.env.demo', '-f', 'docker-compose.yml',
             '-f', 'docker-compose.devops.yml', '-f', 'docker-compose.demo.yml')
if ($WithAirflow) { $compose += @('-f', 'docker-compose.airflow.yml', '--profile', 'airflow') }
$required = @('models/qwen_v3/qwen2.5-3b-instruct-q4_k_m.gguf',
    'models/tfidf_logreg.joblib', 'models/aspect_tfidf.joblib',
    'models/phobert_absa/absa.pt', 'models/phobert_absa/tokenizer/vocab.txt',
    'models/phobert_absa/backbone_config/config.json',
    'models/phobert_absa/relevance.joblib',
    'models/embeddings/models--Qdrant--paraphrase-multilingual-MiniLM-L12-v2-onnx-Q',
    'data/foody/source/order_cleaning.csv',
    'data/foody/source/data_2025_2026.csv',
    'data/foody/processed/reviews_2025_2026_enriched.parquet',
    'data/foody/vector_store_review_2025_2026/index_manifest.json',
    'data/foody/lexical_index_review_2025_2026/reviews.sqlite',
    'database/foody.dump')
foreach ($path in $required) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing packaged artifact: $path" }
}
docker compose @compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose validation failed.' }
New-Item -ItemType Directory -Force -Path state,logs,'outputs/airflow' | Out-Null
docker compose @compose up -d postgres
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL startup failed.' }
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    docker compose @compose exec -T postgres pg_isready -h 127.0.0.1 -U foody -d foody *> $null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $ready) { throw 'PostgreSQL did not become ready.' }
$counts = (docker compose @compose exec -T postgres psql -U foody -d foody -At -c `
    "SELECT CASE WHEN to_regclass('public.fact_order') IS NULL THEN 'empty' ELSE 'loaded' END;").Trim()
if ($counts -ne 'loaded') {
    docker compose @compose cp database/foody.dump postgres:/tmp/foody.dump
    if ($LASTEXITCODE -ne 0) { throw 'Database dump copy failed.' }
    docker compose @compose exec -T postgres pg_restore -U foody -d foody `
        --no-owner --no-privileges /tmp/foody.dump
    if ($LASTEXITCODE -ne 0) { throw 'Database restore failed.' }
} else {
    Write-Host 'Existing demo database found; restore skipped.'
}
$dbCounts = (docker compose @compose exec -T postgres psql -U foody -d foody -At -c `
    'SELECT (SELECT COUNT(*) FROM fact_order), (SELECT COUNT(*) FROM fact_review_v2), (SELECT MAX(version) FROM schema_migrations);').Trim()
if ($dbCounts -ne '400000|15456|005') { throw "Unexpected restored database counts/version: $dbCounts" }
docker build -f Dockerfile.rag -t foody-demo-base:local .
if ($LASTEXITCODE -ne 0) { throw 'Base application image build failed.' }
$env:FOODY_BASE_IMAGE = 'foody-demo-base:local'
docker compose @compose build rag-backend
if ($LASTEXITCODE -ne 0) { throw 'DevOps application image build failed.' }
$services = @('postgres','qwen','rag-backend','streamlit','prometheus','grafana')
if ($WithAirflow) { $services += 'airflow' }
docker compose @compose up -d --wait --wait-timeout 300 @services
if ($LASTEXITCODE -ne 0) { throw 'Demo services did not start.' }
if (-not (Test-Path -LiteralPath 'state/llmops.sqlite')) {
    docker compose @compose cp ./init_telemetry.py streamlit:/tmp/init_telemetry.py
    if ($LASTEXITCODE -ne 0) { throw 'Telemetry script copy failed.' }

    docker compose @compose exec -T streamlit python /tmp/init_telemetry.py
    if ($LASTEXITCODE -ne 0) { throw 'Telemetry initialization failed.' }
}
docker compose @compose exec -T -e FOODY_DEMO_RUNTIME=docker streamlit python -m src.cli demo-preflight
if ($LASTEXITCODE -ne 0) { throw 'Packaged demo preflight failed.' }
docker compose @compose ps
Write-Host 'Demo ready: Streamlit http://localhost:8501 | API http://localhost:8000 | Grafana http://localhost:3000 | Prometheus http://localhost:9090'

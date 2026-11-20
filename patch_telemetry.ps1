$path = Join-Path $PSScriptRoot 'setup_demo.ps1'
$lines = @(Get-Content -LiteralPath $path)

$start = -1
$end = -1

for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match "if \(-not \(Test-Path -LiteralPath 'state/llmops\.sqlite'\)\)") {
        $start = $i
        break
    }
}

if ($start -lt 0) {
    throw "Cannot find telemetry initialization block."
}

for ($i = $start; $i -lt $lines.Count; $i++) {
    if ($lines[$i].Trim() -eq '}') {
        $end = $i
        break
    }
}

if ($end -lt 0) {
    throw "Cannot find end of telemetry block."
}

$newBlock = @(
    "if (-not (Test-Path -LiteralPath 'state/llmops.sqlite')) {"
    "    docker compose @compose cp ./init_telemetry.py streamlit:/tmp/init_telemetry.py"
    "    if (`$LASTEXITCODE -ne 0) { throw 'Telemetry script copy failed.' }"
    ""
    "    docker compose @compose exec -T streamlit python /tmp/init_telemetry.py"
    "    if (`$LASTEXITCODE -ne 0) { throw 'Telemetry initialization failed.' }"
    "}"
)

$result = @()
if ($start -gt 0) {
    $result += $lines[0..($start - 1)]
}
$result += $newBlock
if ($end -lt ($lines.Count - 1)) {
    $result += $lines[($end + 1)..($lines.Count - 1)]
}

Set-Content -LiteralPath $path -Value $result -Encoding UTF8
Write-Host "Telemetry block successfully replaced."

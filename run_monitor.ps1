Set-Location $PSScriptRoot

$env:CPM_POLYMARKET_MARKETS_JSON = Get-Content ".\config\markets.polymarket.json" -Raw
$env:CPM_RULES_JSON             = Get-Content ".\config\rules.json" -Raw
$env:CPM_UPSTREAM               = "multi"

.\.venv\Scripts\python.exe -m src

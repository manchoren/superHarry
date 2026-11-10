param(
    [string]$ScriptPath
)
$ErrorActionPreference = 'Stop'
$ErrorActionPreference = 'Stop'
if (-not $ScriptPath) {
    Write-Host 'Usage: powershell -File validate.ps1 -ScriptPath <path>'
    exit 1
}
if (-not (Test-Path $ScriptPath)) {
    Write-Host "Script not found: $ScriptPath"
    exit 1
}
# Parse the script to check syntax without executing it.
$content = Get-Content -LiteralPath $ScriptPath -Raw
$ast = [System.Management.Automation.AST]::ParseInput($content, $null, [ref]$null)
$tokens = $null
$parserrors = $null
$ast.Parse($null, [ref]$tokens, [ref]$parserrors) | Out-Null
if ($parserrors.Count -gt 0) {
    Write-Host "SYNTAX_ERRORS:"
    $parserrors | ForEach-Object { Write-Host "  line $($_.Extent.StartLineNumber): $($_.Exception.Message)" }
    exit 1
} else {
    Write-Host 'SYNTAX_OK'
}

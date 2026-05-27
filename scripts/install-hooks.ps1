Param()
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$githooksSrc = Join-Path $repoRoot ".githooks"
$githooksDest = Join-Path $repoRoot ".git\hooks"

if (-not (Test-Path (Join-Path $repoRoot ".git"))) {
  Write-Error "No .git directory found. Run this from the repository root."
  exit 1
}

Copy-Item -Path (Join-Path $githooksSrc "pre-push") -Destination (Join-Path $githooksDest "pre-push") -Force
Copy-Item -Path (Join-Path $githooksSrc "post-merge") -Destination (Join-Path $githooksDest "post-merge") -Force
Write-Host "Hooks installed to $githooksDest"

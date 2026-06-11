Set-Location $PSScriptRoot

$workspaceVenv = Join-Path (Split-Path $PSScriptRoot -Parent) ".venv\Scripts\python.exe"
$repoVenv = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$python = if (Test-Path $workspaceVenv) { $workspaceVenv } elseif (Test-Path $repoVenv) { $repoVenv } else { "py" }

& $python "scripts\render_study_sheets.py" @args

exit $LASTEXITCODE

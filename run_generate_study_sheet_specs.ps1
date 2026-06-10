Set-Location $PSScriptRoot

& ".\.venv\Scripts\python.exe" "scripts\generate_study_sheet_specs.py" @args

exit $LASTEXITCODE

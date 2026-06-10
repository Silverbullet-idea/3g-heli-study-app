Set-Location $PSScriptRoot

& ".\.venv\Scripts\python.exe" "scripts\render_study_sheets.py" @args

exit $LASTEXITCODE

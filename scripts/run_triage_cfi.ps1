# Pre-triage for CFI bank — run before review server
# Pre-triage script — sorts FLAG questions into APPROVE/EDIT/ESCALATE
# Run BEFORE the review server to shrink Ryan's manual queue
# Expected output: ~85-90% of FLAGs resolved automatically

Set-Location $PSScriptRoot\..

Write-Host "Pre-triaging FLAG questions (CFI bank)..."
.\.venv\Scripts\python.exe scripts\triage_flag_questions.py --input question-bank/qbank_cfi_helicopter.json

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

exit $LASTEXITCODE

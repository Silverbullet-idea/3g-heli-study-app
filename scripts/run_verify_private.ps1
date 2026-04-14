Set-Location $PSScriptRoot\..

Write-Host "Verifying Private Pilot question bank (batched API)..."
.\.venv\Scripts\python.exe scripts\verify_question_bank.py --input question-bank/qbank_private_helicopter.json

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

exit $LASTEXITCODE

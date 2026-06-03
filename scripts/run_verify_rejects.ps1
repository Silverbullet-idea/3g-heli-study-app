Set-Location $PSScriptRoot\..
.\.venv\Scripts\python.exe scripts\verify_question_bank.py --input question-bank\qbank_rewritten_rejects.json
Write-Host "Verification complete. Next: run triage."

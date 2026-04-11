Set-Location $PSScriptRoot\..

Write-Host "Generating Private Pilot question bank..."
.\.venv\Scripts\python.exe scripts\generate_question_bank.py `
  --rating private

Write-Host "Done. Review question-bank\qbank_private_helicopter.json"

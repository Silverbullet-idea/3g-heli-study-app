Set-Location $PSScriptRoot\..
.\.venv\Scripts\python.exe scripts\merge_rewritten_questions.py --source question-bank\qbank_rewritten_rejects.json
Write-Host "Merge complete."

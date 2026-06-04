Set-Location $PSScriptRoot\..
.\.venv\Scripts\python.exe scripts\merge_rewritten_questions.py --source question-bank\qbank_rewritten_rejects.json --dry-run
Write-Host "Dry-run complete. No files modified."

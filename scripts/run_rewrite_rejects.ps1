Set-Location $PSScriptRoot\..
.\.venv\Scripts\python.exe scripts\rewrite_rejected_questions.py
Write-Host "Rewrite complete. Next: run verify then triage on qbank_rewritten_rejects.json"

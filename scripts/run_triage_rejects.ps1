Set-Location $PSScriptRoot\..
.\.venv\Scripts\python.exe scripts\triage_flag_questions.py --input question-bank\qbank_rewritten_rejects.json
Write-Host "Triage complete. Check triage_summary.txt for escalation count."

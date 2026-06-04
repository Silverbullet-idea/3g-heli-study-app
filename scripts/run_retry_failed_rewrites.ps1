Set-Location $PSScriptRoot\..
.\.venv\Scripts\python.exe scripts\retry_failed_rewrites.py
Write-Host "Retry complete. Check rewrite_errors.log for results."

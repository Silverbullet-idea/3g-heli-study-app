Set-Location $PSScriptRoot\..

Write-Host "=== Downloading Robinson Maintenance Manuals ==="
.\.venv\Scripts\python.exe scripts\populate_pdf_library.py `
  --manufacturer robinson

Write-Host "=== Downloading Lycoming Engine Manuals ==="
.\.venv\Scripts\python.exe scripts\populate_pdf_library.py `
  --manufacturer lycoming

Write-Host "=== Downloading FAA Handbooks and ACs ==="
.\.venv\Scripts\python.exe scripts\populate_pdf_library.py `
  --manufacturer faa

Write-Host "=== Complete. Check raw-pdfs\ subdirectories for output. ==="

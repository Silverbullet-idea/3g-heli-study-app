Set-Location $PSScriptRoot\..

Write-Host "--- Section 2: Limitations ---"
.\.venv\Scripts\python.exe scripts\extract_poh_json.py `
  --pdf raw-pdfs\robinson\r22_poh_2_a730a7b2f8.pdf `
  --section limitations

Write-Host "--- Section 3: Emergency Procedures ---"
.\.venv\Scripts\python.exe scripts\extract_poh_json.py `
  --pdf raw-pdfs\robinson\r22_poh_3_4bcbbbfc58.pdf `
  --section emergency_procedures

Write-Host "--- Section 7: Systems ---"
.\.venv\Scripts\python.exe scripts\extract_poh_json.py `
  --pdf raw-pdfs\robinson\r22_poh_7_6581e57af0.pdf `
  --section systems

Write-Host "--- Complete. Check extracted-data\aircraft\ for output files. ---"

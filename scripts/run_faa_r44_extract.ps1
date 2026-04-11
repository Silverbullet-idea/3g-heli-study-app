Set-Location $PSScriptRoot\..

$py = ".\.venv\Scripts\python.exe"
$script = "scripts\extract_poh_json.py"

Write-Host "=== FAA HANDBOOKS ==="

Write-Host "--- FAA Helicopter Flying Handbook ---"
& $py $script --pdf "raw-pdfs\faa\FAA-H-8083-21B_Helicopter_Flying_Handbook.pdf" --section faa_handbook

Write-Host "--- FAA Helicopter Instructor Handbook ---"
& $py $script --pdf "raw-pdfs\faa\FAA-H-8083-4_Helicopter_Instructors_Handbook.pdf" --section faa_handbook

Write-Host "--- FAA Instrument Flying Handbook ---"
& $py $script --pdf "raw-pdfs\faa\FAA-H-8083-15B_Instrument_Flying_Handbook.pdf" --section faa_handbook

Write-Host "--- FAA Weight and Balance Handbook ---"
& $py $script --pdf "raw-pdfs\faa\FAA-H-8083-1B_Weight_Balance_Handbook.pdf" --section faa_handbook

Write-Host "=== ACS DOCUMENTS ==="

Write-Host "--- Private Pilot Helicopter ACS ---"
& $py $script --pdf "raw-pdfs\faa\FAA-S-ACS-15_Private_Helicopter_ACS.pdf" --section faa_acs

Write-Host "--- Commercial Pilot Helicopter ACS ---"
& $py $script --pdf "raw-pdfs\faa\FAA-S-ACS-16_Commercial_Helicopter_ACS.pdf" --section faa_acs

Write-Host "--- CFI Helicopter ACS ---"
& $py $script --pdf "raw-pdfs\faa\FAA-S-ACS-29_CFI_Helicopter_ACS.pdf" --section faa_acs

Write-Host "--- Instrument Helicopter ACS ---"
& $py $script --pdf "raw-pdfs\faa\FAA-S-ACS-14_Instrument_Helicopter_ACS.pdf" --section faa_acs

Write-Host "=== R44 POH ==="

$baseUrl = "https://robinsonstrapistorprod.blob.core.windows.net/uploads/assets"
$r44Files = @{
  "r44_poh_2_0ef0d9066e.pdf" = "$baseUrl/r44_poh_2_0ef0d9066e.pdf"
  "r44_poh_3_2718c43333.pdf" = "$baseUrl/r44_poh_3_2718c43333.pdf"
  "r44_poh_7_f5e97cee3e.pdf" = "$baseUrl/r44_poh_7_f5e97cee3e.pdf"
}

foreach ($filename in $r44Files.Keys) {
  $dest = "raw-pdfs\robinson\$filename"
  if (-Not (Test-Path $dest)) {
    Write-Host "Downloading $filename..."
    Invoke-WebRequest -Uri $r44Files[$filename] -OutFile $dest
  } else {
    Write-Host "Already present: $filename"
  }
}

Write-Host "--- R44 Section 2: Limitations ---"
& $py $script --pdf "raw-pdfs\robinson\r44_poh_2_0ef0d9066e.pdf" --section r44_limitations

Write-Host "--- R44 Section 3: Emergency Procedures ---"
& $py $script --pdf "raw-pdfs\robinson\r44_poh_3_2718c43333.pdf" --section r44_emergency_procedures

Write-Host "--- R44 Section 7: Systems ---"
& $py $script --pdf "raw-pdfs\robinson\r44_poh_7_f5e97cee3e.pdf" --section r44_systems

Write-Host "=== ALL EXTRACTIONS COMPLETE ==="
Write-Host "Check extracted-data\aircraft\ and extracted-data\faa\ for output."

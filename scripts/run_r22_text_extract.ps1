$baseUrl = "https://robinsonstrapistorprod.blob.core.windows.net/uploads/assets"
$destDir = "raw-pdfs\robinson"

$files = @{
  "r22_poh_2_a730a7b2f8.pdf" = "$baseUrl/r22_poh_2_a730a7b2f8.pdf"
  "r22_poh_3_4bcbbbfc58.pdf" = "$baseUrl/r22_poh_3_4bcbbbfc58.pdf"
  "r22_poh_7_6581e57af0.pdf" = "$baseUrl/r22_poh_7_6581e57af0.pdf"
}

foreach ($filename in $files.Keys) {
  $dest = "$destDir\$filename"
  if (-Not (Test-Path $dest)) {
    Write-Host "Downloading $filename..."
    Invoke-WebRequest -Uri $files[$filename] -OutFile $dest
  } else {
    Write-Host "Already present: $filename"
  }
}

.\.venv\Scripts\python.exe scripts\extract_text.py `
  --pdf raw-pdfs\robinson\r22_poh_2_a730a7b2f8.pdf

.\.venv\Scripts\python.exe scripts\extract_text.py `
  --pdf raw-pdfs\robinson\r22_poh_3_4bcbbbfc58.pdf

.\.venv\Scripts\python.exe scripts\extract_text.py `
  --pdf raw-pdfs\robinson\r22_poh_7_6581e57af0.pdf

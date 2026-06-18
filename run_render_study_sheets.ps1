# run_render_study_sheets.ps1
# Regenerates all study sheet PDFs using the v2 renderer
# Output: output\study_sheets\
# Usage: .\run_render_study_sheets.ps1
# Usage (single aircraft): .\run_render_study_sheets.ps1 -Aircraft r22

param(
    [string]$Aircraft = ""
)

$python = ".\.venv\Scripts\python.exe"
$script = "scripts\render_study_sheets.py"

if ($Aircraft -ne "") {
    Write-Host "Rendering study sheets for aircraft: $Aircraft"
    & $python $script --aircraft $Aircraft
} else {
    Write-Host "Rendering all study sheets..."
    & $python $script
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Done. PDFs written to output\study_sheets\"
    Get-ChildItem output\study_sheets\ -Filter *.pdf | Select-Object Name, @{N='Size KB';E={[math]::Round($_.Length/1KB,1)}}
} else {
    Write-Host "Renderer exited with error code $LASTEXITCODE"
}

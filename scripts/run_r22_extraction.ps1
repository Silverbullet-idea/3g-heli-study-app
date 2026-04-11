# Requires ANTHROPIC_API_KEY (set in this shell or your user environment).
# Example: $env:ANTHROPIC_API_KEY = "<your-key>"
if (-not $env:ANTHROPIC_API_KEY) {
    Write-Error "ANTHROPIC_API_KEY is not set. Set it before running this script."
    exit 1
}

# PDF paths match files in raw-pdfs/robinson/ (AGENTS.md naming).
.\.venv\Scripts\python.exe scripts\extract_poh.py `
  --pdf raw-pdfs\robinson\r22_poh_section2_limitations.pdf `
  --section limitations

.\.venv\Scripts\python.exe scripts\extract_poh.py `
  --pdf raw-pdfs\robinson\r22_poh_section3_emergency_procedures.pdf `
  --section emergency_procedures

.\.venv\Scripts\python.exe scripts\extract_poh.py `
  --pdf raw-pdfs\robinson\r22_poh_section7_systems.pdf `
  --section systems

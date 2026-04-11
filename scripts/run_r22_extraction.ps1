# API key: optional here if ANTHROPIC_API_KEY is in .env (repo\.env or parent folder .env).
# Example: $env:ANTHROPIC_API_KEY = "<your-key>"

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

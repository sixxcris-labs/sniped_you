# === OCR Benchmark Runner ===
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\Activate.ps1
Write-Host "Running OCR benchmark..."
python tools\ocr_benchmark.py --limit 10 --timeout 10 --engines easyocr paddleocr --show-skipped


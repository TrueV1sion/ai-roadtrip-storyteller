# PowerShell script to fix all import issues in Python files
Write-Host "=== Fixing Backend Import Issues ===" -ForegroundColor Green

$fixedCount = 0
$errorCount = 0

# Get all Python files recursively
$pythonFiles = Get-ChildItem -Path . -Filter *.py -Recurse | Where-Object {
    $_.FullName -notmatch "(venv|__pycache__|\.git|\.pytest_cache)"
}

Write-Host "Found $($pythonFiles.Count) Python files to check" -ForegroundColor Yellow

foreach ($file in $pythonFiles) {
    try {
        $content = Get-Content $file.FullName -Raw -Encoding UTF8
        $originalContent = $content
        
        # Fix backend.app imports
        $content = $content -replace 'from backend\.app\.', 'from app.'
        $content = $content -replace 'import backend\.app\.', 'import app.'
        
        # Fix Vertex AI imports
        $content = $content -replace 'from vertexai\.preview\.generative_models', 'from vertexai.generative_models'
        
        # Only write if content changed
        if ($content -ne $originalContent) {
            Set-Content -Path $file.FullName -Value $content -Encoding UTF8 -NoNewline
            Write-Host "[FIXED] $($file.Name)" -ForegroundColor Green
            $fixedCount++
        }
    }
    catch {
        Write-Host "[ERROR] Failed to process $($file.Name): $_" -ForegroundColor Red
        $errorCount++
    }
}

Write-Host "`n=== Summary ===" -ForegroundColor Green
Write-Host "Files fixed: $fixedCount" -ForegroundColor Green
Write-Host "Errors: $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { "Red" } else { "Green" })

Write-Host "`nTo verify the fixes, run:" -ForegroundColor Yellow
Write-Host "  python verify_startup.py" -ForegroundColor Cyan
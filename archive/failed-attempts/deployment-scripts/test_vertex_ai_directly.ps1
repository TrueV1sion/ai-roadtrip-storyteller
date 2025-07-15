# Test Vertex AI directly to see what's happening
Write-Host "Testing Vertex AI directly..." -ForegroundColor Green

# Create a simple Python test script
$pythonScript = @'
import os
from google.cloud import aiplatform

# Initialize
project_id = "roadtrip-460720"
location = "us-central1"

print(f"Testing Vertex AI with project: {project_id}, location: {location}")

try:
    aiplatform.init(project=project_id, location=location)
    model = aiplatform.GenerativeModel("gemini-1.5-flash")
    
    prompt = """
    Tell an interesting fact about Detroit, Michigan.
    The story should be:
    - 2-3 sentences long
    - Educational or entertaining
    - Based on real facts about Detroit
    - Written in a friendly, engaging tone
    """
    
    response = model.generate_content(prompt)
    print("\nSuccess! Generated story:")
    print(response.text)
    
except Exception as e:
    print(f"\nError: {str(e)}")
    print(f"Error type: {type(e).__name__}")
'@

# Save the script
$pythonScript | Out-File -FilePath "test_vertex.py" -Encoding UTF8

Write-Host "`nRunning Vertex AI test..." -ForegroundColor Yellow

# Try different Python commands
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
} else {
    Write-Host "❌ Python not found in PATH" -ForegroundColor Red
    Write-Host "Please ensure Python is installed and in your PATH" -ForegroundColor Yellow
    
    # Try to find Python in common locations
    $commonPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe",
        "C:\Python*\python.exe",
        "$env:USERPROFILE\AppData\Local\Programs\Python\Python*\python.exe"
    )
    
    foreach ($path in $commonPaths) {
        $found = Get-ChildItem -Path $path -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) {
            $pythonCmd = $found.FullName
            Write-Host "Found Python at: $pythonCmd" -ForegroundColor Green
            break
        }
    }
}

if ($pythonCmd) {
    # Run the test
    & $pythonCmd test_vertex.py
} else {
    Write-Host "`nCouldn't find Python. Let's check Cloud Run logs instead..." -ForegroundColor Yellow
}

Write-Host "`n`nChecking Cloud Run logs for Vertex AI errors..." -ForegroundColor Cyan
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=roadtrip-mvp AND textPayload:'AI generation error'" --limit 10 --format="table(timestamp,textPayload)" --project=roadtrip-460720

# Check for credentials
if ($env:GOOGLE_APPLICATION_CREDENTIALS) {
    Write-Host "`nGOOGLE_APPLICATION_CREDENTIALS is set to: $env:GOOGLE_APPLICATION_CREDENTIALS" -ForegroundColor Green
    if (Test-Path $env:GOOGLE_APPLICATION_CREDENTIALS) {
        Write-Host "✅ File exists" -ForegroundColor Green
    } else {
        Write-Host "❌ File NOT found" -ForegroundColor Red
    }
} else {
    Write-Host "`n❌ GOOGLE_APPLICATION_CREDENTIALS is NOT set" -ForegroundColor Red
}

# Clean up
Remove-Item "test_vertex.py" -ErrorAction SilentlyContinue
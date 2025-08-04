# PowerShell script to run database migrations on Windows
param(
    [string]$Environment = "production",
    [string]$ProjectId = "roadtrip-460720",
    [string]$Instance = "roadtrip-db"
)

Write-Host "🗄️  Running Database Migrations" -ForegroundColor Blue
Write-Host "Environment: $Environment" -ForegroundColor Blue
Write-Host "Project: $ProjectId" -ForegroundColor Blue
Write-Host "Instance: $Instance" -ForegroundColor Blue

# Ensure we're in the right directory
if (!(Test-Path "alembic")) {
    Write-Host "❌ Error: Must run from project root directory" -ForegroundColor Red
    exit 1
}

# Check if alembic is installed
Write-Host "📦 Checking alembic installation..." -ForegroundColor Yellow
python -m pip show alembic > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing alembic..." -ForegroundColor Yellow
    python -m pip install alembic sqlalchemy psycopg2-binary python-dotenv
}

# Get Cloud SQL proxy if not installed
$proxyPath = ".\cloud_sql_proxy.exe"
if (!(Test-Path $proxyPath)) {
    Write-Host "📥 Downloading Cloud SQL Proxy..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.11.4/cloud-sql-proxy.x64.exe" -OutFile $proxyPath
}

# Start Cloud SQL proxy
Write-Host "🔌 Starting Cloud SQL Proxy..." -ForegroundColor Yellow
$proxyJob = Start-Job -ScriptBlock {
    param($path, $project, $instance)
    & $path --port 5433 "${project}:us-central1:${instance}"
} -ArgumentList $proxyPath, $ProjectId, $Instance

Start-Sleep -Seconds 3

# Set database URL for local connection through proxy
$env:DATABASE_URL = "postgresql://postgres@localhost:5433/postgres"

Write-Host "🏃 Running migrations..." -ForegroundColor Yellow

# Change to backend directory and run migrations
Set-Location backend
try {
    # Show current revision
    Write-Host "Current revision:" -ForegroundColor Blue
    python -m alembic current

    # Run migrations
    python -m alembic upgrade head

    # Show new revision
    Write-Host "✅ New revision:" -ForegroundColor Green
    python -m alembic current
}
finally {
    # Clean up
    Set-Location ..
    Stop-Job $proxyJob
    Remove-Job $proxyJob
}

Write-Host "🎉 Migrations completed successfully!" -ForegroundColor Green
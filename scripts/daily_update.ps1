# ============================================================================
# PAIC Econometrics - Daily Commodity Data Update Agent
# Runs download_commodities.R, then git add/commit/push to GitHub
# Scheduled via Windows Task Scheduler at 18:00 BRT daily
# ============================================================================

# --- Configuration -----------------------------------------------------------
$ProjectDir = "C:\Users\rodri\OneDrive - Grupo Marista\FAE Business School\PAIC 2025-26\Site_PAIC"
$RscriptPath = "C:\Program Files\R\R-4.4.1\bin\Rscript.exe"
$RScript = "$ProjectDir\download_commodities.R"
$LogDir = "$ProjectDir\scripts\logs"
$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$LogFile = "$LogDir\update_$Timestamp.log"

# --- Setup -------------------------------------------------------------------
Set-Location $ProjectDir

# Create log directory
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Start logging
Start-Transcript -Path $LogFile -Append

Write-Host "=============================================="
Write-Host "PAIC Daily Commodity Update Agent"
Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "=============================================="

# --- Step 1: Run R script to download commodity data -------------------------
Write-Host "`n[1/3] Running download_commodities.R ..."

try {
    $rOutput = & $RscriptPath $RScript 2>&1
    $rExitCode = $LASTEXITCODE
    Write-Host $rOutput
    
    if ($rExitCode -ne 0) {
        Write-Host "ERROR: R script failed with exit code $rExitCode"
        Stop-Transcript
        exit 1
    }
    Write-Host "[OK] R script completed successfully."
} catch {
    Write-Host "ERROR: Failed to execute R script: $_"
    Stop-Transcript
    exit 1
}

# --- Step 2: Check for changes -----------------------------------------------
Write-Host "`n[2/3] Checking for data changes ..."

$gitStatus = & git status --porcelain data/ 2>&1
if ([string]::IsNullOrWhiteSpace($gitStatus)) {
    Write-Host "[INFO] No changes detected in data/ directory. Skipping commit."
    Stop-Transcript
    exit 0
}

Write-Host "Changes detected:"
Write-Host $gitStatus

# --- Step 3: Git add, commit, and push ---------------------------------------
Write-Host "`n[3/3] Committing and pushing to GitHub ..."

$today = Get-Date -Format "yyyy-MM-dd"

try {
    & git add data/commodity_prices.csv data/commodity_prices_long.csv data/commodity_returns.csv
    & git commit -m "data: daily commodity update $today"
    & git push origin main
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Push successful!"
    } else {
        Write-Host "WARNING: Git push may have failed (exit code: $LASTEXITCODE)"
    }
} catch {
    Write-Host "ERROR: Git operations failed: $_"
    Stop-Transcript
    exit 1
}

Write-Host "`n=============================================="
Write-Host "Daily update completed at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "=============================================="

# Clean up old logs (keep last 30 days)
Get-ChildItem -Path $LogDir -Filter "update_*.log" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
    Remove-Item -Force

Stop-Transcript

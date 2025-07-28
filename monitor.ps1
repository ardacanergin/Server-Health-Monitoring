# === monitor.ps1 ===
# Native PowerShell script for running Server Health Monitor

Write-Host "[INFO] Starting Server Health Monitor..." -ForegroundColor Cyan

# ===== 1. Detect OS =====
$OS_TYPE = "windows"
Write-Host "[INFO] Detected OS: $OS_TYPE" -ForegroundColor Cyan

Write-Host "[INFO] Detected OS: $OS_TYPE" -ForegroundColor Cyan

# ===== 2. Check for venv =====
if (-Not (Test-Path "./venv")) {
    Write-Host "[ERROR] Virtual environment (venv) not found in current directory." -ForegroundColor Red
    Write-Host "[HINT] Run 'python -m venv venv' to create it." -ForegroundColor Yellow
    exit 1
}

# ===== 3. Activate venv =====
Write-Host "[INFO] Activating Python virtual environment..." -ForegroundColor Cyan
$venvPath = Join-Path $PWD "venv\Scripts\Activate.ps1"

if (Test-Path $venvPath) {
    try {
        & $venvPath
        Write-Host "[INFO] Virtual environment activated." -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Failed to activate virtual environment." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[ERROR] Activation script not found at $venvPath" -ForegroundColor Red
    exit 1
}

# ===== 4. Run Python script =====
Write-Host "[INFO] Running main.py..." -ForegroundColor Cyan

$pythonExe = Join-Path $PWD "venv\Scripts\python.exe"
$mainScript = Join-Path $PWD "main.py"

if (Test-Path $pythonExe) {
    & $pythonExe $mainScript
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[INFO] Monitoring completed successfully." -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Monitoring failed. Check logs for details." -ForegroundColor Red
    }
} else {
    Write-Host "[ERROR] Python executable not found in venv." -ForegroundColor Red
    exit 1
}

# ===== 5. Deactivate venv =====
Write-Host "[INFO] Deactivating virtual environment..." -ForegroundColor Cyan
deactivate 2>$null
Write-Host "[INFO] Virtual environment deactivated." -ForegroundColor Green

#!/bin/bash

# === Monitor Runner Script ===
# Runs the Python monitoring system cross-platform (Linux, macOS, Windows)

echo "[INFO] Starting Server Health Monitor..."

# ===== 1. Detect platform =====
OS_TYPE="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
elif [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "cygwin"* || "$OSTYPE" == "win32" ]]; then
    OS_TYPE="windows"
else
    echo "[ERROR] Unsupported OS: $OSTYPE"
    exit 1
fi
echo "[INFO] Detected OS: $OS_TYPE"

# ===== 2. Check for venv =====
if [ ! -d "venv" ]; then
    echo "[ERROR] Virtual environment (venv) not found in current directory."
    echo "[HINT] Run 'python -m venv venv' to create it."
    exit 1
fi

# ===== 3. Activate venv =====
echo "[INFO] Activating Python virtual environment..."
if [[ "$OS_TYPE" == "linux" || "$OS_TYPE" == "macos" ]]; then
    source venv/bin/activate
elif [[ "$OS_TYPE" == "windows" ]]; then
    if [ -f "venv/Scripts/activate" ]; then
        # Git Bash / WSL
        source venv/Scripts/activate
    elif [ -f "venv\\Scripts\\activate.bat" ]; then
        # CMD fallback
        call venv\\Scripts\\activate.bat
    elif [ -f "venv\\Scripts\\Activate.ps1" ]; then
        # PowerShell fallback
        powershell -ExecutionPolicy Bypass -File venv\\Scripts\\Activate.ps1
    else
        echo "[ERROR] Cannot find activation script for venv on Windows."
        exit 1
    fi
else
    echo "[ERROR] Unsupported OS for venv activation."
    exit 1
fi

# ===== 4. Run Python script =====
echo "[INFO] Running main.py..."
if [[ "$OS_TYPE" == "windows" ]]; then
    ./venv/Scripts/python.exe ./main.py
else
    python ./main.py
fi

if [ $? -eq 0 ]; then
    echo "[INFO] Monitoring completed successfully."
else
    echo "[ERROR] Monitoring failed. Check logs for details."
fi

# ===== 5. Deactivate venv =====
if type deactivate >/dev/null 2>&1; then
    deactivate
    echo "[INFO] Virtual environment deactivated."
else
    echo "[WARN] deactivate not found. Skipping."
fi

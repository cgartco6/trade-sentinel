# Requires -RunAsAdministrator
$ErrorActionPreference = "Stop"

Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "         TRADE SENTINEL OS -- AUTOMATED SETUP & DEPLOYMENT         " -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. OS Verification
$os = Get-CimInstance Win32_OperatingSystem
Write-Host "[*] Detecting OS: $($os.Caption) ($($os.OSArchitecture))" -ForegroundColor Yellow
if ($os.Caption -notlike "*Windows 10*" -and $os.Caption -notlike "*Windows 11*" -and $os.Caption -notlike "*Server*") {
    Write-Host "[!] Warning: Designed for Windows 10 Pro / Windows 11. Continuing execution..." -ForegroundColor DarkYellow
}

# 2. Function to Check / Download / Install Software
function Assert-Tool {
    param (
        [string]$CommandName,
        [string]$DownloadUrl,
        [string]$InstallerPath,
        [string]$SilentArgs
    )

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        Write-Host "[!] $CommandName not detected. Auto-downloading requirement..." -ForegroundColor Yellow
        $webClient = New-Object System.Net.WebClient
        Write-Host "[*] Downloading from $DownloadUrl ..." -ForegroundColor Gray
        $webClient.DownloadFile($DownloadUrl, $InstallerPath)

        Write-Host "[*] Executing silent installation..." -ForegroundColor Gray
        Start-Process -FilePath $InstallerPath -ArgumentList $SilentArgs -Wait -NoNewWindow
        
        # Refresh Environment Variables
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Remove-Item -Path $InstallerPath -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "[+] $CommandName detected." -ForegroundColor Green
    }
}

# Check Python 3.11+
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Assert-Tool -CommandName "python" `
                -DownloadUrl "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe" `
                -InstallerPath "$env:TEMP\python_installer.exe" `
                -SilentArgs "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0"
}

# Check Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Assert-Tool -CommandName "git" `
                -DownloadUrl "https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/Git-2.44.0-64-bit.exe" `
                -InstallerPath "$env:TEMP\git_installer.exe" `
                -SilentArgs "/VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS"
}

# 3. Virtual Environment Setup
$VENV_PATH = Join-Path $PSScriptRoot "venv"
if (-not (Test-Path $VENV_PATH)) {
    Write-Host "[*] Creating Python Virtual Environment..." -ForegroundColor Yellow
    python -m venv $VENV_PATH
}

$PYTHON_BIN = Join-Path $VENV_PATH "Scripts\python.exe"
$PIP_BIN = Join-Path $VENV_PATH "Scripts\pip.exe"

# 4. Dependency Installation
Write-Host "[*] Upgrading pip and installing Python package dependencies..." -ForegroundColor Yellow
& $PIP_BIN install --upgrade pip setuptools wheel --quiet
& $PIP_BIN install -r (Join-Path $PSScriptRoot "requirements.txt") uvicorn fastapi jinja2 --quiet

# 5. Environment Config Bootstrapping
$ENV_FILE = Join-Path $PSScriptRoot ".env"
$EXAMPLE_ENV = Join-Path $PSScriptRoot ".env.example"

if (-not (Test-Path $ENV_FILE)) {
    if (Test-Path $EXAMPLE_ENV) {
        Write-Host "[*] Creating .env file from .env.example..." -ForegroundColor Yellow
        Copy-Item $EXAMPLE_ENV $ENV_FILE
        Write-Host "[!] ALERT: Please edit the .env file with your real Alpaca, Telegram, and OpenAI API keys!" -ForegroundColor Red
    } else {
        Write-Host "[!] .env.example not found. Creating default .env template..." -ForegroundColor Yellow
        @"
ALPACA_API_KEY=your_alpaca_paper_api_key
ALPACA_SECRET_KEY=your_alpaca_paper_secret_key
ALPACA_PAPER=true
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
MAX_RISK_PER_TRADE_PCT=0.015
MIN_RR_RATIO=1.5
SCAN_INTERVAL_SECONDS=60
DATABASE_URL=sqlite:///./data/sentinel.db
"@ | Out-File -FilePath $ENV_FILE -Encoding utf8
    }
}

# 6. Database Initialization
Write-Host "[*] Initializing local database schema..." -ForegroundColor Yellow
& $PYTHON_BIN -c "from src.storage.models import init_db; init_db()"

# 7. Launch Platform Processes
Write-Host ""
Write-Host "===================================================================" -ForegroundColor Green
Write-Host "     LAUNCHING TRADE SENTINEL AGENTS & WEB COMMAND CENTER          " -ForegroundColor Green
Write-Host "===================================================================" -ForegroundColor Green
Write-Host "[*] Web Interface: http://localhost:8000" -ForegroundColor Cyan
Write-Host ""

# Start FastAPI Web Server in Background Process
$webProcess = Start-Process -FilePath $PYTHON_BIN `
                            -ArgumentList "-m uvicorn src.web.app:app --host 0.0.0.0 --port 8000" `
                            -PassThru `
                            -NoNewWindow

Start-Sleep -Seconds 3

# Open Default Web Browser
Start-Process "http://localhost:8000"

# Launch Main Sentinel Orchestrator in Foreground
& $PYTHON_BIN -m src.main

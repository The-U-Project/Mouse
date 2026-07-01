# Mouse Project - Windows 10 Setup Script
# Run this in PowerShell 5.1 as Administrator for best results
# Location: D:\Projects\source\U-Mouse\Mouse\.agents\setup-win10.ps1

$ErrorActionPreference = "Continue"
$ToolsDir = "D:\Projects\source\U-Mouse\tools"
$ProjectDir = "D:\Projects\source\U-Mouse\Mouse"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Mouse Project - Windows 10 Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Create tools directory
New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null

# ==============================
# 1. RUST (already installed, add to PATH)
# ==============================
Write-Host "[1/6] Configuring Rust..." -ForegroundColor Yellow
$RustBin = "$env:USERPROFILE\.cargo\bin"
if (Test-Path "$RustBin\rustc.exe") {
    $env:Path = "$RustBin;$env:Path"
    Write-Host "  Rust found at: $RustBin" -ForegroundColor Green
    rustc --version
    cargo --version
} else {
    Write-Host "  Rust NOT found! Installing via rustup..." -ForegroundColor Red
    Invoke-WebRequest -Uri "https://win.rustup.rs/x86_64" -OutFile "$env:TEMP\rustup-init.exe" -UseBasicParsing
    & "$env:TEMP\rustup-init.exe" -y --default-toolchain stable --target x86_64-pc-windows-msvc
    $env:Path = "$RustBin;$env:Path"
    rustc --version
    cargo --version
}

# ==============================
# 2. NODE.JS
# ==============================
Write-Host "[2/6] Installing Node.js..." -ForegroundColor Yellow
$NodeDir = "$ToolsDir\nodejs"
if (Get-Command node -ErrorAction SilentlyContinue) {
    Write-Host "  Node.js already in PATH" -ForegroundColor Green
    node --version
} elseif (Test-Path "$NodeDir\node.exe") {
    Write-Host "  Node.js found at: $NodeDir" -ForegroundColor Green
    $env:Path = "$NodeDir;$env:Path"
    node --version
} else {
    Write-Host "  Downloading Node.js..." -ForegroundColor Yellow
    $NodeUrl = "https://nodejs.org/dist/v22.12.0/node-v22.12.0-win-x64.zip"
    Invoke-WebRequest -Uri $NodeUrl -OutFile "$env:TEMP\nodejs.zip" -UseBasicParsing
    Write-Host "  Extracting..." -ForegroundColor Yellow
    Expand-Archive "$env:TEMP\nodejs.zip" -DestinationPath $ToolsDir -Force
    Rename-Item "$ToolsDir\node-v22.12.0-win-x64" $NodeDir -Force -ErrorAction SilentlyContinue
    $env:Path = "$NodeDir;$env:Path"
    Write-Host "  Node.js installed" -ForegroundColor Green
    node --version
    npm --version
}

# ==============================
# 3. BUN
# ==============================
Write-Host "[3/6] Installing Bun..." -ForegroundColor Yellow
if (Get-Command bun -ErrorAction SilentlyContinue) {
    Write-Host "  Bun already in PATH" -ForegroundColor Green
    bun --version
} else {
    Write-Host "  Installing Bun via npm..." -ForegroundColor Yellow
    npm install -g bun 2>&1 | Out-Null
    if (Get-Command bun -ErrorAction SilentlyContinue) {
        Write-Host "  Bun installed" -ForegroundColor Green
        bun --version
    } else {
        Write-Host "  Trying winget..." -ForegroundColor Yellow
        winget install Oven-sh.Bun --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        if (Get-Command bun -ErrorAction SilentlyContinue) {
            Write-Host "  Bun installed via winget" -ForegroundColor Green
            bun --version
        } else {
            Write-Host "  WARNING: Bun install may need terminal restart" -ForegroundColor Magenta
        }
    }
}

# ==============================
# 4. PHP 8.5
# ==============================
Write-Host "[4/6] Installing PHP 8.5..." -ForegroundColor Yellow
$PhpDir = "$ToolsDir\php"
if (Get-Command php -ErrorAction SilentlyContinue) {
    Write-Host "  PHP already in PATH" -ForegroundColor Green
    php --version
} elseif (Test-Path "$PhpDir\php.exe") {
    Write-Host "  PHP found at: $PhpDir" -ForegroundColor Green
    $env:Path = "$PhpDir;$env:Path"
    php --version
} else {
    Write-Host "  Downloading PHP 8.5..." -ForegroundColor Yellow
    $PhpUrl = "https://windows.php.net/downloads/releases/php-8.5.0-nts-Win32-vs17-x64.zip"
    try {
        Invoke-WebRequest -Uri $PhpUrl -OutFile "$env:TEMP\php.zip" -UseBasicParsing
        Write-Host "  Extracting..." -ForegroundColor Yellow
        Expand-Archive "$env:TEMP\php.zip" -DestinationPath $PhpDir -Force
        # Copy php.ini
        if (Test-Path "$PhpDir\php.ini-development") {
            Copy-Item "$PhpDir\php.ini-development" "$PhpDir\php.ini" -Force
        }
        $env:Path = "$PhpDir;$env:Path"
        Write-Host "  PHP installed" -ForegroundColor Green
        php --version
    } catch {
        Write-Host "  PHP download failed: $_" -ForegroundColor Red
        Write-Host "  Trying alternative URL..." -ForegroundColor Yellow
        $PhpUrl2 = "https://windows.php.net/downloads/releases/php-8.4.7-nts-Win32-vs17-x64.zip"
        Invoke-WebRequest -Uri $PhpUrl2 -OutFile "$env:TEMP\php.zip" -UseBasicParsing
        Expand-Archive "$env:TEMP\php.zip" -DestinationPath $PhpDir -Force
        $env:Path = "$PhpDir;$env:Path"
        php --version
    }
}

# ==============================
# 5. MINIFORGE (mamba + Python)
# ==============================
Write-Host "[5/6] Installing Miniforge (mamba)..." -ForegroundColor Yellow
$MambaRoot = "$ToolsDir\miniforge"
if (Get-Command mamba -ErrorAction SilentlyContinue) {
    Write-Host "  mamba already in PATH" -ForegroundColor Green
    mamba --version
} elseif (Get-Command conda -ErrorAction SilentlyContinue) {
    Write-Host "  conda found, installing mamba..." -ForegroundColor Yellow
    conda install -n base -c conda-forge mamba -y 2>&1 | Out-Null
} elseif (Test-Path "$MambaRoot\Scripts\mamba.exe") {
    Write-Host "  Miniforge found at: $MambaRoot" -ForegroundColor Green
    $env:Path = "$MambaRoot\Scripts;$MambaRoot;$MambaRoot\condabin;$env:Path"
    mamba --version
} else {
    Write-Host "  Downloading Miniforge..." -ForegroundColor Yellow
    $MambaUrl = "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe"
    try {
        Invoke-WebRequest -Uri $MambaUrl -OutFile "$env:TEMP\Miniforge3.exe" -UseBasicParsing
        Write-Host "  Installing Miniforge (silent)..." -ForegroundColor Yellow
        & "$env:TEMP\Miniforge3.exe" /InstallationType=JustMe /RegisterPython=0 /S /D=$MambaRoot
        $env:Path = "$MambaRoot\Scripts;$MambaRoot;$MambaRoot\condabin;$env:Path"
        Write-Host "  Miniforge installed" -ForegroundColor Green
        mamba --version
    } catch {
        Write-Host "  Miniforge download failed: $_" -ForegroundColor Red
    }
}

# ==============================
# 6. UV (Python package manager)
# ==============================
Write-Host "[6/6] Installing uv..." -ForegroundColor Yellow
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "  uv already in PATH" -ForegroundColor Green
    uv --version
} else {
    Write-Host "  Installing uv via pip/standalone..." -ForegroundColor Yellow
    try {
        pip install uv 2>&1 | Out-Null
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            Write-Host "  uv installed via pip" -ForegroundColor Green
            uv --version
        }
    } catch {
        Write-Host "  Trying standalone installer..." -ForegroundColor Yellow
        $UvUrl = "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"
        Invoke-WebRequest -Uri $UvUrl -OutFile "$env:TEMP\uv.zip" -UseBasicParsing
        Expand-Archive "$env:TEMP\uv.zip" -DestinationPath "$ToolsDir\uv" -Force
        $env:Path = "$ToolsDir\uv;$env:Path"
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            Write-Host "  uv installed" -ForegroundColor Green
            uv --version
        }
    }
}

# ==============================
# SETUP ENVIRONMENT VARIABLES
# ==============================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setting Up Environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Create .env from .env.example if it doesn't exist
if (-not (Test-Path "$ProjectDir\.env") -and (Test-Path "$ProjectDir\.env.example")) {
    Copy-Item "$ProjectDir\.env.example" "$ProjectDir\.env"
    Write-Host "  Created .env from .env.example" -ForegroundColor Green
}

# ==============================
# VERIFICATION
# ==============================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allOk = $true

Write-Host "--- Rust ---" -ForegroundColor Yellow
try { rustc --version; cargo --version } catch { Write-Host "  FAILED" -ForegroundColor Red; $allOk = $false }

Write-Host "--- Python ---" -ForegroundColor Yellow
try { python --version } catch { Write-Host "  FAILED" -ForegroundColor Red; $allOk = $false }

Write-Host "--- Node.js ---" -ForegroundColor Yellow
try { node --version; npm --version } catch { Write-Host "  Not found (may need PATH refresh)" -ForegroundColor Magenta }

Write-Host "--- Bun ---" -ForegroundColor Yellow
try { bun --version } catch { Write-Host "  Not found (may need terminal restart)" -ForegroundColor Magenta }

Write-Host "--- PHP ---" -ForegroundColor Yellow
try { php --version } catch { Write-Host "  Not found" -ForegroundColor Magenta }

Write-Host "--- mamba ---" -ForegroundColor Yellow
try { mamba --version } catch { Write-Host "  Not found (may need terminal restart)" -ForegroundColor Magenta }

Write-Host "--- uv ---" -ForegroundColor Yellow
try { uv --version } catch { Write-Host "  Not found" -ForegroundColor Magenta }

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Next Steps" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Restart your terminal to refresh PATH"
Write-Host "2. Create the conda environment:"
Write-Host "   mamba create -n mouse python=3.14 -y"
Write-Host "   mamba activate mouse"
Write-Host "3. Install Python dependencies:"
Write-Host "   uv pip install -e Source/Python"
Write-Host "4. Build the project:"
Write-Host "   cargo build"
Write-Host "   cmake -B build -G Ninja -S Source/C++"
Write-Host "   cmake --build build"
Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green

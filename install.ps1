# Helix Swarm Windows 一键安装脚本
# 用法：irm https://raw.githubusercontent.com/Yule-Cai/Helix-Swarm/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

$REPO        = "https://github.com/Yule-Cai/Helix-Swarm.git"
$INSTALL_DIR = "$env:USERPROFILE\helix-swarm"
$MAOS_DIR    = "$INSTALL_DIR\maos"
$VENV_DIR    = "$INSTALL_DIR\.venv"

# ── 颜色输出 ──────────────────────────────────────────────────
function Info    { param($msg) Write-Host "[Helix] $msg" -ForegroundColor Cyan }
function Success { param($msg) Write-Host "[Helix] ✅ $msg" -ForegroundColor Green }
function Warn    { param($msg) Write-Host "[Helix] ⚠️  $msg" -ForegroundColor Yellow }
function Err     { param($msg) Write-Host "[Helix] ❌ $msg" -ForegroundColor Red; exit 1 }

# ── Banner ────────────────────────────────────────────────────
Write-Host @"
  _   _      _ _       ____                                
 | | | | ___| (_)_  __/ ___|_      ____ _ _ __ _ __ ___  
 | |_| |/ _ \ | \/ \/ /\___ \ \ /\ / / _\ | '__| '_ \ _ \
 |  _  |  __/ | |>  <  ___) \ V  V / (_| | |  | | | | | |
 |_| |_|\___|_|_/_/\_\|____/ \_/\_/ \__,_|_|  |_| |_| |_|

  Helix Swarm 本地多智能体编程助手 — Windows 一键安装
"@ -ForegroundColor Magenta

# ── 检测 Python ───────────────────────────────────────────────
Info "检测 Python 版本..."
$PYTHON = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($ver) {
            $parts = $ver.Split(".")
            if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 11) {
                $PYTHON = $cmd
                Success "找到 Python $ver ($cmd)"
                break
            }
        }
    } catch {}
}

if (-not $PYTHON) {
    Warn "未找到 Python 3.11+，正在通过 winget 安装..."
    try {
        winget install -e --id Python.Python.3.13 --silent --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        $PYTHON = "python"
        Success "Python 安装完成"
    } catch {
        Err "自动安装 Python 失败，请从 https://python.org 手动安装 Python 3.11+ 后重试"
    }
}

# ── 检测 Git ──────────────────────────────────────────────────
Info "检测 Git..."
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Warn "未找到 Git，正在安装..."
    try {
        winget install -e --id Git.Git --silent --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    } catch {
        Err "Git 安装失败，请从 https://git-scm.com 手动安装"
    }
}
Success "Git 已就绪"

# ── 克隆 / 更新仓库 ───────────────────────────────────────────
if (Test-Path "$INSTALL_DIR\.git") {
    Info "检测到已有安装，更新中..."
    git -C $INSTALL_DIR pull --ff-only
} else {
    Info "克隆 Helix Swarm 到 $INSTALL_DIR ..."
    git clone $REPO $INSTALL_DIR
}
Success "代码已就绪"

# ── 创建虚拟环境 ──────────────────────────────────────────────
Info "创建 Python 虚拟环境..."
if (-not (Test-Path $VENV_DIR)) {
    & $PYTHON -m venv $VENV_DIR
}
$PIP    = "$VENV_DIR\Scripts\pip.exe"
$PYVENV = "$VENV_DIR\Scripts\python.exe"
Success "虚拟环境就绪"

# ── 安装依赖 ──────────────────────────────────────────────────
Info "安装 Python 依赖（首次安装 chromadb 需要 1-2 分钟）..."
& $PIP install --upgrade pip -q
& $PIP install -r "$MAOS_DIR\requirements.txt" -q
& $PIP install websockets -q
Success "依赖安装完成"

# ── 创建 helix.ps1 启动脚本 ───────────────────────────────────
Info "创建 helix 快捷命令..."
$LAUNCHER = "$INSTALL_DIR\helix.ps1"

@"
# Helix Swarm 启动器
`$PYVENV  = "$VENV_DIR\Scripts\python.exe"
`$MAOS    = "$MAOS_DIR"

switch (`$args[0]) {
    `$null {
        Write-Host "🧬 启动 Helix Swarm..." -ForegroundColor Cyan
        Set-Location `$MAOS
        & `$PYVENV web_ui.py
    }
    "qq" {
        Write-Host "📱 启动 QQ 网关..." -ForegroundColor Cyan
        Set-Location `$MAOS
        & `$PYVENV gateway/qq_gateway.py
    }
    "update" {
        Write-Host "🔄 更新 Helix Swarm..." -ForegroundColor Cyan
        git -C "$INSTALL_DIR" pull --ff-only
        & "$VENV_DIR\Scripts\pip.exe" install -r "$MAOS_DIR\requirements.txt" -q
        Write-Host "✅ 更新完成" -ForegroundColor Green
    }
    "doctor" {
        Write-Host "🩺 诊断环境..." -ForegroundColor Cyan
        & `$PYVENV -c "import flask, chromadb, requests, mcp, websockets; print('✅ 所有依赖正常')"
        try { Invoke-WebRequest -Uri http://127.0.0.1:5000/ -UseBasicParsing -TimeoutSec 2 | Out-Null; Write-Host "✅ Helix Swarm 运行中" -ForegroundColor Green }
        catch { Write-Host "⚠️  Helix Swarm 未运行" -ForegroundColor Yellow }
        try { Invoke-WebRequest -Uri http://127.0.0.1:3000/ -UseBasicParsing -TimeoutSec 2 | Out-Null; Write-Host "✅ NapCat HTTP 运行中" -ForegroundColor Green }
        catch { Write-Host "⚠️  NapCat 未运行" -ForegroundColor Yellow }
    }
    default {
        Write-Host "用法："
        Write-Host "  helix          启动 Helix Swarm Web UI"
        Write-Host "  helix qq       启动 QQ 网关"
        Write-Host "  helix update   更新到最新版本"
        Write-Host "  helix doctor   诊断环境"
    }
}
"@ | Set-Content $LAUNCHER -Encoding UTF8

# 创建全局 helix.bat，加入 PATH
$BAT_PATH = "$env:USERPROFILE\AppData\Local\Microsoft\WindowsApps\helix.cmd"
@"
@echo off
powershell -ExecutionPolicy Bypass -File "$LAUNCHER" %*
"@ | Set-Content $BAT_PATH -Encoding ASCII

# ── 初始化 config.json ────────────────────────────────────────
$CONFIG = "$MAOS_DIR\config.json"
if (-not (Test-Path $CONFIG)) {
    @"
{
  "llm_api_url": "http://localhost:1234/v1",
  "llm_model": "local-model",
  "llm_timeout": 600,
  "ui_language": "zh",
  "ui_dark_mode": true,
  "agent_mode_default": false,
  "skill_library_enabled": true,
  "enhanced_memory_enabled": true,
  "qq_napcat_http": "http://127.0.0.1:3000",
  "qq_gateway_port": 6700,
  "qq_access_token": "",
  "qq_allowlist": [],
  "qq_agent_mode": false
}
"@ | Set-Content $CONFIG -Encoding UTF8
    Info "已生成默认 config.json"
}

# ── 完成 ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "  🎉 Helix Swarm 安装完成！" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "  启动 Helix Swarm：" -ForegroundColor White
Write-Host "    helix" -ForegroundColor Cyan
Write-Host ""
Write-Host "  启动 QQ 网关（需先启动 NapCatQQ）：" -ForegroundColor White
Write-Host "    helix qq" -ForegroundColor Cyan
Write-Host ""
Write-Host "  更新：" -ForegroundColor White
Write-Host "    helix update" -ForegroundColor Cyan
Write-Host ""
Write-Host "  安装目录：$INSTALL_DIR" -ForegroundColor Gray
Write-Host "  配置文件：$CONFIG" -ForegroundColor Gray
Write-Host ""
Write-Host "  提示：先在 LM Studio 启动本地模型（端口 1234）" -ForegroundColor Yellow
Write-Host "        或修改 config.json 使用云端 API" -ForegroundColor Yellow
Write-Host ""
Write-Host "  新开一个 PowerShell 窗口后即可使用 helix 命令" -ForegroundColor Yellow
Write-Host ""

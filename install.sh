#!/usr/bin/env bash
# Helix Swarm 一键安装脚本
# 用法：curl -fsSL https://raw.githubusercontent.com/Yule-Cai/Helix-Swarm/main/install.sh | bash

set -e

REPO="https://github.com/Yule-Cai/Helix-Swarm.git"
INSTALL_DIR="$HOME/helix-swarm"
PYTHON_MIN="3.11"

# ── 颜色 ─────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[Helix]${RESET} $*"; }
success() { echo -e "${GREEN}[Helix]${RESET} ✅ $*"; }
warn()    { echo -e "${YELLOW}[Helix]${RESET} ⚠️  $*"; }
error()   { echo -e "${RED}[Helix]${RESET} ❌ $*"; exit 1; }

# ── Banner ────────────────────────────────────────────────────
echo -e "${BOLD}"
cat << 'EOF'
  _   _      _ _       ____                                
 | | | | ___| (_)_  __/ ___|_      ____ _ _ __ _ __ ___  
 | |_| |/ _ \ | \ \/ /\___ \ \ /\ / / _` | '__| '_ ` _ \ 
 |  _  |  __/ | |>  <  ___) \ V  V / (_| | |  | | | | | |
 |_| |_|\___|_|_/_/\_\|____/ \_/\_/ \__,_|_|  |_| |_| |_|
                                                           
  🧬 本地多智能体编程助手 — 一键安装
EOF
echo -e "${RESET}"

# ── 检测操作系统 ──────────────────────────────────────────────
OS="$(uname -s)"
case "$OS" in
  Linux*)   PLATFORM="linux" ;;
  Darwin*)  PLATFORM="macos" ;;
  *)        error "不支持的系统：$OS（Windows 请使用 install.ps1）" ;;
esac
info "检测到系统：$PLATFORM"

# ── 检测 Python ───────────────────────────────────────────────
info "检测 Python 版本…"
PYTHON=""
for cmd in python3.13 python3.12 python3.11 python3 python; do
  if command -v "$cmd" &>/dev/null; then
    VER=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
    MAJOR=$(echo "$VER" | cut -d. -f1)
    MINOR=$(echo "$VER" | cut -d. -f2)
    if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 11 ]; then
      PYTHON="$cmd"
      success "找到 Python $VER ($cmd)"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  warn "未找到 Python 3.11+，尝试自动安装…"
  if [ "$PLATFORM" = "linux" ]; then
    if command -v apt-get &>/dev/null; then
      sudo apt-get update -qq && sudo apt-get install -y python3.11 python3.11-venv python3-pip
      PYTHON="python3.11"
    elif command -v dnf &>/dev/null; then
      sudo dnf install -y python3.11
      PYTHON="python3.11"
    else
      error "无法自动安装 Python，请手动安装 Python 3.11+ 后重试"
    fi
  elif [ "$PLATFORM" = "macos" ]; then
    if command -v brew &>/dev/null; then
      brew install python@3.11
      PYTHON="python3.11"
    else
      error "请先安装 Homebrew (https://brew.sh) 或手动安装 Python 3.11+"
    fi
  fi
fi

# ── 检测 Git ──────────────────────────────────────────────────
info "检测 Git…"
if ! command -v git &>/dev/null; then
  warn "未找到 Git，尝试安装…"
  if [ "$PLATFORM" = "linux" ]; then
    sudo apt-get install -y git 2>/dev/null || sudo dnf install -y git 2>/dev/null
  elif [ "$PLATFORM" = "macos" ]; then
    xcode-select --install 2>/dev/null || brew install git
  fi
fi
command -v git &>/dev/null || error "Git 安装失败，请手动安装"
success "Git 已就绪"

# ── 克隆仓库 ──────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
  info "检测到已有安装，更新中…"
  git -C "$INSTALL_DIR" pull --ff-only || warn "更新失败，继续使用现有版本"
else
  info "克隆 Helix Swarm 到 $INSTALL_DIR …"
  git clone "$REPO" "$INSTALL_DIR"
fi
success "代码已就绪"

# ── 创建虚拟环境 ──────────────────────────────────────────────
VENV_DIR="$INSTALL_DIR/.venv"
info "创建 Python 虚拟环境…"
if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON" -m venv "$VENV_DIR"
fi
PIP="$VENV_DIR/bin/pip"
PYTHON_VENV="$VENV_DIR/bin/python"
success "虚拟环境就绪：$VENV_DIR"

# ── 安装依赖 ──────────────────────────────────────────────────
info "安装 Python 依赖（首次安装 chromadb 可能需要 1-2 分钟）…"
"$PIP" install --upgrade pip -q
"$PIP" install -r "$INSTALL_DIR/maos/requirements.txt" -q
# QQ 网关额外依赖
"$PIP" install websockets -q
success "依赖安装完成"

# ── 写入 helix 启动命令 ───────────────────────────────────────
info "创建 helix 快捷命令…"

LAUNCHER="$INSTALL_DIR/helix"
cat > "$LAUNCHER" << SCRIPT
#!/usr/bin/env bash
# Helix Swarm 启动器
INSTALL_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
VENV="\$INSTALL_DIR/.venv/bin/python"
MAOS="\$INSTALL_DIR/maos"

case "\${1:-}" in
  "")
    echo "🧬 启动 Helix Swarm…"
    cd "\$MAOS" && "\$VENV" web_ui.py
    ;;
  qq)
    echo "📱 启动 QQ 网关…"
    cd "\$MAOS" && "\$VENV" gateway/qq_gateway.py \${@:2}
    ;;
  update)
    echo "🔄 更新 Helix Swarm…"
    git -C "\$INSTALL_DIR" pull --ff-only
    "\$INSTALL_DIR/.venv/bin/pip" install -r "\$MAOS/requirements.txt" -q
    echo "✅ 更新完成"
    ;;
  doctor)
    echo "🩺 诊断 Helix Swarm…"
    "\$VENV" -c "import flask, chromadb, requests, mcp, websockets; print('✅ 所有依赖正常')"
    curl -s http://127.0.0.1:5000/ > /dev/null && echo "✅ Helix Swarm 运行中" || echo "⚠️  Helix Swarm 未运行"
    curl -s http://127.0.0.1:3000/ > /dev/null && echo "✅ NapCat HTTP 运行中" || echo "⚠️  NapCat 未运行"
    ;;
  *)
    echo "用法："
    echo "  helix          启动 Helix Swarm Web UI"
    echo "  helix qq       启动 QQ 网关"
    echo "  helix update   更新到最新版本"
    echo "  helix doctor   诊断环境"
    ;;
esac
SCRIPT

chmod +x "$LAUNCHER"

# 尝试安装到 PATH
if [ -d "$HOME/.local/bin" ]; then
  ln -sf "$LAUNCHER" "$HOME/.local/bin/helix"
  HELIX_CMD="helix"
elif [ -w "/usr/local/bin" ]; then
  ln -sf "$LAUNCHER" "/usr/local/bin/helix"
  HELIX_CMD="helix"
else
  HELIX_CMD="$LAUNCHER"
fi

# ── 初始化配置 ────────────────────────────────────────────────
CONFIG_FILE="$INSTALL_DIR/maos/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
  cat > "$CONFIG_FILE" << 'JSON'
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
JSON
  info "已生成默认 config.json"
fi

# ── 完成 ──────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}${BOLD}  🎉 Helix Swarm 安装完成！${RESET}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "  ${BOLD}启动 Helix Swarm：${RESET}"
echo -e "    ${CYAN}$HELIX_CMD${RESET}"
echo ""
echo -e "  ${BOLD}启动 QQ 网关（需要先启动 NapCatQQ）：${RESET}"
echo -e "    ${CYAN}$HELIX_CMD qq${RESET}"
echo ""
echo -e "  ${BOLD}更新：${RESET}"
echo -e "    ${CYAN}$HELIX_CMD update${RESET}"
echo ""
echo -e "  ${BOLD}安装目录：${RESET} $INSTALL_DIR"
echo -e "  ${BOLD}配置文件：${RESET} $CONFIG_FILE"
echo ""
echo -e "  ${YELLOW}提示：先在 LM Studio 启动本地模型服务（端口 1234）${RESET}"
echo -e "  ${YELLOW}      或修改 config.json 使用云端 API${RESET}"
echo ""

# 检查 PATH
if ! command -v helix &>/dev/null 2>&1; then
  echo -e "  ${YELLOW}将以下内容加入 ~/.bashrc 或 ~/.zshrc 以使用 helix 命令：${RESET}"
  echo -e "    ${CYAN}export PATH=\"\$HOME/.local/bin:\$PATH\"${RESET}"
  echo ""
fi

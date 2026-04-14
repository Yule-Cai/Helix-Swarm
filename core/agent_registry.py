"""
AgentRegistry — Agent 自动发现与动态注册（双语版）

设计目标：
  - 扫描 agents/ 目录，自动发现所有 agent
  - 每个 agent 文件定义 DESCRIPTION（英文）和 DESCRIPTION_ZH（中文）
  - 根据 config.json 的 ui_language 自动选择语言注入 Planner
  - TaskPlanner 从 Registry 获取描述，不再硬编码 AGENT_REGISTRY
  - 新增 agent 只需放文件，零配置

Agent 文件规范（agents/<n>/agent.py）：

  DESCRIPTION    = "Write or modify source code files"   # 英文（必须）
  DESCRIPTION_ZH = "编写或修改源代码文件，支持 <file> 标签"  # 中文（可选）

  class CoderAgent:
      def __init__(self, llm_client=None): ...
      def run(self, instruction: str, workspace_dir: str) -> str: ...

兼容：没有 DESCRIPTION 的旧 agent 自动使用 fallback 表，不报错。
      没有 DESCRIPTION_ZH 的 agent 中文模式下回退到英文描述。
"""
from __future__ import annotations
import os
import sys
import json
import importlib
import inspect
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parent.parent
AGENTS_DIR  = BASE_DIR / "agents"
CONFIG_FILE = BASE_DIR / "config.json"


def _load_lang() -> str:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("ui_language", "en")
    except Exception:
        return "en"


_FALLBACK_EN: dict[str, str] = {
    "viewer":       "Scan and read workspace directory structure and file contents",
    "cleaner":      "Remove leftover or temporary files from the workspace",
    "coder":        "Write or modify source code files, supports <file> tags and markdown blocks",
    "tester":       "Run code to verify functionality, handles interactive programs via stdin simulation",
    "debugger":     "Deep error analysis — reads source + traceback, outputs a fully fixed file",
    "reviewer":     "Code quality review, rewrites improved version back to disk",
    "terminal":     "Execute shell commands: pip install, compile, run scripts, system operations",
    "searcher":     "GitHub search for API docs, error solutions, and code references",
    "browser":      "Fetch and extract readable content from web pages",
    "doc":          "Generate README.md documentation for the current project",
    "writer":       "Write fiction, story prose, essays or any creative text content",
    "statemanager": "Extract novel character state from chapters and update JSON state file",
    "visualizer":   "Generate Mermaid flowcharts or architecture diagrams as PNG",
    "skill":        "Query skill library and recommend reusable task templates",
    "selfimprove":  "Analyze system weak points and generate actionable improvement suggestions",
    "mcp":          "Connect to any external tool or service via MCP protocol",
    "plugin":       "Wrap third-party GitHub projects as directly callable agent capabilities",
}

_FALLBACK_ZH: dict[str, str] = {
    "viewer":       "扫描并读取工作区目录结构和文件内容",
    "cleaner":      "清理工作区中遗留的临时文件或目录",
    "coder":        "编写或修改源代码文件，支持 <file> 标签和 Markdown 代码块",
    "tester":       "运行代码验证功能，通过 stdin 模拟处理交互式程序",
    "debugger":     "深度错误分析：读取源码和报错，直接输出修复后的完整文件",
    "reviewer":     "代码质量审查，将改进版本直接写回磁盘",
    "terminal":     "执行 Shell 命令：pip 安装、编译、运行脚本等系统操作",
    "searcher":     "GitHub 搜索：API 文档、报错解决方案、代码参考",
    "browser":      "抓取并提取网页的可读内容",
    "doc":          "为当前项目生成 README.md 文档",
    "writer":       "撰写小说、故事散文、随笔或任何创意文字内容",
    "statemanager": "从章节中提取小说人物状态并更新 JSON 状态文件",
    "visualizer":   "生成 Mermaid 流程图或架构图（输出为 PNG）",
    "skill":        "查询技能库，为相似请求推荐可复用的任务模板",
    "selfimprove":  "分析系统薄弱点，输出可操作的改进建议",
    "mcp":          "通过 MCP 协议连接任意外部工具或服务",
    "plugin":       "将第三方 GitHub 项目封装为可直接调用的 Agent 能力",
}


class AgentEntry:
    def __init__(self, name, module, cls, description_en, description_zh, requires_llm):
        self.name           = name
        self.module         = module
        self.cls            = cls
        self.description_en = description_en
        self.description_zh = description_zh
        self.requires_llm   = requires_llm
        self._instance      = None

    def get_description(self, lang: str = "en") -> str:
        if lang == "zh" and self.description_zh:
            return self.description_zh
        return self.description_en

    def instantiate(self, llm_client=None):
        if self._instance is None:
            self._instance = self._create(llm_client)
        return self._instance

    def fresh(self, llm_client=None):
        return self._create(llm_client)

    def _create(self, llm_client=None):
        if self.requires_llm and llm_client is not None:
            return self.cls(llm_client)
        try:
            return self.cls(llm_client) if self.requires_llm else self.cls()
        except TypeError:
            return self.cls()


class AgentRegistry:
    """
    Agent 注册表 — 自动扫描 agents/ 目录，支持中英双语描述。

    用法：
        registry = AgentRegistry()               # 自动读取 config.json 语言
        desc     = registry.format_for_planner() # 按当前语言生成描述
        agents   = registry.build_all(llm)       # 实例化所有 Agent
        coder    = registry.build_one("coder", llm)
        registry.set_lang("zh")                  # 手动切换语言
        print(registry.summary())                # 调试：查看所有双语描述
    """

    def __init__(self, disabled: list[str] = None, lang: str = None):
        self._entries:  dict[str, AgentEntry] = {}
        self._disabled: set[str] = set(disabled or [])
        self._lang: str = lang or _load_lang()
        self._discover()

    def set_lang(self, lang: str):
        self._lang = lang

    def reload_lang(self):
        self._lang = _load_lang()

    def _discover(self):
        if not AGENTS_DIR.exists():
            return
        root_str = str(BASE_DIR)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)
        for agent_dir in sorted(AGENTS_DIR.iterdir()):
            if not agent_dir.is_dir():
                continue
            agent_file = agent_dir / "agent.py"
            if not agent_file.exists():
                continue
            name = agent_dir.name
            if name.startswith("_"):
                continue
            try:
                entry = self._load_agent(name, agent_file)
                if entry:
                    self._entries[name] = entry
            except Exception as e:
                print(f"⚠️  [AgentRegistry] 跳过 {name}: {e}")

    def _load_agent(self, name: str, agent_file: Path) -> AgentEntry | None:
        module_path = f"agents.{name}.agent"
        module = sys.modules.get(module_path) or importlib.import_module(module_path)

        cls = None
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if isinstance(obj, type) and attr_name.endswith("Agent") and attr_name != "Agent":
                cls = obj
                break
        if cls is None:
            return None

        desc_en = (
            getattr(module, "DESCRIPTION", None)
            or _FALLBACK_EN.get(name)
            or (inspect.getdoc(cls) or "").split("\n")[0]
            or f"Agent: {name}"
        )
        desc_zh = (
            getattr(module, "DESCRIPTION_ZH", None)
            or _FALLBACK_ZH.get(name)
            or ""
        )

        if hasattr(module, "REQUIRES_LLM"):
            requires_llm = bool(module.REQUIRES_LLM)
        else:
            sig = inspect.signature(cls.__init__)
            requires_llm = len([p for p in sig.parameters if p != "self"]) > 0

        return AgentEntry(name, module, cls, desc_en, desc_zh, requires_llm)

    def format_for_planner(self, lang: str = None, include_disabled: bool = False) -> str:
        """
        生成注入 Planner prompt 的 Agent 描述列表，自动按语言切换。

        zh 模式示例：
          - viewer: 扫描并读取工作区目录结构和文件内容
          - coder:  编写或修改源代码文件，支持 <file> 标签

        en 模式示例：
          - viewer: Scan and read workspace directory structure
          - coder:  Write or modify source code files
        """
        use_lang = lang or self._lang
        lines = []
        for name, entry in self._entries.items():
            if not include_disabled and name in self._disabled:
                continue
            lines.append(f"- {name}: {entry.get_description(use_lang)}")
        return "\n".join(lines)

    def get_description(self, name: str, lang: str = None) -> str:
        entry = self._entries.get(name)
        return entry.get_description(lang or self._lang) if entry else ""

    def available_names(self) -> list[str]:
        return [n for n in self._entries if n not in self._disabled]

    def build_all(self, llm_client=None, disabled: list[str] = None) -> dict:
        skip = self._disabled | set(disabled or [])
        result = {}
        for name, entry in self._entries.items():
            if name in skip:
                continue
            try:
                result[name] = entry.instantiate(llm_client)
            except Exception as e:
                print(f"⚠️  [AgentRegistry] 实例化 {name} 失败: {e}")
        return result

    def build_one(self, name: str, llm_client=None):
        entry = self._entries.get(name)
        if not entry:
            raise KeyError(f"Agent '{name}' not found in registry")
        return entry.fresh(llm_client)

    def set_disabled(self, disabled: list[str]):
        self._disabled = set(disabled)

    def reload(self):
        self._entries.clear()
        self._discover()

    def summary(self) -> str:
        """打印所有 Agent 的双语描述（调试用）。"""
        lines = [f"AgentRegistry — {len(self._entries)} agents (lang={self._lang})\n"]
        for name, entry in self._entries.items():
            status = "🚫" if name in self._disabled else "✅"
            lines.append(f"  {status} [{name}]")
            lines.append(f"       EN: {entry.description_en}")
            if entry.description_zh:
                lines.append(f"       ZH: {entry.description_zh}")
        return "\n".join(lines)

    def __repr__(self):
        return f"<AgentRegistry lang={self._lang} agents={self.available_names()}>"

"""
SystemHandler — 系统指令直接处理器
不走LLM，直接返回系统状态/数据
"""
import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class SystemHandler:
    def __init__(self, skill_library=None, workspace="workspace"):
        self.skills    = skill_library
        self.workspace = workspace

    def handle(self, action: str, payload: str) -> str:
        handlers = {
            "list_skills":    self._list_skills,
            "delete_skill":   self._delete_skill,
            "show_workspace": self._show_workspace,
            "show_history":   self._show_history,
            "system_status":  self._system_status,
            "error_solutions":self._error_solutions,
            "improve_report": self._improve_report,
            "learning_report":self._learning_report,
            "help":           self._help,
            "general":        self._general,
        }
        fn = handlers.get(action, self._general)
        return fn(payload)

    def _list_skills(self, payload: str) -> str:
        if not self.skills:
            return "📭 技能库未初始化"
        skills = self.skills.list_skills()
        if not skills:
            return "📭 技能库目前为空，完成几个开发任务后会自动积累技能。"
        lines = [f"📚 **技能库** — 共 {len(skills)} 个技能\n"]
        for s in skills:
            kws = ", ".join(s.get("keywords", [])[:4])
            lines.append(
                f"✦ **{s['name']}**\n"
                f"  ID: {s['id']} | 使用次数: {s.get('success_count',1)}\n"
                f"  关键词: {kws}\n"
                f"  创建时间: {s.get('created_at','')}"
            )
        return "\n\n".join(lines)

    def _delete_skill(self, payload: str) -> str:
        if not self.skills:
            return "❌ 技能库未初始化"
        for s in self.skills.list_skills():
            if s["name"] in payload or s["id"] in payload:
                self.skills.delete_skill(s["id"])
                return f"🗑️ 已删除技能：{s['name']}"
        return "❓ 未找到匹配的技能"

    def _show_workspace(self, payload: str) -> str:
        ws = os.path.join(BASE_DIR, self.workspace)
        if not os.path.exists(ws):
            return "📁 workspace 目录为空"
        return "📁 workspace 目录：\n" + self._tree(ws)

    def _tree(self, path: str, prefix: str = "") -> str:
        result = ""
        try:
            items = sorted(i for i in os.listdir(path)
                          if not i.startswith('.') and i not in ('__pycache__',))
        except PermissionError:
            return "(权限不足)"
        for i, item in enumerate(items):
            last = i == len(items) - 1
            conn = "└── " if last else "├── "
            result += f"{prefix}{conn}{item}\n"
            full = os.path.join(path, item)
            if os.path.isdir(full):
                result += self._tree(full, prefix + ("    " if last else "│   "))
        return result or "(空)"

    def _show_history(self, payload: str) -> str:
        hf = os.path.join(BASE_DIR, "history.json")
        if not os.path.exists(hf):
            return "📭 暂无历史记录"
        try:
            with open(hf, "r", encoding="utf-8") as f:
                history = json.load(f)
            lines = [f"📋 最近 {min(5,len(history))} 条对话："]
            for h in history[:5]:
                lines.append(f"  • {h.get('title','无标题')} ({h.get('created_at','')})")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ 读取历史失败：{e}"

    def _system_status(self, payload: str) -> str:
        import platform
        skill_count = len(self.skills.list_skills()) if self.skills else 0
        ws_path = os.path.join(BASE_DIR, self.workspace)
        ws_size = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, dn, fn in os.walk(ws_path) for f in fn
        ) if os.path.exists(ws_path) else 0
        return (
            f"⚙️ **系统状态**\n"
            f"Python: {platform.python_version()}\n"
            f"技能库: {skill_count} 个技能\n"
            f"Workspace: {ws_size//1024} KB\n"
            f"平台: {platform.system()}"
        )

    def _error_solutions(self, payload: str) -> str:
        ef = os.path.join(BASE_DIR, "error_solutions.json")
        if not os.path.exists(ef):
            return "📭 错误解决方案库为空，遇到报错并修复后会自动记录。"
        try:
            with open(ef, "r", encoding="utf-8") as f:
                db = json.load(f)
            if not db:
                return "📭 错误解决方案库为空"
            items = sorted(db.values(), key=lambda x: x.get("count",0), reverse=True)
            lines = [f"🔧 **错误解决方案库** — 共 {len(items)} 条\n"]
            for item in items[:5]:
                lines.append(
                    f"• 出现 {item.get('count',1)} 次\n"
                    f"  错误：{item['error'][:80]}…\n"
                    f"  方案：{item['solution'][:100]}…"
                )
            return "\n\n".join(lines)
        except Exception as e:
            return f"❌ 读取失败：{e}"

    def _improve_report(self, payload: str) -> str:
        lf = os.path.join(BASE_DIR, "improvement_log.json")
        if not os.path.exists(lf):
            return "📭 暂无改进报告，运行 '分析系统改进建议' 生成报告。"
        try:
            with open(lf, "r", encoding="utf-8") as f:
                logs = json.load(f)
            if not logs:
                return "📭 改进日志为空"
            latest = logs[0]
            return (
                f"📊 **最新改进报告** ({latest.get('timestamp','')})\n\n"
                f"{latest.get('analysis','')}"
            )
        except Exception as e:
            return f"❌ 读取失败：{e}"

    def _learning_report(self, payload: str) -> str:
        rd = os.path.join(BASE_DIR, "learning_reports")
        if not os.path.exists(rd):
            return "📭 暂无学习报告"
        reports = sorted(os.listdir(rd), reverse=True)
        if not reports:
            return "📭 暂无学习报告"
        latest = reports[0]
        try:
            with open(os.path.join(rd, latest), "r", encoding="utf-8") as f:
                data = json.load(f)
            return (
                f"📚 **最新学习报告** ({data.get('generated_at','')})\n"
                f"共学习 {data.get('total_topics',0)} 个主题\n\n" +
                "\n".join(f"✦ {item['topic']}: {item.get('summary','')}"
                          for item in data.get('items',[])[:5])
            )
        except Exception as e:
            return f"❌ 读取失败：{e}"

    def _help(self, payload: str) -> str:
        return """🤖 **Multi-Agent OS 使用指南**

**开发任务（直接描述需求）：**
• 用 Python + pygame 写贪吃蛇游戏
• 创建 Flask REST API
• 写一个命令行计算器

**系统查询（直接输入）：**
• 列出所有技能
• 查看 workspace 目录
• 查看错误解决方案记录
• 系统状态
• 查看改进建议
• 学习报告

**自主学习（顶栏开关）：**
• 打开「自主学习」按钮，系统在后台学习 GitHub 技术内容
• 打开「GitHub 学习」按钮，让 Agent 搜索时使用 GitHub

**技能库（自动）：**
• 每次任务成功后自动封装为技能
• 下次类似任务自动召回参考"""

    def _general(self, payload: str) -> str:
        return f"收到系统指令：{payload}\n请尝试更具体的描述，或输入「帮助」查看使用指南。"

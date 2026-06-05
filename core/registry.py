# core/registry.py
import os
import re
import sys
import yaml
import json
import inspect
import importlib
import importlib.util
from rich.console import Console

console = Console()

class ToolRegistry:
    def __init__(self):
        # 底层原子工具 (Python)
        self.functions = {}
        self.schemas = {}
        # 高级 SOP 技能 (Markdown)
        self.md_skills = {}

    # 🛠️ 终极防弹 Schema 修正器
    def register(self, schema=None, **kwargs):
        """装饰器：注册底层 Python 工具 (兼容 kwargs 并自动修复 Schema)"""
        def decorator(func):
            func_name = kwargs.get("name", func.__name__)
            self.functions[func_name] = func
            
            if schema is not None:
                if "function" in schema and "parameters" in schema["function"]:
                    params = schema["function"]["parameters"]
                    if "type" not in params:
                        params["type"] = "object"
                self.schemas[func_name] = schema
            else:
                params = kwargs.get("parameters", {})
                safe_params = {
                    "type": "object",
                    "properties": params.get("properties", {}) if isinstance(params, dict) else {}
                }
                if isinstance(params, dict) and "required" in params:
                    safe_params["required"] = params["required"]

                self.schemas[func_name] = {
                    "type": "function",
                    "function": {
                        "name": func_name,
                        "description": kwargs.get("description", func.__doc__ or "No description provided."),
                        "parameters": safe_params
                    }
                }
            return func
        return decorator

    def execute(self, name: str, args_str: str) -> str:
        """执行底层 Python 工具"""
        if name not in self.functions:
            return f"Error: Tool '{name}' not found."
        try:
            kwargs = json.loads(args_str) if args_str else {}
            result = self.functions[name](**kwargs)
            return str(result)
        except Exception as e:
            return f"Error executing '{name}': {str(e)}"

    def get_schema(self, name: str):
        return self.schemas.get(name)

    def reload_tools(self, directories=None):
        """🔄 终极热重载：同时重载 Python 工具和 Markdown 技能"""
        if directories is None:
            directories = ["tools", "skills"]

        old_funcs = self.functions.copy()
        old_schemas = self.schemas.copy()

        self.functions.clear()
        self.schemas.clear()

        try:
            for directory in directories:
                if os.path.exists(directory):
                    discover_tools(directory, registry_instance=self)
            console.print(f"[bold green]✅ Python 工具树已深度重载！当前挂载 {len(self.functions)} 个底层指令。[/]")
        except Exception as e:
            self.functions = old_funcs
            self.schemas = old_schemas
            console.print(f"[bold red]❌ Python 热重载失败，已回滚: {e}[/]")

        for directory in directories:
            if os.path.exists(directory):
                self.reload_md_skills(directory)

    def reload_md_skills(self, directory="skills"):
        """🚀 递归深度解析任意文件夹层级的 .md 高级 SOP"""
        if not os.path.exists(directory):
            os.makedirs(directory)
            return

        self.md_skills.clear()
        loaded_count = 0

        # 核心黑科技：使用 os.walk 穿透所有子文件夹
        for root, dirs, files in os.walk(directory):
            # 忽略隐藏文件夹(如 .git)和 Python 缓存文件夹
            dirs[:] = [d for d in dirs if not d.startswith('.') and not d.startswith('__')]
            
            for filename in files:
                if filename.endswith(".md"):
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # 正则提取 YAML 头
                        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
                        if match:
                            metadata = yaml.safe_load(match.group(1))
                            body = match.group(2).strip()
                            
                            skill_name = metadata.get('name', filename.replace('.md', ''))
                            self.md_skills[skill_name] = {
                                "metadata": metadata,
                                "content": body,
                                "filepath": filepath
                            }
                            loaded_count += 1
                    except Exception as e:
                        console.print(f"[bold red]❌ 解析 MD 技能 {filepath} 失败: {e}[/]")

        try:
            from core.config import config
            current_lang = str(config.data.get("lang", "zh")).lower().strip()
        except Exception:
            current_lang = "zh"

        if current_lang.startswith("en"):
            console.print(
                f"[bold green]✅ Markdown skill library fully reloaded! "
                f"{loaded_count} advanced SOP skills mounted.[/]"
            )
        else:
            console.print(
                f"[bold green]✅ Markdown 技能库已深度重载！"
                f"当前挂载 {loaded_count} 个高级 SOP 战术。[/]"
            )

    def get_all_md_skills_summary(self) -> str:
        """生成供大模型阅读的技能清单"""
        if not self.md_skills:
            return "No advanced markdown skills currently loaded."
        
        summary = "Available Advanced Skills (SOPs):\n"
        for name, data in self.md_skills.items():
            desc = data['metadata'].get('description', '').replace('\n', ' ')
            summary += f"- **{name}**: {desc}\n"
        return summary

# 全局单例暴露
registry = ToolRegistry()
tool = registry.register

def discover_tools(directory="skills", registry_instance=None):
    """🚀 递归深度扫描并动态挂载所有子目录下的 .py 文件"""
    target_registry = registry_instance if registry_instance else registry

    if not os.path.exists(directory):
        os.makedirs(directory)
        return

    # 核心黑科技：使用 os.walk 穿透所有子文件夹
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.') and not d.startswith('__')]
        dirs.sort()
        
        # 将当前扫到的子文件夹加入 sys.path，保证文件里的 import 能正常工作
        abs_root = os.path.abspath(root)
        if abs_root not in sys.path:
            sys.path.insert(0, abs_root)

        for filename in sorted(files):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                filepath = os.path.join(root, filename)
                try:
                    # 终极动态加载：根据文件绝对路径直接把模块“塞”进系统
                    spec = importlib.util.spec_from_file_location(module_name, filepath)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)
                except Exception as e:
                    console.print(f"[bold red]❌ Failed to load python skill [{filepath}]: {e}[/]")

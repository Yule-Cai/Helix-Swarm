# skills/file_ops.py
import os
from core.registry import registry

@registry.register(
    name="read_file",
    description="[CRITICAL] Read the contents of a specific file. ONLY use this AFTER locating the target via grep_search. Do NOT read large files blindly.",
    parameters={
        "properties": {
            "filepath": {"type": "string", "description": "Absolute or relative path to the file."}
        },
        "required": ["filepath"]
    },
    category="file"
)
def read_file(filepath: str) -> str:
    """带物理截断的防爆读取器"""
    print(f"  [Skill] 📖 读取文件: {filepath}")
    if not os.path.exists(filepath):
        return f"❌ 错误: 文件 '{filepath}' 不存在。"
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # 🛡️ 终极防爆截断：限制读取前 400 行
        MAX_LINES = 400
        if len(lines) > MAX_LINES:
            content = "".join(lines[:MAX_LINES])
            return (f"{content}\n\n"
                    f"... ⚠️ [SYSTEM WARNING: FILE TRUNCATED] ⚠️ ...\n"
                    f"文件总共有 {len(lines)} 行，为了保护大模型记忆容量，此处仅展示前 {MAX_LINES} 行。\n"
                    f"⛔ 严禁再次尝试读取此文件！如果你需要查看更后面的逻辑，请立即使用 `grep_search` 工具搜索具体关键字！")
        return "".join(lines)
    except Exception as e:
        return f"❌ 读取文件出错: {str(e)}"

@registry.register(
    name="write_file",
    description="Write complete content to a file. Overwrites existing content.",
    parameters={
        "properties": {
            "filepath": {"type": "string", "description": "Path to the file."},
            "content": {"type": "string", "description": "The full source code or text to write."}
        },
        "required": ["filepath", "content"]
    },
    category="file"
)
def write_file(filepath: str, content: str) -> str:
    print(f"  [Skill] 💾 写入文件: {filepath}")
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"✅ Successfully wrote {len(content)} characters to {filepath}"
    except Exception as e:
        return f"❌ Write Error: {str(e)}"
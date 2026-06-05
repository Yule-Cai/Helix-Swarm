# skills/search_tools.py
import os
import re
from core.registry import registry

# 过滤掉容易污染 AI 上下文的垃圾目录和文件
IGNORE_DIRS = {".git", "__pycache__", "node_modules", "venv", ".venv", "dist", "build", ".idea"}
IGNORE_EXTS = {".json", ".lock", ".sqlite", ".db", ".csv", ".xlsx", ".pdf", ".jpg", ".png", ".pyc"}

@registry.register(
    name="grep_search",
    description="[CRITICAL TOOL] Search for a specific keyword or regex pattern across all code files in the directory. ALWAYS use this to find functions/variables before reading whole files.",
    parameters={
        "properties": {
            "keyword": {"type": "string", "description": "The exact string or regex pattern to search for (e.g., 'def main' or 'import fastapi')."},
            "directory": {"type": "string", "description": "Directory to search in. Default is '.' (current directory)."}
        },
        "required": ["keyword"]
    },
    category="code"
)
def grep_search(keyword: str, directory: str = ".") -> str:
    """Python 原生的跨平台安全检索器"""
    results = []
    match_count = 0
    max_results = 50  # 强制保护：最多返回 50 条匹配，防止把 AI 撑爆
    
    try:
        pattern = re.compile(keyword, re.IGNORECASE)
    except re.error:
        return f"❌ 错误：无效的正则表达式或搜索关键字 '{keyword}'"

    for root, dirs, files in os.walk(directory):
        # 原地修改 dirs，过滤掉黑名单目录，提升搜索速度
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            # 过滤非代码文件
            ext = os.path.splitext(file)[1].lower()
            if ext in IGNORE_EXTS:
                continue
                
            file_path = os.path.join(root, file)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if pattern.search(line):
                            # 格式：相对路径:行号: 行内容
                            rel_path = os.path.relpath(file_path, directory)
                            clean_line = line.strip()
                            # 截断单行过长的无用代码（比如混淆的js）
                            if len(clean_line) > 150:
                                clean_line = clean_line[:150] + "..."
                                
                            results.append(f"{rel_path}:{line_num}: {clean_line}")
                            match_count += 1
                            
                            if match_count >= max_results:
                                results.append(f"\n... [系统截断] 搜索结果过多，总共超过 {max_results} 条。请使用更具体的关键字重试。 ...")
                                return "\n".join(results)
            except UnicodeDecodeError:
                pass # 忽略二进制文件
            except Exception:
                pass

    if not results:
        return f"🔍 未能在代码库中找到与 '{keyword}' 匹配的内容。"
        
    return "\n".join(results)
# core/toolsets.py
from typing import List, Dict, Set
from core.registry import registry

# 定义预设的工具集合，支持嵌套 (includes)
_TOOLSETS: Dict[str, dict] = {
    "system": {
        "description": "Basic system operations like running bash commands.",
        "tools": ["execute_bash"],
        "includes": []
    },
    "file_io": {
        "description": "Reading and writing files locally.",
        "tools": ["read_file", "write_file", "search_files"],
        "includes": []
    },
    # 一个组合型工具集，包含了 system 和 file_io 的所有能力
    "developer": {
        "description": "Full suite for a software developer agent.",
        "tools": [],
        "includes": ["system", "file_io"]
    }
}

def resolve_toolset(toolset_name: str, visited: Set[str] = None) -> List[str]:
    """
    递归解析工具集名称，展开所有包含的底层工具名称。
    """
    if visited is None:
        visited = set()
        
    if toolset_name in visited:
        return [] # 防止循环依赖
        
    visited.add(toolset_name)
    
    if toolset_name not in _TOOLSETS:
        return []
        
    config = _TOOLSETS[toolset_name]
    resolved_tools = list(config.get("tools", []))
    
    # 递归展开包含的子工具集
    for included_set in config.get("includes", []):
        resolved_tools.extend(resolve_toolset(included_set, visited))
        
    # 去重并返回
    return list(set(resolved_tools))

def get_schemas_for_toolsets(toolset_names: List[str]) -> List[dict]:
    """
    根据传入的工具集名称列表，返回大模型需要的 JSON Schemas 列表。
    """
    all_tool_names = set()
    for ts_name in toolset_names:
        tools = resolve_toolset(ts_name)
        all_tool_names.update(tools)
        
    schemas = []
    for tool_name in all_tool_names:
        schema = registry.get_schema(tool_name)
        if schema:
            schemas.append(schema)
            
    return schemas
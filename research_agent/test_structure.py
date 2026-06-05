"""
项目结构测试

验证项目结构是否正确。
"""

import os
import sys
from pathlib import Path


def test_project_structure():
    """测试项目结构"""
    # 获取项目根目录
    root_dir = Path(__file__).parent
    
    # 检查必要的目录和文件
    required_paths = [
        # 核心模块
        "core/__init__.py",
        "core/agent_base.py",
        "core/task_manager.py",
        "core/state_manager.py",
        "core/workflow_engine.py",
        
        # 服务模块
        "services/__init__.py",
        "services/llm_service.py",
        "services/search_service.py",
        "services/storage_service.py",
        
        # 测试模块
        "tests/__init__.py",
        "tests/test_agent.py",
        "tests/test_tasks.py",
        "tests/test_memory.py",
        "tests/test_workflows.py",
        "tests/test_services.py",
        
        # 配置文件
        "config/__init__.py",
        "config/settings.py",
        "main.py",
        "requirements.txt",
        "README.md",
        "LICENSE",
        "setup.py",
        "pyproject.toml",
        "Makefile",
        ".gitignore",
    ]
    
    missing_paths = []
    
    for path in required_paths:
        full_path = root_dir / path
        if not full_path.exists():
            missing_paths.append(path)
    
    if missing_paths:
        print("[FAIL] Missing files or directories:")
        for path in missing_paths:
            print(f"  - {path}")
        return False
    
    print("[OK] Project structure verification passed")
    return True


def test_imports():
    """测试导入"""
    try:
        # 获取项目根目录
        root_dir = Path(__file__).parent
        
        # 添加项目根目录的父目录到路径
        sys.path.insert(0, str(root_dir.parent))
        
        # 测试导入
        from research_agent.core import AgentBase, AgentResult
        from research_agent.core.task_manager import TaskManager, Task, TaskStatus, TaskPriority
        from research_agent.core.state_manager import StateManager, StateType, State
        from research_agent.core.workflow_engine import WorkflowEngine, Workflow, WorkflowStep, WorkflowStatus, StepStatus
        from research_agent.services import LLMService, SearchService, StorageService
        from research_agent.config import settings
        
        print("[OK] All module imports successful")
        return True
        
    except ImportError as e:
        print(f"[FAIL] Import failed: {e}")
        return False


def main():
    """主函数"""
    print("="*60)
    print("Research Agent - Project Structure Test")
    print("="*60)
    print()
    
    # 测试项目结构
    structure_ok = test_project_structure()
    print()
    
    # 测试导入
    imports_ok = test_imports()
    print()
    
    # 总结
    print("="*60)
    if structure_ok and imports_ok:
        print("[OK] All tests passed! Project structure is correct.")
    else:
        print("[FAIL] Some tests failed. Please check project structure.")
    print("="*60)
    
    return 0 if (structure_ok and imports_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
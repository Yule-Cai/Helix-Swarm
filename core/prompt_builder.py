import os
import glob
from pathlib import Path

# 基础系统指令 (The Core Identity)
BASE_PROMPT = """You are Helix, an elite autonomous AI software engineer part of the Helix-Swarm.
You operate within a local CLI environment and have access to advanced tools.

CORE DIRECTIVES:
1. THINK BEFORE ACTING: Analyze the task and break it down.
2. VERIFY: After modifying code, ALWAYS verify it by running tests or syntax checks.
3. FIX ERRORS: If a command fails, read the error output and try another approach. Do not loop blindly.
"""

def build_dynamic_system_prompt() -> str:
    """
    动态扫描 skills 目录，收集所有激活技能的 INSTRUCTIONS.md
    并将它们组装成终极 System Prompt。
    """
    project_root = Path(__file__).parent.parent.absolute()
    skills_dir = project_root / "skills"
    
    final_prompt = BASE_PROMPT + "\n\n=== EQUIPPED SKILLS & INSTRUCTIONS ===\n"
    
    if not skills_dir.exists():
        return final_prompt
        
    # 扫描所有子目录下的 INSTRUCTIONS.md
    instruction_files = skills_dir.glob("*/INSTRUCTIONS.md")
    loaded_skills = 0
    
    for md_file in instruction_files:
        skill_name = md_file.parent.name
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    final_prompt += f"\n--- Skill: [{skill_name.upper()}] ---\n"
                    final_prompt += f"{content}\n"
                    loaded_skills += 1
        except Exception as e:
            print(f"⚠️ Warning: Could not read instructions for skill {skill_name}: {e}")
            
    if loaded_skills > 0:
        final_prompt += "\nRemember to STRICTLY follow the skill instructions above when using tools."
        
    return final_prompt
import os
import json
import re

class StateManager:
    """场记。负责在小说章节完成后，读取正文文本并更新角色的状态表(JSON)。"""
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def run(self, instruction):
        print(f"📋 [State Manager] 正在更新小说动态状态表...")
        
        # 🟢 1. 智能提取小说文本文件(.txt/.md)和状态表文件(.json)的路径
        txt_match = re.search(r'([a-zA-Z0-9_-]+/[\w.-]+\.(?:txt|md))', instruction) or re.search(r'([\w.-]+\.(?:txt|md))', instruction)
        json_match = re.search(r'([a-zA-Z0-9_-]+/[\w.-]+\.json)', instruction) or re.search(r'([\w.-]+\.json)', instruction)

        if not txt_match:
            return "❌ StateManager 未能在指令中找到需要读取的小说文本文件 (.txt/.md)。"

        txt_filename = txt_match.group(1)
        json_filename = json_match.group(1) if json_match else "novel_state.json"

        txt_filepath = os.path.join("workspace", txt_filename)
        state_path = os.path.join("workspace", json_filename)

        # 🟢 2. 深度寻路：读取刚刚写好的小说正文！(核心修复点)
        if not os.path.exists(txt_filepath):
            found = False
            for root, dirs, files in os.walk("workspace"):
                for file in files:
                    if file == txt_filename.split('/')[-1]:
                        txt_filepath = os.path.join(root, file)
                        found = True
                        break
                if found: break

        if not os.path.exists(txt_filepath):
            return f"❌ 找不到小说文本文件: {txt_filename}，无法更新状态。"

        try:
            with open(txt_filepath, 'r', encoding='utf-8', errors='replace') as f:
                novel_content = f.read()
        except Exception as e:
            return f"❌ 读取小说文件失败: {str(e)}"

        # 🟢 3. 读取旧状态表 (完全保留你的原版逻辑)
        # 自动纠正 JSON 文件的沙箱路径，让它和 TXT 文件呆在一起
        if os.path.dirname(txt_filepath) != "workspace" and os.path.dirname(state_path) == "workspace":
            state_path = os.path.join(os.path.dirname(txt_filepath), json_filename.split('/')[-1])

        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        
        old_state = "{}"
        if os.path.exists(state_path):
            with open(state_path, 'r', encoding='utf-8', errors='replace') as f:
                old_state = f.read()

        # 🟢 4. 将【真正的小说正文】喂给大模型
        prompt = (
            "你是一个严谨的场记。刚才主笔完成了一段新的剧情。\n"
            "请阅读新剧情，结合【旧状态表】，提取出主角（或主要视角角色）的当前状态，输出一份【新状态表】。\n"
            "如果旧状态表为空，请直接根据新剧情创建全新的状态。\n"
            "必须只输出合法的 JSON 格式，绝不能有任何 Markdown 标记或多余的文字。\n\n"
            f"【旧状态表】\n{old_state}\n\n"
            f"【新剧情内容】\n{novel_content[:8000]}\n\n" # 截断防爆
            "请直接输出合法的 JSON："
        )

        new_state_text = self.llm_client.chat("你是小说数据维护员。", prompt, temperature=0.1)
        
        # 🟢 5. 保留你原版的暴力 JSON 提取正则，并顺手做个美化
        try:
            # 贪婪匹配第一个 { 和最后一个 } 之间的所有内容
            json_match = re.search(r'\{.*\}', new_state_text, re.DOTALL)
            if json_match:
                clean_json = json_match.group(0)
                
                # 验证是否合法，并将其美化（增加缩进，方便人类阅读）
                parsed_json = json.loads(clean_json) 
                pretty_json = json.dumps(parsed_json, ensure_ascii=False, indent=4)
                
                with open(state_path, 'w', encoding='utf-8') as f:
                    f.write(pretty_json)
                return f"✅ 动态状态表 ({json_filename.split('/')[-1]}) 已成功更新。"
            else:
                return "⚠️ 未能生成合法的 JSON，状态表更新失败。"
        except Exception as e:
            return f"❌ 状态解析失败: {str(e)}。LLM 的原始输出格式有误。"
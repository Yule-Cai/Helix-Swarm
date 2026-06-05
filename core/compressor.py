# core/compressor.py
import json
import logging
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)

# 预估：1 token 约等于 4 个字符
CHARS_PER_TOKEN = 4

def _summarize_tool_result(tool_name: str, tool_args: str, tool_content: str) -> str:
    """零成本修剪：将冗长的工具输出压缩成一句话摘要"""
    try:
        args = json.loads(tool_args) if tool_args else {}
    except Exception:
        args = {}

    content = tool_content or ""
    content_len = len(content)
    line_count = content.count("\n") + 1 if content.strip() else 0

    if tool_name == "execute_terminal":
        cmd = args.get("command", "")[:60]
        return f"[execute_terminal] ran `{cmd}...` -> {line_count} lines output"

    if tool_name == "read_file":
        path = args.get("path", "?")
        return f"[read_file] read {path} ({content_len:,} chars)"

    if tool_name == "write_file":
        path = args.get("path", "?")
        return f"[write_file] wrote to {path} ({line_count} lines)"

    # 默认回退
    return f"[{tool_name}] executed ({content_len:,} chars result)"

class ContextCompressor:
    def __init__(self, api_url, model, max_tokens=32000):
        self.api_url = api_url
        self.model = model
        self.max_tokens = max_tokens
        # 换算成近似字符数作为硬上限
        self.max_chars = max_tokens * CHARS_PER_TOKEN
        
        # 保护策略配置
        self.protect_head = 2  # 保护最初的 system prompt 和第一个 user/assistant 对话
        self.protect_tail = 6  # 保护最近的 6 条消息

    def compress_if_needed(self, messages: list) -> list:
        """主入口：如果上下文超载，则执行无损+有损压缩"""
        current_chars = sum(len(str(m)) for m in messages)
        
        if current_chars < self.max_chars:
            return messages

        console.print(f"\n🗜️ [记忆压缩器] 触发！当前容量 {current_chars:,}/{self.max_chars:,}...")
        
        # 阶段一：廉价的预处理修剪 (Pruning)
        pruned_messages = self._prune_tool_results(messages)
        
        pruned_chars = sum(len(str(m)) for m in pruned_messages)
        if pruned_chars < self.max_chars:
            console.print(f"[dim green]✨ [无损瘦身] 仅修剪冗余工具输出，容量降至 {pruned_chars:,}！[/]")
            return self._sanitize_tool_pairs(pruned_messages)

        # 阶段二：硬切割保护 (Tail Protection)
        # 如果修剪完还是超载，说明聊得太久了，我们只能保留头和尾
        
        if len(pruned_messages) <= (self.protect_head + self.protect_tail):
            # 消息太少无法切割，放弃压缩以免破坏逻辑
            return self._sanitize_tool_pairs(pruned_messages)
            
        head_msgs = pruned_messages[:self.protect_head]
        tail_msgs = pruned_messages[-self.protect_tail:]
        
        # 中间的被切掉了，我们插入一个明确的断层提示，防止大模型幻觉
        amnesia_note = {
            "role": "user",
            "content": "[SYSTEM NOTE: 较早前的对话记录已被折叠清理以节省内存。请基于最近的几条对话继续工作。]"
        }
        
        compressed_msgs = head_msgs + [amnesia_note] + tail_msgs
        
        final_msgs = self._sanitize_tool_pairs(compressed_msgs)
        final_chars = sum(len(str(m)) for m in final_msgs)
        
        saved_pct = ((current_chars - final_chars) / current_chars) * 100
        console.print(f"[dim green]✨ [深度清理] 历史折叠完成，体积减少了 {saved_pct:.1f}% ![/]")
        
        return final_msgs

    def _prune_tool_results(self, messages: list) -> list:
        """遍历消息，将旧的、庞大的 Tool Result 替换为单行摘要"""
        result = []
        # 我们不修剪最近的几条结果，防止刚执行完大模型就忘了细节
        protect_zone = len(messages) - self.protect_tail
        
        # 建立一个 mapping 方便查找 call_id 对应的工具名
        call_map = {}
        for m in messages:
            if m.get("role") == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    call_map[tc["id"]] = (tc["function"]["name"], tc["function"]["arguments"])

        for i, msg in enumerate(messages):
            new_msg = msg.copy()
            if i < protect_zone and msg.get("role") == "tool":
                content = str(msg.get("content", ""))
                # 只修剪那些非常长且占用大量 token 的输出
                if len(content) > 500:
                    tool_id = msg.get("tool_call_id", "")
                    t_name, t_args = call_map.get(tool_id, ("unknown", ""))
                    summary = _summarize_tool_result(t_name, t_args, content)
                    new_msg["content"] = summary
            result.append(new_msg)
            
        return result

    def _sanitize_tool_pairs(self, messages: list) -> list:
        """防报错核心：清理那些被腰斩的孤儿 Tool Call 或 Tool Result"""
        surviving_calls = set()
        result_calls = set()

        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    surviving_calls.add(tc["id"])
            elif msg.get("role") == "tool" and msg.get("tool_call_id"):
                result_calls.add(msg["tool_call_id"])

        # 1. 删掉没有爹的 Tool Result (孤儿)
        orphaned_results = result_calls - surviving_calls
        if orphaned_results:
            messages = [m for m in messages if not (m.get("role") == "tool" and m.get("tool_call_id") in orphaned_results)]

        # 2. 给没收到结果的 Tool Call 补一个假 Result (太监)
        missing_results = surviving_calls - result_calls
        if missing_results:
            patched = []
            for msg in messages:
                patched.append(msg)
                if msg.get("role") == "assistant" and msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        if tc["id"] in missing_results:
                            patched.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": "[Result archived — previous action successful]"
                            })
            messages = patched

        return messages
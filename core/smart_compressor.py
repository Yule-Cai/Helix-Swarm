# core/smart_compressor.py
import json
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)

# Token estimation: ~4 chars per token
CHARS_PER_TOKEN = 4

@dataclass
class MessageSummary:
    """Summary of a message or message group."""
    role: str
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None

class SmartCompressor:
    """
    Intelligent context compressor that preserves important information
    while reducing token usage.

    Features:
    - Tool result summarization
    - Conversation summarization
    - Semantic relevance tracking
    - Smart truncation with context preservation
    """

    def __init__(self, max_tokens: int = 32000, summarize_threshold: int = 0.8):
        self.max_tokens = max_tokens
        self.max_chars = max_tokens * CHARS_PER_TOKEN
        self.summarize_threshold = summarize_threshold

        # Protection zones
        self.protect_head = 2  # Protect system prompt and first exchange
        self.protect_tail = 8  # Protect recent messages

        # Tool result summarization templates
        self.tool_summaries = {
            "execute_terminal": self._summarize_terminal,
            "execute_bash": self._summarize_terminal,
            "read_file": self._summarize_file_read,
            "write_file": self._summarize_file_write,
            "edit_file": self._summarize_file_edit,
            "grep_code": self._summarize_search,
            "glob_files": self._summarize_search,
            "git_diff": self._summarize_git,
            "git_status": self._summarize_git,
            "git_log": self._summarize_git,
        }

    def compress_if_needed(self, messages: List[Dict]) -> List[Dict]:
        """Main entry point: compress context if it exceeds limits."""
        current_chars = sum(len(str(m)) for m in messages)

        if current_chars < self.max_chars * self.summarize_threshold:
            return messages

        console.print(f"\n🗜️ [Smart Compressor] Context size: {current_chars:,}/{self.max_chars:,} chars")

        # Phase 1: Summarize tool results (lossless for recent, lossy for old)
        summarized = self._summarize_tool_results(messages)
        summarized_chars = sum(len(str(m)) for m in summarized)

        if summarized_chars < self.max_chars:
            console.print(f"[dim green]✨ Tool result summarization saved {(current_chars - summarized_chars):,} chars[/]")
            return self._sanitize_tool_pairs(summarized)

        # Phase 2: Generate conversation summary if still too large
        if len(summarized) > (self.protect_head + self.protect_tail + 4):
            summarized = self._generate_conversation_summary(summarized)
            final_chars = sum(len(str(m)) for m in summarized)
            console.print(f"[dim green]✨ Conversation summarization saved {(current_chars - final_chars):,} chars[/]")
        else:
            # Fallback to hard truncation
            summarized = self._hard_truncate(summarized)
            final_chars = sum(len(str(m)) for m in summarized)
            console.print(f"[dim green]✨ Hard truncation saved {(current_chars - final_chars):,} chars[/]")

        return self._sanitize_tool_pairs(summarized)

    def _summarize_tool_results(self, messages: List[Dict]) -> List[Dict]:
        """Summarize old tool results while preserving recent ones."""
        result = []
        protect_zone = len(messages) - self.protect_tail

        # Build tool call mapping
        call_map = {}
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    call_map[tc["id"]] = (tc["function"]["name"], tc["function"]["arguments"])

        for i, msg in enumerate(messages):
            new_msg = msg.copy()

            # Only summarize old tool results (outside protection zone)
            if i < protect_zone and msg.get("role") == "tool":
                content = str(msg.get("content", ""))
                if len(content) > 500:  # Only summarize long results
                    tool_id = msg.get("tool_call_id", "")
                    tool_name, tool_args = call_map.get(tool_id, ("unknown", ""))

                    # Get specialized summary if available
                    if tool_name in self.tool_summaries:
                        summary = self.tool_summaries[tool_name](content, tool_args)
                    else:
                        summary = self._generic_summary(tool_name, content)

                    new_msg["content"] = summary

            result.append(new_msg)

        return result

    def _summarize_terminal(self, content: str, args: str) -> str:
        """Summarize terminal output."""
        try:
            args_dict = json.loads(args) if args else {}
            cmd = args_dict.get("command", "")[:60]
        except:
            cmd = "unknown"

        lines = content.count('\n') + 1
        # Keep first and last few lines
        if lines > 10:
            lines_list = content.split('\n')
            summary = '\n'.join(lines_list[:3]) + '\n...[TRUNCATED]...\n' + '\n'.join(lines_list[-3:])
            return f"[Terminal: {cmd}...] ({lines} lines)\n{summary}"
        return f"[Terminal: {cmd}...] ({lines} lines)\n{content}"

    def _summarize_file_read(self, content: str, args: str) -> str:
        """Summarize file read output."""
        try:
            args_dict = json.loads(args) if args else {}
            path = args_dict.get("path", "unknown")
        except:
            path = "unknown"

        chars = len(content)
        lines = content.count('\n') + 1
        return f"[Read: {path}] ({lines} lines, {chars:,} chars)"

    def _summarize_file_write(self, content: str, args: str) -> str:
        """Summarize file write output."""
        try:
            args_dict = json.loads(args) if args else {}
            path = args_dict.get("path", "unknown")
        except:
            path = "unknown"

        return f"[Wrote: {path}]"

    def _summarize_file_edit(self, content: str, args: str) -> str:
        """Summarize file edit output."""
        try:
            args_dict = json.loads(args) if args else {}
            path = args_dict.get("path", "unknown")
        except:
            path = "unknown"

        return f"[Edited: {path}]"

    def _summarize_search(self, content: str, args: str) -> str:
        """Summarize search results."""
        try:
            args_dict = json.loads(args) if args else {}
            pattern = args_dict.get("pattern", args_dict.get("symbol_name", ""))
        except:
            pattern = ""

        matches = content.count('\n') + 1
        if matches > 10:
            lines = content.split('\n')
            summary = '\n'.join(lines[:5]) + f'\n...[{matches - 5} more matches]...'
            return f"[Search: {pattern}] ({matches} matches)\n{summary}"
        return f"[Search: {pattern}] ({matches} matches)\n{content}"

    def _summarize_git(self, content: str, args: str) -> str:
        """Summarize git command output."""
        try:
            args_dict = json.loads(args) if args else {}
        except:
            args_dict = {}

        lines = content.count('\n') + 1
        if lines > 15:
            lines_list = content.split('\n')
            summary = '\n'.join(lines_list[:5]) + f'\n...[{lines - 5} more lines]...'
            return f"[Git output] ({lines} lines)\n{summary}"
        return f"[Git output] ({lines} lines)\n{content}"

    def _generic_summary(self, tool_name: str, content: str) -> str:
        """Generic summary for unknown tool types."""
        chars = len(content)
        lines = content.count('\n') + 1
        return f"[{tool_name}] ({lines} lines, {chars:,} chars)"

    def _generate_conversation_summary(self, messages: List[Dict]) -> List[Dict]:
        """Generate a summary of the conversation, keeping head and tail."""
        if len(messages) <= (self.protect_head + self.protect_tail):
            return messages

        head = messages[:self.protect_head]
        tail = messages[-self.protect_tail:]
        middle = messages[self.protect_head:-self.protect_tail]

        # Extract key information from middle messages
        summary_parts = []
        for msg in middle:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                # Summarize user messages
                if len(content) > 100:
                    summary_parts.append(f"User asked about: {content[:100]}...")
                else:
                    summary_parts.append(f"User: {content}")

            elif role == "assistant":
                # Summarize assistant responses
                if msg.get("tool_calls"):
                    tools = [tc["function"]["name"] for tc in msg["tool_calls"]]
                    summary_parts.append(f"Assistant used tools: {', '.join(tools)}")
                elif content:
                    if len(content) > 100:
                        summary_parts.append(f"Assistant responded: {content[:100]}...")
                    else:
                        summary_parts.append(f"Assistant: {content}")

            elif role == "tool":
                # Tool results are already summarized
                pass

        # Create summary message
        summary_content = "[Previous conversation summary]\n" + "\n".join(summary_parts[-10:])  # Keep last 10 items

        summary_msg = {
            "role": "system",
            "content": summary_content
        }

        return head + [summary_msg] + tail

    def _hard_truncate(self, messages: List[Dict]) -> List[Dict]:
        """Hard truncation as fallback - keep head and tail."""
        if len(messages) <= (self.protect_head + self.protect_tail):
            return messages

        head = messages[:self.protect_head]
        tail = messages[-self.protect_tail:]

        amnesia_note = {
            "role": "system",
            "content": "[Context truncated to save tokens. Recent conversation preserved.]"
        }

        return head + [amnesia_note] + tail

    def _sanitize_tool_pairs(self, messages: List[Dict]) -> List[Dict]:
        """Ensure tool calls have matching results and vice versa."""
        surviving_calls = set()
        result_calls = set()

        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    surviving_calls.add(tc["id"])
            elif msg.get("role") == "tool" and msg.get("tool_call_id"):
                result_calls.add(msg["tool_call_id"])

        # Remove orphaned tool results
        orphaned_results = result_calls - surviving_calls
        if orphaned_results:
            messages = [
                m for m in messages
                if not (m.get("role") == "tool" and m.get("tool_call_id") in orphaned_results)
            ]

        # Add dummy results for tool calls without results
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
                                "content": "[Result archived - previous action completed]"
                            })
            messages = patched

        return messages

    def get_context_stats(self, messages: List[Dict]) -> Dict:
        """Get statistics about the current context."""
        total_chars = sum(len(str(m)) for m in messages)
        total_tokens = total_chars // CHARS_PER_TOKEN

        tool_calls = 0
        tool_results = 0
        user_messages = 0
        assistant_messages = 0

        for msg in messages:
            role = msg.get("role", "")
            if role == "user":
                user_messages += 1
            elif role == "assistant":
                assistant_messages += 1
                if msg.get("tool_calls"):
                    tool_calls += len(msg["tool_calls"])
            elif role == "tool":
                tool_results += 1

        return {
            "total_chars": total_chars,
            "total_tokens": total_tokens,
            "message_count": len(messages),
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "utilization": total_chars / self.max_chars if self.max_chars > 0 else 0
        }

    def extract_key_facts(self, messages: List[Dict]) -> List[str]:
        """Extract key facts from conversation for memory."""
        facts = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user" and len(content) > 50:
                # Extract user requests
                facts.append(f"User requested: {content[:200]}...")

            elif role == "assistant" and content:
                # Extract decisions or conclusions
                if any(keyword in content.lower() for keyword in ["decided", "concluded", "found", "discovered", "fixed", "implemented"]):
                    facts.append(f"Decision: {content[:200]}...")

        return facts[-20:]  # Keep last 20 facts

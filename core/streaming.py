# core/streaming.py
import sys
import time
from typing import Optional, Callable
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown

console = Console()

class StreamingHandler:
    """
    Handles streaming output for AI responses.

    Features:
    - Token-by-token display
    - Tool call progress indication
    - Typing animation
    - Buffer management
    """

    def __init__(self, show_thinking: bool = True):
        self.show_thinking = show_thinking
        self.buffer = ""
        self.current_tool = None
        self.tool_start_time = None
        self.line_buffer = ""

    def on_token(self, token: str):
        """Called for each token in the stream."""
        self.buffer += token
        self.line_buffer += token

        # Print token by token
        sys.stdout.write(token)
        sys.stdout.flush()

        # Add small delay for typing effect (optional)
        # time.sleep(0.01)

    def on_thinking(self, thinking: str):
        """Called when model is thinking (if supported)."""
        if self.show_thinking:
            console.print(f"\n[dim italic]💭 Thinking: {thinking}[/]")

    def on_tool_call_start(self, tool_name: str, arguments: dict):
        """Called when a tool call starts."""
        self.current_tool = tool_name
        self.tool_start_time = time.time()

        # Show tool call in a panel
        args_preview = str(arguments)[:100] + "..." if len(str(arguments)) > 100 else str(arguments)
        console.print(f"\n🔧 [bold blue]Calling tool:[/] {tool_name}")
        if args_preview:
            console.print(f"   [dim]{args_preview}[/]")

    def on_tool_call_end(self, tool_name: str, result: str, success: bool = True):
        """Called when a tool call completes."""
        elapsed = time.time() - self.tool_start_time if self.tool_start_time else 0

        if success:
            # Show abbreviated result
            if len(result) > 200:
                result_preview = result[:200] + "..."
            else:
                result_preview = result

            console.print(f"✅ [green]{tool_name}[/] completed in {elapsed:.1f}s")
            if result_preview:
                console.print(f"   [dim]{result_preview}[/]")
        else:
            console.print(f"❌ [red]{tool_name}[/] failed: {result[:200]}")

        self.current_tool = None
        self.tool_start_time = None

    def on_error(self, error: str):
        """Called when an error occurs."""
        console.print(f"\n❌ [bold red]Error:[/] {error}")

    def on_complete(self):
        """Called when the response is complete."""
        if self.line_buffer:
            sys.stdout.write("\n")
            sys.stdout.flush()
        self.line_buffer = ""

    def get_buffer(self) -> str:
        """Get the current buffer content."""
        return self.buffer

    def clear_buffer(self):
        """Clear the buffer."""
        self.buffer = ""
        self.line_buffer = ""


class BufferedStreamingHandler(StreamingHandler):
    """
    Streaming handler that buffers content and displays in panels.
    Better for structured responses.
    """

    def __init__(self, show_thinking: bool = True):
        super().__init__(show_thinking)
        self.content_buffer = ""
        self.in_code_block = False
        self.code_block_lang = ""
        self.code_block_content = ""

    def on_token(self, token: str):
        """Buffer tokens and display intelligently."""
        self.buffer += token
        self.content_buffer += token

        # Check for code blocks
        if "```" in token:
            if not self.in_code_block:
                self.in_code_block = True
                # Extract language if specified
                parts = token.split("```")
                if len(parts) > 1 and parts[1]:
                    self.code_block_lang = parts[1].strip()
                sys.stdout.write("\n```" + self.code_block_lang + "\n")
            else:
                self.in_code_block = False
                sys.stdout.write("\n```\n")
                self.code_block_lang = ""
                self.code_block_content = ""
        elif self.in_code_block:
            self.code_block_content += token
            sys.stdout.write(token)
        else:
            # Regular text - display with wrapping
            sys.stdout.write(token)

        sys.stdout.flush()

    def on_complete(self):
        """Display final formatted content."""
        if self.content_buffer:
            # Could render as markdown here if needed
            pass
        super().on_complete()

    def get_formatted_content(self) -> str:
        """Get the content formatted for display."""
        return self.content_buffer


class ProgressStreamingHandler(StreamingHandler):
    """
    Streaming handler with progress indicators.
    Shows a progress bar during generation.
    """

    def __init__(self, show_thinking: bool = True):
        super().__init__(show_thinking)
        self.token_count = 0
        self.start_time = None
        self.live = None

    def on_token(self, token: str):
        """Track tokens and show progress."""
        self.token_count += 1
        self.buffer += token

        if self.start_time is None:
            self.start_time = time.time()

        # Print token
        sys.stdout.write(token)
        sys.stdout.flush()

        # Update progress every 10 tokens
        if self.token_count % 10 == 0:
            elapsed = time.time() - self.start_time
            tokens_per_sec = self.token_count / elapsed if elapsed > 0 else 0
            # Could display a progress bar here

    def on_complete(self):
        """Show final statistics."""
        if self.start_time:
            elapsed = time.time() - self.start_time
            tokens_per_sec = self.token_count / elapsed if elapsed > 0 else 0
            console.print(f"\n[dim]📊 Generated {self.token_count} tokens in {elapsed:.1f}s ({tokens_per_sec:.1f} tok/s)[/]")
        super().on_complete()


def create_streaming_handler(mode: str = "default") -> StreamingHandler:
    """Factory function to create appropriate streaming handler."""
    handlers = {
        "default": StreamingHandler,
        "buffered": BufferedStreamingHandler,
        "progress": ProgressStreamingHandler,
    }

    handler_class = handlers.get(mode, StreamingHandler)
    return handler_class()

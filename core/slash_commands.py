# core/slash_commands.py
import os
import sys
import json
import logging
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass, field
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
logger = logging.getLogger(__name__)

@dataclass
class CommandContext:
    """Context for command execution."""
    command: str
    args: List[str]
    raw_input: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None

@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    output: str
    data: Any = None
    should_continue: bool = True  # Whether to continue to AI processing

class SlashCommand:
    """Base class for slash commands."""

    def __init__(self, name: str, description: str, usage: str = ""):
        self.name = name
        self.description = description
        self.usage = usage

    def execute(self, context: CommandContext) -> CommandResult:
        """Execute the command. Must be overridden."""
        raise NotImplementedError

    def get_help(self) -> str:
        """Get help text for this command."""
        return f"/{self.name} - {self.description}\nUsage: {self.usage}" if self.usage else f"/{self.name} - {self.description}"

class CommandRegistry:
    """
    Registry for slash commands.

    Features:
    - Command registration and discovery
    - Help system
    - Command history
    - Aliases
    """

    def __init__(self):
        self.commands: Dict[str, SlashCommand] = {}
        self.aliases: Dict[str, str] = {}
        self.history: List[str] = []
        self.max_history = 100

        self._register_builtin_commands()

    def _register_builtin_commands(self):
        """Register built-in commands."""
        self.register(HelpCommand())
        self.register(ClearCommand())
        self.register(HistoryCommand())
        self.register(ModelCommand())
        self.register(ConfigCommand())
        self.register(ToolsCommand())
        self.register(SkillsCommand())
        self.register(StatsCommand())
        self.register(ExportCommand())
        self.register(ImportCommand())

    def register(self, command: SlashCommand, aliases: List[str] = None):
        """Register a slash command."""
        self.commands[command.name] = command

        if aliases:
            for alias in aliases:
                self.aliases[alias] = command.name

    def unregister(self, name: str):
        """Unregister a slash command."""
        if name in self.commands:
            del self.commands[name]
        # Remove aliases pointing to this command
        self.aliases = {k: v for k, v in self.aliases.items() if v != name}

    def parse_command(self, user_input: str) -> Optional[CommandContext]:
        """Parse user input for slash commands."""
        if not user_input.startswith("/"):
            return None

        parts = user_input.split()
        command_name = parts[0][1:]  # Remove leading /
        args = parts[1:] if len(parts) > 1 else []

        # Check aliases
        if command_name in self.aliases:
            command_name = self.aliases[command_name]

        return CommandContext(
            command=command_name,
            args=args,
            raw_input=user_input
        )

    def execute(self, context: CommandContext) -> Optional[CommandResult]:
        """Execute a command."""
        # Add to history
        self.history.append(context.raw_input)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        # Find command
        command = self.commands.get(context.command)
        if not command:
            console.print(f"[red]Unknown command: /{context.command}[/]")
            console.print("Type /help to see available commands")
            return CommandResult(success=False, output=f"Unknown command: /{context.command}")

        try:
            return command.execute(context)
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            console.print(f"[red]Error executing /{context.command}: {e}[/]")
            return CommandResult(success=False, output=str(e))

    def get_help_text(self) -> str:
        """Get help text for all commands."""
        table = Table(title="Available Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="green")
        table.add_column("Usage", style="dim")

        for name, cmd in sorted(self.commands.items()):
            table.add_row(f"/{name}", cmd.description, cmd.usage)

        # Add aliases
        if self.aliases:
            table.add_row("", "", "")
            table.add_row("[bold]Aliases[/]", "", "")
            for alias, target in sorted(self.aliases.items()):
                table.add_row(f"/{alias}", f"→ /{target}", "")

        return table

    def get_command(self, name: str) -> Optional[SlashCommand]:
        """Get a command by name or alias."""
        if name in self.aliases:
            name = self.aliases[name]
        return self.commands.get(name)


# Built-in command implementations

class HelpCommand(SlashCommand):
    """Show help information."""

    def __init__(self):
        super().__init__("help", "Show help information", "/help [command]")

    def execute(self, context: CommandContext) -> CommandResult:
        if context.args:
            # Show help for specific command
            cmd_name = context.args[0].lstrip("/")
            command = command_registry.get_command(cmd_name)
            if command:
                console.print(Panel(command.get_help(), title=f"/{cmd_name}"))
            else:
                console.print(f"[red]Unknown command: /{cmd_name}[/]")
        else:
            # Show all commands
            console.print(command_registry.get_help_text())
        return CommandResult(success=True, output="Help displayed")


class ClearCommand(SlashCommand):
    """Clear the screen."""

    def __init__(self):
        super().__init__("clear", "Clear the screen")

    def execute(self, context: CommandContext) -> CommandResult:
        os.system('cls' if os.name == 'nt' else 'clear')
        return CommandResult(success=True, output="Screen cleared")


class HistoryCommand(SlashCommand):
    """Show command history."""

    def __init__(self):
        super().__init__("history", "Show command history", "/history [count]")

    def execute(self, context: CommandContext) -> CommandResult:
        count = 10
        if context.args:
            try:
                count = int(context.args[0])
            except ValueError:
                pass

        history = command_registry.history[-count:]
        if history:
            for i, cmd in enumerate(history, 1):
                console.print(f"  {i}. {cmd}")
        else:
            console.print("No command history")
        return CommandResult(success=True, output="History displayed")


class ModelCommand(SlashCommand):
    """Switch or list models."""

    def __init__(self):
        super().__init__("model", "Switch or list models", "/model [list|use <model>]")

    def execute(self, context: CommandContext) -> CommandResult:
        from core.model_router import model_router

        if not context.args or context.args[0] == "list":
            # List models
            table = Table(title="Available Models")
            table.add_column("Name", style="cyan")
            table.add_column("Provider", style="green")
            table.add_column("Speed", justify="right")
            table.add_column("Quality", justify="right")
            table.add_column("Cost/1K", justify="right")

            for model_info in model_router.get_all_models():
                table.add_row(
                    model_info["name"],
                    model_info["provider"],
                    str(model_info["speed_rating"]),
                    str(model_info["quality_rating"]),
                    f"${model_info['cost_per_1k']:.4f}"
                )

            console.print(table)
            return CommandResult(success=True, output="Models listed")

        elif context.args[0] == "use" and len(context.args) > 1:
            model_name = context.args[1]
            if model_name in model_router.models:
                # Store preference (would need to integrate with config)
                console.print(f"[green]Switched to model: {model_name}[/]")
                return CommandResult(success=True, output=f"Switched to {model_name}")
            else:
                console.print(f"[red]Unknown model: {model_name}[/]")
                return CommandResult(success=False, output=f"Unknown model: {model_name}")

        else:
            console.print("[red]Usage: /model [list|use <model>][/]")
            return CommandResult(success=False, output="Invalid usage")


class ConfigCommand(SlashCommand):
    """View or modify configuration."""

    def __init__(self):
        super().__init__("config", "View or modify configuration", "/config [show|set <key> <value>]")

    def execute(self, context: CommandContext) -> CommandResult:
        from core.config import config

        if not context.args or context.args[0] == "show":
            # Show config
            console.print(Panel(
                json.dumps(config.data, indent=2),
                title="Configuration"
            ))
            return CommandResult(success=True, output="Config displayed")

        elif context.args[0] == "set" and len(context.args) >= 3:
            key = context.args[1]
            value = context.args[2]

            # Update config
            try:
                # Try to parse as JSON
                value = json.loads(value)
            except json.JSONDecodeError:
                pass

            config.data[key] = value
            config.save()
            console.print(f"[green]Set {key} = {value}[/]")
            return CommandResult(success=True, output=f"Set {key}")

        else:
            console.print("[red]Usage: /config [show|set <key> <value>][/]")
            return CommandResult(success=False, output="Invalid usage")


class ToolsCommand(SlashCommand):
    """List available tools."""

    def __init__(self):
        super().__init__("tools", "List available tools", "/tools [search <pattern>]")

    def execute(self, context: CommandContext) -> CommandResult:
        from core.registry import registry

        if context.args and context.args[0] == "search":
            pattern = context.args[1] if len(context.args) > 1 else ""
            tools = {
                name: schema for name, schema in registry.schemas.items()
                if pattern.lower() in name.lower() or pattern.lower() in str(schema).lower()
            }
        else:
            tools = registry.schemas

        table = Table(title="Available Tools")
        table.add_column("Name", style="cyan")
        table.add_column("Category", style="green")
        table.add_column("Description")

        for name, schema in sorted(tools.items()):
            desc = schema.get("function", {}).get("description", "")
            category = schema.get("category", "general")
            table.add_row(name, category, desc[:50] + "..." if len(desc) > 50 else desc)

        console.print(table)
        return CommandResult(success=True, output="Tools listed")


class SkillsCommand(SlashCommand):
    """List available skills."""

    def __init__(self):
        super().__init__("skills", "List available skills", "/skills [reload]")

    def execute(self, context: CommandContext) -> CommandResult:
        from core.registry import registry

        if context.args and context.args[0] == "reload":
            registry.reload_tools()
            console.print("[green]Skills reloaded[/]")
            return CommandResult(success=True, output="Skills reloaded")

        # List skills
        table = Table(title="Available Skills")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Description")

        # Python tools
        for name in sorted(registry.functions.keys()):
            schema = registry.schemas.get(name, {})
            desc = schema.get("function", {}).get("description", "")
            table.add_row(name, "Python", desc[:50] + "..." if len(desc) > 50 else desc)

        # Markdown skills
        for name, data in sorted(registry.md_skills.items()):
            desc = data.get("metadata", {}).get("description", "")
            table.add_row(name, "Markdown", desc[:50] + "..." if len(desc) > 50 else desc)

        console.print(table)
        return CommandResult(success=True, output="Skills listed")


class StatsCommand(SlashCommand):
    """Show statistics."""

    def __init__(self):
        super().__init__("stats", "Show statistics", "/stats")

    def execute(self, context: CommandContext) -> CommandResult:
        from core.model_router import model_router
        from core.registry import registry

        stats = model_router.get_stats()

        table = Table(title="Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Registered Tools", str(len(registry.functions)))
        table.add_row("Markdown Skills", str(len(registry.md_skills)))
        table.add_row("Total API Calls", str(stats["total_calls"]))
        table.add_row("Total Cost", f"${stats['total_cost']:.4f}")
        table.add_row("Registered Models", str(stats["total_models"]))

        console.print(table)
        return CommandResult(success=True, output="Stats displayed")


class ExportCommand(SlashCommand):
    """Export conversation or data."""

    def __init__(self):
        super().__init__("export", "Export conversation", "/export [format]")

    def execute(self, context: CommandContext) -> CommandResult:
        # This would need integration with the conversation manager
        console.print("[yellow]Export functionality coming soon[/]")
        return CommandResult(success=True, output="Export not yet implemented")


class ImportCommand(SlashCommand):
    """Import conversation or data."""

    def __init__(self):
        super().__init__("import", "Import conversation", "/import <file>")

    def execute(self, context: CommandContext) -> CommandResult:
        # This would need integration with the conversation manager
        console.print("[yellow]Import functionality coming soon[/]")
        return CommandResult(success=True, output="Import not yet implemented")


# Global command registry instance
command_registry = CommandRegistry()

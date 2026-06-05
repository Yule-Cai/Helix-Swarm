# core/model_router.py
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)

class TaskType(Enum):
    """Types of tasks for model routing."""
    SIMPLE = "simple"           # Simple questions, greetings
    CODE = "code"              # Code generation, editing
    COMPLEX = "complex"        # Complex reasoning, planning
    CREATIVE = "creative"      # Creative writing, brainstorming
    ANALYSIS = "analysis"      # Data analysis, research
    CHAT = "chat"              # General conversation

@dataclass
class ModelConfig:
    """Configuration for a model."""
    name: str
    provider: str
    max_tokens: int
    cost_per_1k_tokens: float
    speed_rating: int  # 1-10, higher is faster
    quality_rating: int  # 1-10, higher is better
    supports_tools: bool = True
    supports_streaming: bool = True
    supports_vision: bool = False

class ModelRouter:
    """
    Routes tasks to appropriate models based on complexity and requirements.

    Features:
    - Automatic task classification
    - Cost optimization
    - Fallback chains
    - Performance tracking
    """

    def __init__(self):
        self.models: Dict[str, ModelConfig] = {}
        self.task_routing: Dict[TaskType, List[str]] = {}
        self.fallback_chain: List[str] = []
        self.performance_stats: Dict[str, Dict] = {}

        self._register_default_models()
        self._setup_default_routing()

    def _register_default_models(self):
        """Register default model configurations."""
        # Fast models for simple tasks
        self.register_model(ModelConfig(
            name="gpt-4o-mini",
            provider="openai",
            max_tokens=4096,
            cost_per_1k_tokens=0.00015,
            speed_rating=9,
            quality_rating=7,
            supports_tools=True,
            supports_streaming=True
        ))

        # Balanced models
        self.register_model(ModelConfig(
            name="gpt-4o",
            provider="openai",
            max_tokens=4096,
            cost_per_1k_tokens=0.005,
            speed_rating=7,
            quality_rating=9,
            supports_tools=True,
            supports_streaming=True,
            supports_vision=True
        ))

        # Code-specialized models
        self.register_model(ModelConfig(
            name="claude-3.5-sonnet",
            provider="anthropic",
            max_tokens=4096,
            cost_per_1k_tokens=0.003,
            speed_rating=7,
            quality_rating=9,
            supports_tools=True,
            supports_streaming=True,
            supports_vision=True
        ))

        # Local models
        self.register_model(ModelConfig(
            name="local-model",
            provider="local",
            max_tokens=2048,
            cost_per_1k_tokens=0.0,
            speed_rating=8,
            quality_rating=6,
            supports_tools=True,
            supports_streaming=True
        ))

    def _setup_default_routing(self):
        """Setup default task routing rules."""
        self.task_routing = {
            TaskType.SIMPLE: ["gpt-4o-mini", "local-model"],
            TaskType.CODE: ["claude-3.5-sonnet", "gpt-4o"],
            TaskType.COMPLEX: ["gpt-4o", "claude-3.5-sonnet"],
            TaskType.CREATIVE: ["gpt-4o", "claude-3.5-sonnet"],
            TaskType.ANALYSIS: ["gpt-4o", "gpt-4o-mini"],
            TaskType.CHAT: ["gpt-4o-mini", "local-model"],
        }

        self.fallback_chain = ["gpt-4o-mini", "gpt-4o", "claude-3.5-sonnet", "local-model"]

    def register_model(self, config: ModelConfig):
        """Register a model configuration."""
        self.models[config.name] = config
        self.performance_stats[config.name] = {
            "total_calls": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_latency": 0.0,
            "success_rate": 1.0
        }

    def classify_task(self, user_input: str, context: Dict = None) -> TaskType:
        """
        Classify the task type based on user input.

        Uses simple heuristics. Can be enhanced with ML classification.
        """
        user_input_lower = user_input.lower()

        # Simple greetings and questions
        simple_patterns = ["hello", "hi", "hey", "thanks", "thank you", "bye", "goodbye"]
        if any(pattern in user_input_lower for pattern in simple_patterns):
            return TaskType.SIMPLE

        # Code-related keywords
        code_keywords = [
            "code", "function", "class", "implement", "debug", "fix", "bug",
            "test", "refactor", "optimize", "algorithm", "python", "javascript",
            "typescript", "java", "c++", "rust", "go", "sql", "html", "css"
        ]
        if any(keyword in user_input_lower for keyword in code_keywords):
            return TaskType.CODE

        # Complex reasoning
        complex_keywords = [
            "analyze", "compare", "evaluate", "design", "architect", "plan",
            "strategy", "research", "investigate", "explain why", "how does"
        ]
        if any(keyword in user_input_lower for keyword in complex_keywords):
            return TaskType.COMPLEX

        # Creative tasks
        creative_keywords = [
            "write", "create", "generate", "compose", "draft", "story",
            "poem", "article", "blog", "creative", "imagine"
        ]
        if any(keyword in user_input_lower for keyword in creative_keywords):
            return TaskType.CREATIVE

        # Analysis tasks
        analysis_keywords = [
            "data", "statistics", "metrics", "report", "summary", "trends",
            "patterns", "insights", "numbers", "calculate"
        ]
        if any(keyword in user_input_lower for keyword in analysis_keywords):
            return TaskType.ANALYSIS

        # Default to chat
        return TaskType.CHAT

    def route(self, task_type: TaskType = None, user_input: str = None,
              context: Dict = None, preferred_model: str = None) -> str:
        """
        Route to the best model for the task.

        Args:
            task_type: Type of task (auto-classified if not provided)
            user_input: User input for classification
            context: Additional context
            preferred_model: User's preferred model

        Returns:
            Model name to use
        """
        # Use preferred model if specified
        if preferred_model and preferred_model in self.models:
            return preferred_model

        # Classify task if not provided
        if task_type is None:
            task_type = self.classify_task(user_input or "", context)

        # Get models for this task type
        candidates = self.task_routing.get(task_type, self.fallback_chain)

        # Filter by availability and capabilities
        available = [
            m for m in candidates
            if m in self.models and self._is_model_available(m)
        ]

        if not available:
            # Fallback to any available model
            available = [m for m in self.fallback_chain if m in self.models]

        if not available:
            console.print("[yellow]⚠️ No models available, using default[/]")
            return "gpt-4o-mini"

        # Select based on performance stats
        return self._select_best_model(available, task_type)

    def _is_model_available(self, model_name: str) -> bool:
        """Check if a model is available and healthy."""
        stats = self.performance_stats.get(model_name, {})
        success_rate = stats.get("success_rate", 1.0)
        return success_rate > 0.5  # Consider unavailable if success rate < 50%

    def _select_best_model(self, candidates: List[str], task_type: TaskType) -> str:
        """Select the best model from candidates based on task type and performance."""
        if len(candidates) == 1:
            return candidates[0]

        # Score each candidate
        scores = {}
        for model_name in candidates:
            config = self.models.get(model_name)
            stats = self.performance_stats.get(model_name, {})

            if not config:
                continue

            # Base score from quality/speed ratings
            if task_type in [TaskType.CODE, TaskType.COMPLEX]:
                # Prioritize quality for complex tasks
                score = config.quality_rating * 0.7 + config.speed_rating * 0.3
            elif task_type in [TaskType.SIMPLE, TaskType.CHAT]:
                # Prioritize speed for simple tasks
                score = config.speed_rating * 0.7 + config.quality_rating * 0.3
            else:
                # Balanced
                score = config.quality_rating * 0.5 + config.speed_rating * 0.5

            # Adjust by success rate
            success_rate = stats.get("success_rate", 1.0)
            score *= success_rate

            # Adjust by cost (lower is better)
            cost = config.cost_per_1k_tokens
            if cost > 0:
                cost_factor = 1.0 / (1.0 + cost * 100)  # Normalize
                score *= (0.9 + cost_factor * 0.1)  # Small cost influence

            scores[model_name] = score

        # Return highest scoring model
        if scores:
            return max(scores, key=scores.get)
        return candidates[0]

    def record_usage(self, model_name: str, tokens_used: int, latency: float, success: bool):
        """Record model usage for performance tracking."""
        if model_name not in self.performance_stats:
            return

        stats = self.performance_stats[model_name]
        stats["total_calls"] += 1
        stats["total_tokens"] += tokens_used

        # Update cost
        config = self.models.get(model_name)
        if config:
            stats["total_cost"] += (tokens_used / 1000) * config.cost_per_1k_tokens

        # Update latency (running average)
        n = stats["total_calls"]
        stats["avg_latency"] = ((n - 1) * stats["avg_latency"] + latency) / n

        # Update success rate (exponential moving average)
        alpha = 0.1
        stats["success_rate"] = (1 - alpha) * stats["success_rate"] + alpha * (1.0 if success else 0.0)

    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """Get information about a model."""
        config = self.models.get(model_name)
        if not config:
            return None

        stats = self.performance_stats.get(model_name, {})

        return {
            "name": config.name,
            "provider": config.provider,
            "max_tokens": config.max_tokens,
            "cost_per_1k": config.cost_per_1k_tokens,
            "speed_rating": config.speed_rating,
            "quality_rating": config.quality_rating,
            "supports_tools": config.supports_tools,
            "supports_streaming": config.supports_streaming,
            "supports_vision": config.supports_vision,
            "total_calls": stats.get("total_calls", 0),
            "avg_latency": stats.get("avg_latency", 0),
            "success_rate": stats.get("success_rate", 1.0)
        }

    def get_all_models(self) -> List[Dict]:
        """Get information about all registered models."""
        return [self.get_model_info(name) for name in self.models]

    def get_stats(self) -> Dict:
        """Get overall routing statistics."""
        total_calls = sum(s["total_calls"] for s in self.performance_stats.values())
        total_cost = sum(s["total_cost"] for s in self.performance_stats.values())

        return {
            "total_models": len(self.models),
            "total_calls": total_calls,
            "total_cost": total_cost,
            "model_stats": self.performance_stats
        }


# Global model router instance
model_router = ModelRouter()

"""
研究想法生成器模块

基于文献综述生成新颖的研究想法，评估想法的可行性和新颖性。
支持真实 LLM 调用（Anthropic Claude / OpenAI GPT）。
"""

import asyncio
import json
from dataclasses import dataclass
from typing import List, Dict, Optional
import random

# 延迟导入 LLM 服务
try:
    from research_agent.services.llm_service import LLMService
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


@dataclass
class ResearchIdea:
    """研究想法数据类

    Attributes:
        title: 想法标题
        abstract: 摘要
        hypothesis: 研究假设
        methodology: 研究方法
        novelty_score: 新颖性分数 (0-1)
        feasibility_score: 可行性分数 (0-1)
    """
    title: str
    abstract: str
    hypothesis: str
    methodology: str
    novelty_score: float = 0.0
    feasibility_score: float = 0.0

    def __str__(self) -> str:
        """字符串表示"""
        return f"ResearchIdea(title='{self.title}', novelty={self.novelty_score:.2f}, feasibility={self.feasibility_score:.2f})"

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "title": self.title,
            "abstract": self.abstract,
            "hypothesis": self.hypothesis,
            "methodology": self.methodology,
            "novelty_score": self.novelty_score,
            "feasibility_score": self.feasibility_score,
        }


class IdeaGenerator:
    """研究想法生成器

    基于提供的论文列表生成新颖的研究想法，并评估其可行性和新颖性。
    支持真实 LLM 调用和 Mock 模式。
    """

    # 预定义的研究想法模板（Mock 模式使用）
    _IDEA_TEMPLATES: List[Dict[str, str]] = [
        {
            "title": "Neuro-Symbolic Integration for Robust AI Systems",
            "abstract": "Combining neural networks with symbolic reasoning to improve robustness and interpretability.",
            "hypothesis": "Integrating symbolic reasoning with neural networks will improve model robustness.",
            "methodology": "Develop a hybrid architecture combining transformers with logic programming."
        },
        {
            "title": "Few-Shot Learning with Meta-Learning Enhancement",
            "abstract": "Enhancing few-shot learning performance through advanced meta-learning techniques.",
            "hypothesis": "Meta-learning can significantly improve few-shot learning performance.",
            "methodology": "Design a meta-learning framework with attention mechanisms."
        },
        {
            "title": "Explainable AI through Attention Visualization",
            "abstract": "Improving AI explainability by visualizing attention patterns in transformer models.",
            "hypothesis": "Attention visualization can provide intuitive explanations for model decisions.",
            "methodology": "Develop attention visualization tools and conduct user studies."
        }
    ]

    # 评分常量
    DEFAULT_BASE_NOVELTY: float = 0.8
    DEFAULT_BASE_FEASIBILITY: float = 0.7
    MAX_PENALTY_PER_PAPER: float = 0.05
    MAX_TOTAL_PENALTY: float = 0.3
    RANDOM_VARIATION: float = 0.1

    def __init__(self, llm_service: Optional['LLMService'] = None, use_llm: bool = True):
        """
        初始化想法生成器

        Args:
            llm_service: LLM 服务实例（可选）
            use_llm: 是否使用 LLM（默认 True，如果 LLM 不可用则回退到 Mock）
        """
        self.llm_service = llm_service
        self.use_llm = use_llm and LLM_AVAILABLE and llm_service is not None

    def generate_idea(self, papers: List[Dict]) -> ResearchIdea:
        """Synchronous public API used by the orchestrator and tests."""
        if self.use_llm and self.llm_service:
            try:
                return self.generate_idea_sync(papers)
            except Exception as e:
                print(f"LLM generation failed, falling back to mock: {e}")
        return self._generate_idea_mock(papers)

    async def generate_idea_async(self, papers: List[Dict]) -> ResearchIdea:
        """
        基于论文列表生成研究想法

        Args:
            papers: 论文列表，每个论文包含 title, abstract 等字段

        Returns:
            生成的研究想法
        """
        if self.use_llm and self.llm_service:
            try:
                return await self._generate_idea_with_llm(papers)
            except Exception as e:
                print(f"LLM generation failed, falling back to mock: {e}")
                return self._generate_idea_mock(papers)
        else:
            return self._generate_idea_mock(papers)

    async def _generate_idea_with_llm(self, papers: List[Dict]) -> ResearchIdea:
        """使用 LLM 生成研究想法"""
        # 构建论文摘要
        paper_summaries = []
        for i, paper in enumerate(papers[:10], 1):  # 最多取 10 篇
            title = paper.get('title', 'Unknown')
            abstract = paper.get('summary', paper.get('abstract', ''))[:300]
            paper_summaries.append(f"{i}. {title}\n   Abstract: {abstract}")

        papers_text = "\n\n".join(paper_summaries)

        prompt = f"""Based on the following research papers, generate a novel and innovative research idea.

Papers:
{papers_text}

Please generate a research idea in the following JSON format:
{{
    "title": "A concise, descriptive title for the research idea",
    "abstract": "A 2-3 sentence abstract describing the research idea",
    "hypothesis": "The main hypothesis of the research",
    "methodology": "Brief description of the proposed methodology"
}}

Requirements:
1. The idea should be novel and not directly covered by the existing papers
2. It should build upon or combine ideas from the papers
3. It should be feasible to implement
4. It should have clear scientific contribution

Respond ONLY with the JSON object, no additional text."""

        system_prompt = "You are an expert researcher who generates innovative research ideas based on existing literature. Always respond with valid JSON."

        response = await self.llm_service.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.8,
            max_tokens=1000,
        )

        # 解析 JSON 响应
        try:
            # 尝试提取 JSON
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            idea_data = json.loads(json_str.strip())

            idea = ResearchIdea(
                title=idea_data.get("title", "Generated Research Idea"),
                abstract=idea_data.get("abstract", ""),
                hypothesis=idea_data.get("hypothesis", ""),
                methodology=idea_data.get("methodology", ""),
            )
        except (json.JSONDecodeError, KeyError) as e:
            # JSON 解析失败，使用响应文本
            idea = ResearchIdea(
                title="LLM Generated Idea",
                abstract=response[:500],
                hypothesis="See abstract for details",
                methodology="To be determined",
            )

        # 评估新颖性和可行性
        idea.novelty_score = await self.evaluate_novelty_with_llm(idea, papers)
        idea.feasibility_score = await self.evaluate_feasibility_with_llm(idea)

        return idea

    def _generate_idea_mock(self, papers: List[Dict]) -> ResearchIdea:
        """Mock 实现：随机选择一个想法模板"""
        template = random.choice(self._IDEA_TEMPLATES)

        idea = ResearchIdea(
            title=template["title"],
            abstract=template["abstract"],
            hypothesis=template["hypothesis"],
            methodology=template["methodology"]
        )

        # 评估新颖性和可行性
        idea.novelty_score = self.evaluate_novelty(idea, papers)
        idea.feasibility_score = self.evaluate_feasibility(idea)

        return idea

    async def evaluate_novelty_with_llm(self, idea: ResearchIdea, papers: List[Dict]) -> float:
        """使用 LLM 评估想法的新颖性"""
        if not self.use_llm or not self.llm_service:
            return self.evaluate_novelty(idea, papers)

        paper_titles = [p.get('title', '') for p in papers[:10]]
        papers_text = "\n".join(f"- {t}" for t in paper_titles if t)

        prompt = f"""Evaluate the novelty of this research idea on a scale of 0.0 to 1.0.

Research Idea:
- Title: {idea.title}
- Abstract: {idea.abstract}
- Hypothesis: {idea.hypothesis}

Existing Papers in the Field:
{papers_text}

Consider:
1. How different is this from existing work?
2. Does it combine ideas in a novel way?
3. Does it address a gap in the literature?

Respond with ONLY a number between 0.0 and 1.0 (e.g., 0.75)."""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=10,
            )
            # 提取数字
            score = float(response.strip())
            return max(0.0, min(1.0, score))
        except (ValueError, Exception):
            return self.evaluate_novelty(idea, papers)

    async def evaluate_feasibility_with_llm(self, idea: ResearchIdea) -> float:
        """使用 LLM 评估想法的可行性"""
        if not self.use_llm or not self.llm_service:
            return self.evaluate_feasibility(idea)

        prompt = f"""Evaluate the feasibility of this research idea on a scale of 0.0 to 1.0.

Research Idea:
- Title: {idea.title}
- Methodology: {idea.methodology}

Consider:
1. Can this be implemented with current technology?
2. Is the scope reasonable for a research project?
3. Are the required resources accessible?

Respond with ONLY a number between 0.0 and 1.0 (e.g., 0.65)."""

        try:
            response = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=10,
            )
            score = float(response.strip())
            return max(0.0, min(1.0, score))
        except (ValueError, Exception):
            return self.evaluate_feasibility(idea)

    def evaluate_novelty(self, idea: ResearchIdea, papers: List[Dict]) -> float:
        """评估想法的新颖性（Mock 实现）"""
        if not papers:
            return random.uniform(0.7, 0.95)

        base_novelty = self.DEFAULT_BASE_NOVELTY
        penalty = min(len(papers) * self.MAX_PENALTY_PER_PAPER, self.MAX_TOTAL_PENALTY)
        novelty = base_novelty - penalty
        novelty += random.uniform(-self.RANDOM_VARIATION, self.RANDOM_VARIATION)

        return max(0.1, min(1.0, novelty))

    def evaluate_feasibility(self, idea: ResearchIdea) -> float:
        """评估想法的可行性（Mock 实现）"""
        title_length = len(idea.title.split())
        base_feasibility = self.DEFAULT_BASE_FEASIBILITY

        if title_length > 8:
            base_feasibility -= 0.1

        feasibility = base_feasibility + random.uniform(-0.15, 0.15)
        return max(0.1, min(1.0, feasibility))

    # 同步版本的包装器
    def generate_idea_sync(self, papers: List[Dict]) -> ResearchIdea:
        """同步版本的 generate_idea"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在异步环境中，创建新的事件循环
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.generate_idea_async(papers))
                    return future.result()
            else:
                return loop.run_until_complete(self.generate_idea_async(papers))
        except RuntimeError:
            return asyncio.run(self.generate_idea_async(papers))

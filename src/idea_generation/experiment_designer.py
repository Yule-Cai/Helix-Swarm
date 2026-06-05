"""
实验设计器模块

基于研究想法自动设计实验方案，包括基线方法、评估指标、数据集需求等。
支持 LLM 驱动的智能实验设计。
"""

import asyncio
import json
from dataclasses import dataclass
from typing import List, Dict, Optional
from loguru import logger


@dataclass
class ExperimentPlan:
    """实验计划数据类
    
    Attributes:
        baselines: 基线方法列表
        metrics: 评估指标列表
        dataset_requirements: 数据集需求描述
        estimated_duration: 预估实验时长（小时）
        experiment_type: 实验类型（classification, regression, etc.）
        description: 实验描述
    """
    baselines: List[str]
    metrics: List[str]
    dataset_requirements: str
    estimated_duration: int
    experiment_type: str
    description: str
    
    def __str__(self) -> str:
        """字符串表示"""
        return (f"ExperimentPlan(type='{self.experiment_type}', "
                f"duration={self.estimated_duration}h, "
                f"baselines={len(self.baselines)}, metrics={len(self.metrics)})")


class ExperimentDesigner:
    """实验设计器
    
    基于研究想法自动设计实验方案，根据研究领域选择合适的基线方法和评估指标。
    当前为规则-based 实现，后续可接入 LLM 进行更智能的设计。
    """
    
    # 不同实验类型的默认配置
    _EXPERIMENT_CONFIGS: Dict[str, Dict[str, List[str]]] = {
        "classification": {
            "metrics": ["Accuracy", "Precision", "Recall", "F1-Score", "AUC-ROC"],
            "baselines": ["Logistic Regression", "SVM", "Random Forest", "XGBoost"],
            "dataset_keywords": ["labeled", "classes", "categories"]
        },
        "regression": {
            "metrics": ["MSE", "RMSE", "MAE", "R²"],
            "baselines": ["Linear Regression", "Ridge", "Lasso", "Random Forest Regressor"],
            "dataset_keywords": ["continuous", "numerical", "target"]
        },
        "nlp": {
            "metrics": ["BLEU", "ROUGE", "Perplexity", "Accuracy"],
            "baselines": ["BERT-base", "GPT-2", "LSTM", "Transformer"],
            "dataset_keywords": ["text", "language", "corpus", "tokens"]
        },
        "vision": {
            "metrics": ["Accuracy", "mAP", "IoU", "PSNR"],
            "baselines": ["ResNet", "VGG", "YOLO", "U-Net"],
            "dataset_keywords": ["images", "video", "visual", "pixels"]
        },
        "few-shot": {
            "metrics": ["Accuracy", "Support Accuracy", "Query Accuracy"],
            "baselines": ["Prototypical Networks", "MAML", "Matching Networks", "Fine-tuning"],
            "dataset_keywords": ["few-shot", "meta-learning", "episodes"]
        },
        "explainability": {
            "metrics": ["Faithfulness", "Comprehensibility", "Stability", "Sparsity"],
            "baselines": ["LIME", "SHAP", "Attention Visualization", "Feature Importance"],
            "dataset_keywords": ["interpretability", "explainability", "transparent"]
        }
    }
    
    # 实验类型关键词映射（按优先级排序）
    _TYPE_KEYWORDS: Dict[str, List[str]] = {
        "few-shot": ["few-shot", "few shot", "meta-learning", "meta learning", "low-resource"],
        "explainability": ["explainab", "interpretab", "transparent", "attention visual", "xai"],
        "nlp": ["text", "language", "nlp", "natural language", "token", "corpus", "bert", "gpt", "transformer"],
        "vision": ["image", "visual", "vision", "video", "pixel", "cnn", "resnet", "detection", "segmentation"],
        "regression": ["regression", "continuous", "numerical prediction", "forecasting"],
        "classification": ["classif", "categor", "labeled", "prediction", "recognition"]
    }
    
    # 数据集需求模板
    _DATASET_REQUIREMENTS: Dict[str, str] = {
        "classification": "Labeled dataset with clear class definitions. Train/validation/test splits required.",
        "regression": "Dataset with continuous target variables. Ensure sufficient samples for reliable estimation.",
        "nlp": "Text corpus with appropriate preprocessing. Consider tokenization and vocabulary size.",
        "vision": "Image/video dataset with annotations. Consider resolution, augmentation, and normalization.",
        "few-shot": "Dataset suitable for episode-based training. Multiple tasks/classes with limited samples.",
        "explainability": "Dataset with human-interpretable features. Consider user study requirements."
    }
    
    # 基础实验时长（小时）
    _BASE_DURATIONS: Dict[str, int] = {
        "classification": 24,
        "regression": 20,
        "nlp": 48,
        "vision": 72,
        "few-shot": 60,
        "explainability": 40
    }
    
    # 复杂度调整常量
    _COMPLEXITY_WORD_THRESHOLD: int = 20
    _COMPLEXITY_DURATION_INCREMENT: int = 24
    _NOVELTY_THRESHOLD: float = 0.8
    _NOVELTY_DURATION_INCREMENT: int = 12
    
    def __init__(self, llm_service=None) -> None:
        """
        初始化实验设计器

        Args:
            llm_service: LLM 服务实例（可选）
        """
        self.llm_service = llm_service
        self._logger = logger.bind(module="ExperimentDesigner")
    
    async def design_experiment_async(self, idea: 'ResearchIdea') -> ExperimentPlan:
        """
        基于研究想法设计实验（异步版本，支持 LLM）

        Args:
            idea: 研究想法

        Returns:
            实验计划
        """
        if self.llm_service:
            try:
                return await self._design_with_llm(idea)
            except Exception as e:
                self._logger.warning(f"LLM design failed, using rule-based: {e}")
                return self.design_experiment(idea)
        else:
            return self.design_experiment(idea)

    def design_experiment(self, idea: 'ResearchIdea') -> ExperimentPlan:
        """基于研究想法设计实验（同步版本，规则-based）

        Args:
            idea: 研究想法

        Returns:
            实验计划
        """
        # 确定实验类型
        experiment_type = self._determine_experiment_type(idea)

        # 建议基线方法
        baselines = self.suggest_baselines(idea)

        # 定义评估指标
        metrics = self.define_metrics(idea)

        # 确定数据集需求
        dataset_requirements = self._determine_dataset_requirements(idea, experiment_type)

        # 估算实验时长
        estimated_duration = self._estimate_duration(idea, experiment_type)

        # 生成实验描述
        description = self._generate_description(idea, experiment_type)

        return ExperimentPlan(
            baselines=baselines,
            metrics=metrics,
            dataset_requirements=dataset_requirements,
            estimated_duration=estimated_duration,
            experiment_type=experiment_type,
            description=description
        )

    async def _design_with_llm(self, idea: 'ResearchIdea') -> ExperimentPlan:
        """使用 LLM 设计实验"""
        prompt = f"""Design a detailed experiment plan for this research idea:

Title: {idea.title}
Abstract: {idea.abstract}
Hypothesis: {idea.hypothesis}
Methodology: {idea.methodology}

Please provide a JSON response with:
{{
    "experiment_type": "classification/regression/nlp/vision/few-shot/explainability",
    "baselines": ["baseline1", "baseline2", "baseline3", "baseline4"],
    "metrics": ["metric1", "metric2", "metric3", "metric4"],
    "dataset_requirements": "Detailed description of dataset needs",
    "estimated_duration": 48,
    "description": "Detailed experiment description"
}}

Consider:
1. Appropriate baselines for the research area
2. Standard evaluation metrics
3. Realistic time estimates
4. Specific dataset requirements

Respond ONLY with the JSON object."""

        system_prompt = "You are an expert research methodologist. Design rigorous experiments with appropriate baselines and metrics."

        response = await self.llm_service.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=1000,
        )

        # 解析响应
        json_str = response
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0]

        design_data = json.loads(json_str.strip())

        return ExperimentPlan(
            baselines=design_data.get("baselines", ["Baseline 1", "Baseline 2"]),
            metrics=design_data.get("metrics", ["Accuracy", "F1-Score"]),
            dataset_requirements=design_data.get("dataset_requirements", "Standard dataset required"),
            estimated_duration=design_data.get("estimated_duration", 48),
            experiment_type=design_data.get("experiment_type", "classification"),
            description=design_data.get("description", f"Experiment for {idea.title}"),
        )
    
    def suggest_baselines(self, idea: 'ResearchIdea') -> List[str]:
        """为研究想法建议基线方法
        
        Args:
            idea: 研究想法
            
        Returns:
            基线方法列表
        """
        experiment_type = self._determine_experiment_type(idea)
        config = self._EXPERIMENT_CONFIGS.get(experiment_type, self._EXPERIMENT_CONFIGS["classification"])
        return config["baselines"].copy()
    
    def define_metrics(self, idea: 'ResearchIdea') -> List[str]:
        """为研究想法定义评估指标
        
        Args:
            idea: 研究想法
            
        Returns:
            评估指标列表
        """
        experiment_type = self._determine_experiment_type(idea)
        config = self._EXPERIMENT_CONFIGS.get(experiment_type, self._EXPERIMENT_CONFIGS["classification"])
        return config["metrics"].copy()
    
    def _determine_experiment_type(self, idea: 'ResearchIdea') -> str:
        """根据想法确定实验类型
        
        Args:
            idea: 研究想法
            
        Returns:
            实验类型
        """
        # 合并标题、摘要、方法用于关键词匹配
        text = f"{idea.title} {idea.abstract} {idea.methodology}".lower()
        
        # 按优先级检查关键词
        for exp_type, keywords in self._TYPE_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                return exp_type
        
        # 默认类型
        return "classification"
    
    def _determine_dataset_requirements(self, idea: 'ResearchIdea', experiment_type: str) -> str:
        """确定数据集需求
        
        Args:
            idea: 研究想法
            experiment_type: 实验类型
            
        Returns:
            数据集需求描述
        """
        base_requirement = self._DATASET_REQUIREMENTS.get(
            experiment_type, 
            self._DATASET_REQUIREMENTS["classification"]
        )
        
        # 添加基于想法的特定需求
        text_lower = f"{idea.title} {idea.abstract}".lower()
        if "neuro-symbolic" in text_lower:
            base_requirement += " Integration with symbolic reasoning components required."
        
        return base_requirement
    
    def _estimate_duration(self, idea: 'ResearchIdea', experiment_type: str) -> int:
        """估算实验时长（小时）
        
        Args:
            idea: 研究想法
            experiment_type: 实验类型
            
        Returns:
            预估时长（小时）
        """
        # 基础时长
        duration = self._BASE_DURATIONS.get(experiment_type, 24)
        
        # 根据想法复杂度调整
        complexity_indicators = len(idea.title.split()) + len(idea.methodology.split())
        if complexity_indicators > self._COMPLEXITY_WORD_THRESHOLD:
            duration += self._COMPLEXITY_DURATION_INCREMENT
        
        # 根据新颖性调整（越高越需要更多时间）
        if idea.novelty_score > self._NOVELTY_THRESHOLD:
            duration += self._NOVELTY_DURATION_INCREMENT
        
        return duration
    
    def _generate_description(self, idea: 'ResearchIdea', experiment_type: str) -> str:
        """生成实验描述
        
        Args:
            idea: 研究想法
            experiment_type: 实验类型
            
        Returns:
            实验描述
        """
        return (f"Experiment for '{idea.title}'. "
                f"Type: {experiment_type}. "
                f"Testing hypothesis: {idea.hypothesis[:100]}...")

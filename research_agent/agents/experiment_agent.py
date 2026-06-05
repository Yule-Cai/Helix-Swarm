"""
实验设计Agent

负责实验设计、样本量计算、统计功效分析和实验方案优化。
"""

import asyncio
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from loguru import logger
import numpy as np
from scipy import stats

from ..core.agent_base import AgentBase, AgentResult
from ..services.llm_service import LLMService


class Variable(BaseModel):
    """变量模型"""
    name: str = Field(..., description="变量名称")
    type: str = Field(..., description="变量类型 (independent, dependent, control, confounding)")
    data_type: str = Field("continuous", description="数据类型 (continuous, categorical, ordinal)")
    description: str = Field("", description="变量描述")
    measurement: str = Field("", description="测量方法")
    units: str = Field("", description="单位")
    levels: List[Any] = Field(default_factory=list, description="水平/类别")
    range: Optional[Tuple[float, float]] = Field(None, description="取值范围")


class Hypothesis(BaseModel):
    """假设模型"""
    id: str = Field(..., description="假设ID")
    type: str = Field("alternative", description="假设类型 (null, alternative)")
    statement: str = Field(..., description="假设陈述")
    variables: List[str] = Field(default_factory=list, description="相关变量")
    direction: str = Field("two_tailed", description="方向 (one_tailed, two_tailed)")
    test_type: str = Field("", description="建议的检验类型")


class ExperimentDesign(BaseModel):
    """实验设计模型"""
    id: str = Field(..., description="实验ID")
    title: str = Field(..., description="实验标题")
    description: str = Field("", description="实验描述")
    research_question: str = Field("", description="研究问题")
    hypotheses: List[Hypothesis] = Field(default_factory=list, description="假设列表")
    variables: List[Variable] = Field(default_factory=list, description="变量列表")
    design_type: str = Field("between_subjects", description="设计类型")
    sample_size: int = Field(0, description="样本量")
    power: float = Field(0.8, description="统计功效")
    alpha: float = Field(0.05, description="显著性水平")
    effect_size: float = Field(0.5, description="效应量")
    randomization: bool = Field(True, description="是否随机化")
    blinding: str = Field("none", description="盲法 (none, single, double)")
    controls: List[str] = Field(default_factory=list, description="控制措施")
    procedure: List[str] = Field(default_factory=list, description="实验步骤")
    materials: List[str] = Field(default_factory=list, description="实验材料")
    data_collection: Dict[str, Any] = Field(default_factory=dict, description="数据收集方法")
    analysis_plan: Dict[str, Any] = Field(default_factory=dict, description="分析计划")
    ethical_considerations: List[str] = Field(default_factory=list, description="伦理考虑")
    timeline: Dict[str, Any] = Field(default_factory=dict, description="时间线")
    budget: Dict[str, Any] = Field(default_factory=dict, description="预算")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    status: str = Field("draft", description="状态")


class PowerAnalysis(BaseModel):
    """统计功效分析"""
    sample_size: int = Field(0, description="样本量")
    effect_size: float = Field(0.0, description="效应量")
    alpha: float = Field(0.05, description="显著性水平")
    power: float = Field(0.0, description="统计功效")
    test_type: str = Field("", description="检验类型")
    tails: int = Field(2, description="单尾/双尾")
    groups: int = Field(2, description="组数")
    recommendations: List[str] = Field(default_factory=list, description="建议")


class ExperimentAgent(AgentBase):
    """
    实验设计Agent
    
    负责实验设计、样本量计算、统计功效分析和实验方案优化。
    
    Features:
        - 实验设计生成
        - 假设制定
        - 变量识别和操作化
        - 样本量计算
        - 统计功效分析
        - 实验方案优化
        - 伦理审查辅助
        - 数据收集计划
    """
    
    def __init__(self, llm_service: LLMService, name: str = "ExperimentAgent"):
        """
        初始化实验设计Agent
        
        Args:
            llm_service: LLM服务
            name: Agent名称
        """
        super().__init__(name=name)
        self.llm_service = llm_service
        self._logger = logger.bind(module="ExperimentAgent")
        
        # 实验设计存储
        self._experiments: Dict[str, ExperimentDesign] = {}
        
        # 常见效应量参考
        self._effect_size_references = {
            "small": 0.2,
            "medium": 0.5,
            "large": 0.8,
        }
        
        # 常见检验类型
        self._test_types = {
            "t_test_independent": "独立样本t检验",
            "t_test_paired": "配对样本t检验",
            "anova_one_way": "单因素方差分析",
            "anova_two_way": "双因素方差分析",
            "chi_square": "卡方检验",
            "correlation": "相关分析",
            "regression": "回归分析",
            "mann_whitney": "Mann-Whitney U检验",
            "wilcoxon": "Wilcoxon符号秩检验",
            "kruskal_wallis": "Kruskal-Wallis检验",
        }
    
    async def execute(self, **kwargs) -> AgentResult:
        """
        执行实验设计任务
        
        Args:
            **kwargs: 任务参数
                - action: 操作类型 (create, design, power, optimize, validate, export)
                - experiment_id: 实验ID
                - research_question: 研究问题
                - design_type: 设计类型
                - variables: 变量列表
                
        Returns:
            AgentResult: 执行结果
        """
        action = kwargs.get("action", "create")
        
        try:
            if action == "create":
                result = await self.create_experiment(
                    title=kwargs["title"],
                    research_question=kwargs.get("research_question", ""),
                    design_type=kwargs.get("design_type", "between_subjects"),
                )
            elif action == "design":
                result = await self.generate_design(
                    research_question=kwargs["research_question"],
                    variables=kwargs.get("variables", []),
                    constraints=kwargs.get("constraints", {}),
                )
            elif action == "power":
                result = await self.power_analysis(
                    test_type=kwargs.get("test_type", "t_test_independent"),
                    effect_size=kwargs.get("effect_size", 0.5),
                    alpha=kwargs.get("alpha", 0.05),
                    power=kwargs.get("power", 0.8),
                    groups=kwargs.get("groups", 2),
                )
            elif action == "sample_size":
                result = await self.calculate_sample_size(
                    test_type=kwargs.get("test_type", "t_test_independent"),
                    effect_size=kwargs.get("effect_size", 0.5),
                    alpha=kwargs.get("alpha", 0.05),
                    power=kwargs.get("power", 0.8),
                    groups=kwargs.get("groups", 2),
                )
            elif action == "optimize":
                result = await self.optimize_design(
                    experiment_id=kwargs["experiment_id"],
                    optimization_goals=kwargs.get("optimization_goals", []),
                )
            elif action == "validate":
                result = await self.validate_design(
                    experiment_id=kwargs["experiment_id"],
                )
            elif action == "export":
                result = await self.export_design(
                    experiment_id=kwargs["experiment_id"],
                    format=kwargs.get("format", "markdown"),
                )
            elif action == "hypothesis":
                result = await self.generate_hypotheses(
                    research_question=kwargs["research_question"],
                    variables=kwargs.get("variables", []),
                )
            elif action == "procedure":
                result = await self.generate_procedure(
                    experiment_id=kwargs["experiment_id"],
                )
            elif action == "analysis_plan":
                result = await self.generate_analysis_plan(
                    experiment_id=kwargs["experiment_id"],
                )
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown action: {action}",
                    agent_name=self.name,
                )
            
            return AgentResult(
                success=True,
                data=result,
                agent_name=self.name,
            )
            
        except Exception as e:
            self._logger.exception(f"Error in ExperimentAgent: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                agent_name=self.name,
            )
    
    async def create_experiment(
        self,
        title: str,
        research_question: str = "",
        design_type: str = "between_subjects",
    ) -> ExperimentDesign:
        """
        创建实验设计
        
        Args:
            title: 实验标题
            research_question: 研究问题
            design_type: 设计类型
            
        Returns:
            ExperimentDesign: 实验设计对象
        """
        self._logger.info(f"Creating experiment: {title}")
        
        # 生成实验ID
        exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建实验设计
        experiment = ExperimentDesign(
            id=exp_id,
            title=title,
            research_question=research_question,
            design_type=design_type,
        )
        
        # 存储实验
        self._experiments[exp_id] = experiment
        
        self._logger.info(f"Experiment created: {exp_id}")
        
        return experiment
    
    async def generate_design(
        self,
        research_question: str,
        variables: List[Dict[str, Any]] = None,
        constraints: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        生成实验设计
        
        Args:
            research_question: 研究问题
            variables: 变量列表
            constraints: 约束条件
            
        Returns:
            Dict[str, Any]: 设计建议
        """
        self._logger.info(f"Generating design for: {research_question}")
        
        variables = variables or []
        constraints = constraints or {}
        
        # 使用LLM生成设计建议
        prompt = f"""
        请为以下研究问题生成实验设计建议：
        
        研究问题：{research_question}
        
        变量信息：
        {self._format_variables(variables)}
        
        约束条件：
        {self._format_constraints(constraints)}
        
        请提供以下方面的建议：
        1. 实验设计类型（被试内/被试间/混合设计）
        2. 自变量操作化
        3. 因变量测量
        4. 控制变量
        5. 样本量建议
        6. 随机化和盲法
        7. 可能的混淆变量及控制方法
        
        请以JSON格式输出：
        {{
            "design_type": "设计类型",
            "independent_variables": ["自变量1", "自变量2"],
            "dependent_variables": ["因变量1", "因变量2"],
            "control_variables": ["控制变量1", "控制变量2"],
            "sample_size_recommendation": "样本量建议",
            "randomization_method": "随机化方法",
            "blinding": "盲法",
            "confounding_variables": ["混淆变量1", "混淆变量2"],
            "control_methods": ["控制方法1", "控制方法2"],
            "design_rationale": "设计理由"
        }}
        """
        
        response = await self.llm_service.generate(prompt)
        
        try:
            import json
            design_suggestions = json.loads(response)
        except:
            design_suggestions = {
                "design_type": "between_subjects",
                "design_rationale": response,
            }
        
        return design_suggestions
    
    def _format_variables(self, variables: List[Dict[str, Any]]) -> str:
        """格式化变量信息"""
        if not variables:
            return "未提供变量信息"
        
        lines = []
        for var in variables:
            lines.append(f"- {var.get('name', '未知')} ({var.get('type', '未知')}): {var.get('description', '')}")
        
        return "\n".join(lines)
    
    def _format_constraints(self, constraints: Dict[str, Any]) -> str:
        """格式化约束条件"""
        if not constraints:
            return "无特殊约束"
        
        lines = []
        for key, value in constraints.items():
            lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)
    
    async def power_analysis(
        self,
        test_type: str = "t_test_independent",
        effect_size: float = 0.5,
        alpha: float = 0.05,
        power: float = 0.8,
        groups: int = 2,
    ) -> PowerAnalysis:
        """
        统计功效分析
        
        Args:
            test_type: 检验类型
            effect_size: 效应量
            alpha: 显著性水平
            power: 统计功效
            groups: 组数
            
        Returns:
            PowerAnalysis: 功效分析结果
        """
        self._logger.info(f"Power analysis: {test_type}, effect_size={effect_size}")
        
        # 计算样本量
        sample_size = self._calculate_sample_size(
            test_type=test_type,
            effect_size=effect_size,
            alpha=alpha,
            power=power,
            groups=groups,
        )
        
        # 生成建议
        recommendations = self._generate_power_recommendations(
            test_type=test_type,
            effect_size=effect_size,
            alpha=alpha,
            power=power,
            sample_size=sample_size,
        )
        
        analysis = PowerAnalysis(
            sample_size=sample_size,
            effect_size=effect_size,
            alpha=alpha,
            power=power,
            test_type=test_type,
            groups=groups,
            recommendations=recommendations,
        )
        
        return analysis
    
    def _calculate_sample_size(
        self,
        test_type: str,
        effect_size: float,
        alpha: float,
        power: float,
        groups: int = 2,
    ) -> int:
        """
        计算样本量
        
        Args:
            test_type: 检验类型
            effect_size: 效应量
            alpha: 显著性水平
            power: 统计功效
            groups: 组数
            
        Returns:
            int: 样本量
        """
        # 使用简化的样本量计算公式
        # 实际应用中应使用更精确的统计软件
        
        if test_type in ["t_test_independent", "t_test_paired"]:
            # t检验样本量计算
            z_alpha = stats.norm.ppf(1 - alpha/2)
            z_beta = stats.norm.ppf(power)
            
            if test_type == "t_test_independent":
                # 独立样本t检验
                n = ((z_alpha + z_beta) / effect_size) ** 2
                n = math.ceil(n) * 2  # 两组
            else:
                # 配对样本t检验
                n = ((z_alpha + z_beta) / effect_size) ** 2
                n = math.ceil(n)
        
        elif test_type.startswith("anova"):
            # 方差分析样本量
            z_alpha = stats.norm.ppf(1 - alpha/groups)
            z_beta = stats.norm.ppf(power)
            
            n_per_group = ((z_alpha + z_beta) / effect_size) ** 2
            n = math.ceil(n_per_group) * groups
        
        elif test_type == "chi_square":
            # 卡方检验样本量
            z_alpha = stats.norm.ppf(1 - alpha)
            z_beta = stats.norm.ppf(power)
            
            n = ((z_alpha + z_beta) / effect_size) ** 2
            n = math.ceil(n)
        
        elif test_type == "correlation":
            # 相关分析样本量
            z_alpha = stats.norm.ppf(1 - alpha/2)
            z_beta = stats.norm.ppf(power)
            
            # Fisher's z transformation
            z_effect = 0.5 * math.log((1 + effect_size) / (1 - effect_size))
            
            n = ((z_alpha + z_beta) / z_effect) ** 2 + 3
            n = math.ceil(n)
        
        else:
            # 默认计算
            z_alpha = stats.norm.ppf(1 - alpha/2)
            z_beta = stats.norm.ppf(power)
            
            n = ((z_alpha + z_beta) / effect_size) ** 2
            n = math.ceil(n)
        
        return max(n, 10)  # 最小样本量为10
    
    def _generate_power_recommendations(
        self,
        test_type: str,
        effect_size: float,
        alpha: float,
        power: float,
        sample_size: int,
    ) -> List[str]:
        """
        生成功效分析建议
        
        Args:
            test_type: 检验类型
            effect_size: 效应量
            alpha: 显著性水平
            power: 统计功效
            sample_size: 样本量
            
        Returns:
            List[str]: 建议列表
        """
        recommendations = []
        
        # 效应量建议
        if effect_size < 0.2:
            recommendations.append("效应量较小，可能需要较大的样本量才能检测到效应")
        elif effect_size > 0.8:
            recommendations.append("效应量较大，较小的样本量可能就足够")
        
        # 样本量建议
        if sample_size < 30:
            recommendations.append("样本量较小，结果可能不够稳定")
        elif sample_size > 1000:
            recommendations.append("样本量较大，考虑成本和可行性")
        
        # 功效建议
        if power < 0.8:
            recommendations.append("统计功效较低（<0.8），建议增加样本量以提高功效")
        
        # 检验类型建议
        if test_type == "t_test_independent" and sample_size < 20:
            recommendations.append("独立样本t检验样本量较小，考虑使用非参数检验")
        
        # 通用建议
        recommendations.append(f"建议每组至少{math.ceil(sample_size/2)}名参与者")
        recommendations.append("考虑增加10-20%的样本量以应对流失")
        
        return recommendations
    
    async def calculate_sample_size(
        self,
        test_type: str = "t_test_independent",
        effect_size: float = 0.5,
        alpha: float = 0.05,
        power: float = 0.8,
        groups: int = 2,
    ) -> Dict[str, Any]:
        """
        计算样本量
        
        Args:
            test_type: 检验类型
            effect_size: 效应量
            alpha: 显著性水平
            power: 统计功效
            groups: 组数
            
        Returns:
            Dict[str, Any]: 样本量计算结果
        """
        self._logger.info(f"Calculating sample size: {test_type}")
        
        # 计算不同功效下的样本量
        power_levels = [0.7, 0.8, 0.9, 0.95]
        sample_sizes = {}
        
        for p in power_levels:
            n = self._calculate_sample_size(
                test_type=test_type,
                effect_size=effect_size,
                alpha=alpha,
                power=p,
                groups=groups,
            )
            sample_sizes[f"power_{p}"] = n
        
        # 计算不同效应量下的样本量
        effect_sizes = [0.2, 0.5, 0.8]
        effect_size_samples = {}
        
        for es in effect_sizes:
            n = self._calculate_sample_size(
                test_type=test_type,
                effect_size=es,
                alpha=alpha,
                power=power,
                groups=groups,
            )
            effect_size_samples[f"effect_{es}"] = n
        
        # 推荐样本量
        recommended_n = self._calculate_sample_size(
            test_type=test_type,
            effect_size=effect_size,
            alpha=alpha,
            power=power,
            groups=groups,
        )
        
        # 考虑流失率的样本量
        attrition_rate = 0.15  # 假设15%流失率
        adjusted_n = math.ceil(recommended_n / (1 - attrition_rate))
        
        return {
            "test_type": test_type,
            "effect_size": effect_size,
            "alpha": alpha,
            "power": power,
            "groups": groups,
            "recommended_sample_size": recommended_n,
            "adjusted_sample_size": adjusted_n,
            "attrition_rate": attrition_rate,
            "sample_sizes_by_power": sample_sizes,
            "sample_sizes_by_effect": effect_size_samples,
            "per_group_size": math.ceil(recommended_n / groups),
            "adjusted_per_group_size": math.ceil(adjusted_n / groups),
        }
    
    async def optimize_design(
        self,
        experiment_id: str,
        optimization_goals: List[str] = None,
    ) -> Dict[str, Any]:
        """
        优化实验设计
        
        Args:
            experiment_id: 实验ID
            optimization_goals: 优化目标
            
        Returns:
            Dict[str, Any]: 优化建议
        """
        self._logger.info(f"Optimizing design: {experiment_id}")
        
        if experiment_id not in self._experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        experiment = self._experiments[experiment_id]
        optimization_goals = optimization_goals or ["power", "cost", "feasibility"]
        
        # 使用LLM生成优化建议
        prompt = f"""
        请为以下实验设计提供优化建议：
        
        实验标题：{experiment.title}
        研究问题：{experiment.research_question}
        设计类型：{experiment.design_type}
        当前样本量：{experiment.sample_size}
        统计功效：{experiment.power}
        显著性水平：{experiment.alpha}
        效应量：{experiment.effect_size}
        
        优化目标：{', '.join(optimization_goals)}
        
        请从以下方面提供优化建议：
        1. 提高统计功效
        2. 降低成本
        3. 提高可行性
        4. 减少混淆变量
        5. 提高内部效度
        6. 提高外部效度
        
        请以JSON格式输出：
        {{
            "current_assessment": "当前设计评估",
            "optimization_suggestions": [
                {{
                    "aspect": "优化方面",
                    "current_value": "当前值",
                    "suggested_value": "建议值",
                    "rationale": "理由",
                    "impact": "预期影响"
                }}
            ],
            "trade_offs": ["权衡1", "权衡2"],
            "priority_actions": ["优先行动1", "优先行动2"]
        }}
        """
        
        response = await self.llm_service.generate(prompt)
        
        try:
            import json
            optimization = json.loads(response)
        except:
            optimization = {
                "current_assessment": response,
                "optimization_suggestions": [],
            }
        
        return optimization
    
    async def validate_design(self, experiment_id: str) -> Dict[str, Any]:
        """
        验证实验设计
        
        Args:
            experiment_id: 实验ID
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        self._logger.info(f"Validating design: {experiment_id}")
        
        if experiment_id not in self._experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        experiment = self._experiments[experiment_id]
        
        issues = []
        warnings = []
        suggestions = []
        
        # 检查假设
        if not experiment.hypotheses:
            issues.append("未定义研究假设")
        
        # 检查变量
        if not experiment.variables:
            issues.append("未定义研究变量")
        
        # 检查样本量
        if experiment.sample_size < 10:
            warnings.append("样本量可能不足")
        
        # 检查统计功效
        if experiment.power < 0.8:
            warnings.append("统计功效较低（<0.8）")
        
        # 检查效应量
        if experiment.effect_size < 0.2:
            warnings.append("效应量较小，可能难以检测")
        
        # 检查设计类型
        valid_design_types = [
            "between_subjects", "within_subjects", "mixed",
            "factorial", "crossover", "repeated_measures"
        ]
        if experiment.design_type not in valid_design_types:
            issues.append(f"无效的设计类型: {experiment.design_type}")
        
        # 检查盲法
        if experiment.blinding == "none":
            suggestions.append("考虑使用单盲或双盲设计以减少偏差")
        
        # 检查随机化
        if not experiment.randomization:
            suggestions.append("考虑使用随机化以减少选择偏差")
        
        # 检查控制措施
        if not experiment.controls:
            warnings.append("未定义控制措施")
        
        # 检查伦理考虑
        if not experiment.ethical_considerations:
            warnings.append("未考虑伦理问题")
        
        # 生成验证报告
        validation_report = {
            "experiment_id": experiment_id,
            "title": experiment.title,
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "suggestions": suggestions,
            "issue_count": len(issues),
            "warning_count": len(warnings),
            "suggestion_count": len(suggestions),
            "overall_score": self._calculate_design_score(experiment),
        }
        
        return validation_report
    
    def _calculate_design_score(self, experiment: ExperimentDesign) -> float:
        """
        计算设计评分
        
        Args:
            experiment: 实验设计
            
        Returns:
            float: 设计评分 (0-100)
        """
        score = 100.0
        
        # 假设定义
        if not experiment.hypotheses:
            score -= 20
        
        # 变量定义
        if not experiment.variables:
            score -= 20
        
        # 样本量
        if experiment.sample_size < 30:
            score -= 10
        elif experiment.sample_size < 10:
            score -= 20
        
        # 统计功效
        if experiment.power < 0.8:
            score -= 15
        
        # 随机化
        if not experiment.randomization:
            score -= 10
        
        # 盲法
        if experiment.blinding == "none":
            score -= 5
        
        # 控制措施
        if not experiment.controls:
            score -= 10
        
        # 伦理考虑
        if not experiment.ethical_considerations:
            score -= 10
        
        return max(0, min(100, score))
    
    async def export_design(
        self,
        experiment_id: str,
        format: str = "markdown",
    ) -> Dict[str, Any]:
        """
        导出实验设计
        
        Args:
            experiment_id: 实验ID
            format: 导出格式
            
        Returns:
            Dict[str, Any]: 导出结果
        """
        self._logger.info(f"Exporting design: {experiment_id}")
        
        if experiment_id not in self._experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        experiment = self._experiments[experiment_id]
        
        # 生成导出内容
        if format == "markdown":
            content = self._to_markdown(experiment)
        elif format == "latex":
            content = self._to_latex(experiment)
        elif format == "json":
            import json
            content = json.dumps(experiment.dict(), indent=2, ensure_ascii=False, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{experiment_id}_{timestamp}.{format}"
        
        return {
            "experiment_id": experiment_id,
            "format": format,
            "filename": filename,
            "content": content,
            "message": f"实验设计已导出为{format}格式",
        }
    
    def _to_markdown(self, experiment: ExperimentDesign) -> str:
        """转换为Markdown格式"""
        lines = []
        
        # 标题
        lines.append(f"# {experiment.title}")
        lines.append("")
        
        # 基本信息
        lines.append("## 基本信息")
        lines.append(f"- **实验ID:** {experiment.id}")
        lines.append(f"- **设计类型:** {experiment.design_type}")
        lines.append(f"- **状态:** {experiment.status}")
        lines.append(f"- **创建时间:** {experiment.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 研究问题
        if experiment.research_question:
            lines.append("## 研究问题")
            lines.append(experiment.research_question)
            lines.append("")
        
        # 假设
        if experiment.hypotheses:
            lines.append("## 研究假设")
            for i, hyp in enumerate(experiment.hypotheses, 1):
                lines.append(f"{i}. **{hyp.type}:** {hyp.statement}")
            lines.append("")
        
        # 变量
        if experiment.variables:
            lines.append("## 变量")
            for var in experiment.variables:
                lines.append(f"- **{var.name}** ({var.type}): {var.description}")
            lines.append("")
        
        # 样本量和统计参数
        lines.append("## 统计参数")
        lines.append(f"- **样本量:** {experiment.sample_size}")
        lines.append(f"- **统计功效:** {experiment.power}")
        lines.append(f"- **显著性水平:** {experiment.alpha}")
        lines.append(f"- **效应量:** {experiment.effect_size}")
        lines.append("")
        
        # 实验控制
        lines.append("## 实验控制")
        lines.append(f"- **随机化:** {'是' if experiment.randomization else '否'}")
        lines.append(f"- **盲法:** {experiment.blinding}")
        if experiment.controls:
            lines.append("- **控制措施:**")
            for control in experiment.controls:
                lines.append(f"  - {control}")
        lines.append("")
        
        # 实验步骤
        if experiment.procedure:
            lines.append("## 实验步骤")
            for i, step in enumerate(experiment.procedure, 1):
                lines.append(f"{i}. {step}")
            lines.append("")
        
        # 数据收集
        if experiment.data_collection:
            lines.append("## 数据收集")
            for key, value in experiment.data_collection.items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")
        
        # 分析计划
        if experiment.analysis_plan:
            lines.append("## 分析计划")
            for key, value in experiment.analysis_plan.items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")
        
        # 伦理考虑
        if experiment.ethical_considerations:
            lines.append("## 伦理考虑")
            for consideration in experiment.ethical_considerations:
                lines.append(f"- {consideration}")
            lines.append("")
        
        # 时间线
        if experiment.timeline:
            lines.append("## 时间线")
            for key, value in experiment.timeline.items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")
        
        # 预算
        if experiment.budget:
            lines.append("## 预算")
            for key, value in experiment.budget.items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _to_latex(self, experiment: ExperimentDesign) -> str:
        """转换为LaTeX格式"""
        lines = []
        
        lines.append("\\documentclass[12pt]{article}")
        lines.append("\\usepackage[utf8]{inputenc}")
        lines.append("\\usepackage{amsmath}")
        lines.append("\\usepackage{booktabs}")
        lines.append("\\usepackage{hyperref}")
        lines.append("")
        lines.append(f"\\title{{{experiment.title}}}")
        lines.append("\\author{}")
        lines.append("\\date{\\today}")
        lines.append("")
        lines.append("\\begin{document}")
        lines.append("")
        lines.append("\\maketitle")
        lines.append("")
        
        # 研究问题
        if experiment.research_question:
            lines.append("\\section{研究问题}")
            lines.append(experiment.research_question)
            lines.append("")
        
        # 假设
        if experiment.hypotheses:
            lines.append("\\section{研究假设}")
            lines.append("\\begin{enumerate}")
            for hyp in experiment.hypotheses:
                lines.append(f"\\item \\textbf{{{hyp.type}:}} {hyp.statement}")
            lines.append("\\end{enumerate}")
            lines.append("")
        
        # 变量
        if experiment.variables:
            lines.append("\\section{变量}")
            lines.append("\\begin{itemize}")
            for var in experiment.variables:
                lines.append(f"\\item \\textbf{{{var.name}}} ({var.type}): {var.description}")
            lines.append("\\end{itemize}")
            lines.append("")
        
        # 统计参数
        lines.append("\\section{统计参数}")
        lines.append("\\begin{table}[h]")
        lines.append("\\centering")
        lines.append("\\begin{tabular}{ll}")
        lines.append("\\toprule")
        lines.append("参数 & 值 \\\\")
        lines.append("\\midrule")
        lines.append(f"样本量 & {experiment.sample_size} \\\\")
        lines.append(f"统计功效 & {experiment.power} \\\\")
        lines.append(f"显著性水平 & {experiment.alpha} \\\\")
        lines.append(f"效应量 & {experiment.effect_size} \\\\")
        lines.append("\\bottomrule")
        lines.append("\\end{tabular}")
        lines.append("\\caption{统计参数}")
        lines.append("\\end{table}")
        lines.append("")
        
        # 实验步骤
        if experiment.procedure:
            lines.append("\\section{实验步骤}")
            lines.append("\\begin{enumerate}")
            for step in experiment.procedure:
                lines.append(f"\\item {step}")
            lines.append("\\end{enumerate}")
            lines.append("")
        
        lines.append("\\end{document}")
        
        return "\n".join(lines)
    
    async def generate_hypotheses(
        self,
        research_question: str,
        variables: List[Dict[str, Any]] = None,
    ) -> List[Hypothesis]:
        """
        生成研究假设
        
        Args:
            research_question: 研究问题
            variables: 变量列表
            
        Returns:
            List[Hypothesis]: 假设列表
        """
        self._logger.info(f"Generating hypotheses for: {research_question}")
        
        variables = variables or []
        
        prompt = f"""
        请为以下研究问题生成研究假设：
        
        研究问题：{research_question}
        
        变量信息：
        {self._format_variables(variables)}
        
        请生成：
        1. 零假设（H0）
        2. 备择假设（H1）
        3. 可能的额外假设
        
        请以JSON格式输出：
        [
            {{
                "type": "null|alternative",
                "statement": "假设陈述",
                "variables": ["相关变量"],
                "direction": "one_tailed|two_tailed",
                "test_type": "建议的检验类型"
            }}
        ]
        """
        
        response = await self.llm_service.generate(prompt)
        
        try:
            import json
            hypotheses_data = json.loads(response)
            
            hypotheses = []
            for i, hyp_data in enumerate(hypotheses_data):
                hypothesis = Hypothesis(
                    id=f"hyp_{i+1}",
                    type=hyp_data.get("type", "alternative"),
                    statement=hyp_data.get("statement", ""),
                    variables=hyp_data.get("variables", []),
                    direction=hyp_data.get("direction", "two_tailed"),
                    test_type=hyp_data.get("test_type", ""),
                )
                hypotheses.append(hypothesis)
            
            return hypotheses
            
        except:
            # 如果解析失败，返回默认假设
            return [
                Hypothesis(
                    id="hyp_1",
                    type="null",
                    statement="没有显著效应",
                    direction="two_tailed",
                ),
                Hypothesis(
                    id="hyp_2",
                    type="alternative",
                    statement="存在显著效应",
                    direction="two_tailed",
                ),
            ]
    
    async def generate_procedure(self, experiment_id: str) -> List[str]:
        """
        生成实验步骤
        
        Args:
            experiment_id: 实验ID
            
        Returns:
            List[str]: 实验步骤
        """
        self._logger.info(f"Generating procedure for: {experiment_id}")
        
        if experiment_id not in self._experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        experiment = self._experiments[experiment_id]
        
        prompt = f"""
        请为以下实验设计生成详细的实验步骤：
        
        实验标题：{experiment.title}
        研究问题：{experiment.research_question}
        设计类型：{experiment.design_type}
        变量：{[v.name for v in experiment.variables]}
        
        请生成详细的实验步骤，包括：
        1. 参与者招募和筛选
        2. 知情同意
        3. 随机分组（如适用）
        4. 实验操作
        5. 数据收集
        6. 参与者 debriefing（如适用）
        
        请以列表形式输出，每步一行。
        """
        
        response = await self.llm_service.generate(prompt)
        procedure = [line.strip() for line in response.split('\n') if line.strip()]
        
        # 更新实验设计
        experiment.procedure = procedure
        experiment.updated_at = datetime.now()
        
        return procedure
    
    async def generate_analysis_plan(self, experiment_id: str) -> Dict[str, Any]:
        """
        生成分析计划
        
        Args:
            experiment_id: 实验ID
            
        Returns:
            Dict[str, Any]: 分析计划
        """
        self._logger.info(f"Generating analysis plan for: {experiment_id}")
        
        if experiment_id not in self._experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        experiment = self._experiments[experiment_id]
        
        prompt = f"""
        请为以下实验设计生成数据分析计划：
        
        实验标题：{experiment.title}
        设计类型：{experiment.design_type}
        变量：{[(v.name, v.type, v.data_type) for v in experiment.variables]}
        假设：{[h.statement for h in experiment.hypotheses]}
        
        请生成详细的数据分析计划，包括：
        1. 数据预处理步骤
        2. 描述性统计
        3. 假设检验方法
        4. 效应量计算
        5. 多重比较校正（如适用）
        6. 敏感性分析
        7. 缺失数据处理
        
        请以JSON格式输出：
        {{
            "data_preprocessing": ["步骤1", "步骤2"],
            "descriptive_statistics": ["统计1", "统计2"],
            "hypothesis_testing": {{
                "primary_analysis": "主要分析方法",
                "secondary_analyses": ["次要分析1", "次要分析2"],
                "effect_size_measures": ["效应量指标1", "效应量指标2"],
                "multiple_comparison_correction": "校正方法"
            }},
            "sensitivity_analyses": ["敏感性分析1", "敏感性分析2"],
            "missing_data_handling": "缺失数据处理方法",
            "assumptions_checking": ["假设检验1", "假设检验2"]
        }}
        """
        
        response = await self.llm_service.generate(prompt)
        
        try:
            import json
            analysis_plan = json.loads(response)
        except:
            analysis_plan = {
                "data_preprocessing": ["数据清洗", "异常值处理"],
                "descriptive_statistics": ["均值", "标准差", "频率分布"],
                "hypothesis_testing": {
                    "primary_analysis": response,
                },
            }
        
        # 更新实验设计
        experiment.analysis_plan = analysis_plan
        experiment.updated_at = datetime.now()
        
        return analysis_plan
    
    def get_experiment(self, experiment_id: str) -> Optional[ExperimentDesign]:
        """
        获取实验设计
        
        Args:
            experiment_id: 实验ID
            
        Returns:
            Optional[ExperimentDesign]: 实验设计对象
        """
        return self._experiments.get(experiment_id)
    
    def list_experiments(self) -> List[Dict[str, Any]]:
        """
        列出所有实验设计
        
        Returns:
            List[Dict[str, Any]]: 实验设计列表
        """
        experiments = []
        for exp_id, exp in self._experiments.items():
            experiments.append({
                "id": exp_id,
                "title": exp.title,
                "design_type": exp.design_type,
                "sample_size": exp.sample_size,
                "status": exp.status,
                "created_at": exp.created_at.isoformat(),
                "updated_at": exp.updated_at.isoformat(),
            })
        
        return experiments
    
    def delete_experiment(self, experiment_id: str) -> bool:
        """
        删除实验设计
        
        Args:
            experiment_id: 实验ID
            
        Returns:
            bool: 是否成功删除
        """
        if experiment_id in self._experiments:
            del self._experiments[experiment_id]
            self._logger.info(f"Experiment {experiment_id} deleted")
            return True
        return False
    
    def get_test_types(self) -> Dict[str, str]:
        """
        获取所有检验类型
        
        Returns:
            Dict[str, str]: 检验类型字典
        """
        return self._test_types
    
    def get_effect_size_references(self) -> Dict[str, float]:
        """
        获取效应量参考值
        
        Returns:
            Dict[str, float]: 效应量参考字典
        """
        return self._effect_size_references
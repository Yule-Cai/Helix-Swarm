"""
数据分析Agent

负责数据清洗、统计分析、可视化和机器学习。
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field
from loguru import logger
import pandas as pd
import numpy as np
from scipy import stats

from ..core.agent_base import AgentBase, AgentResult
from ..services.llm_service import LLMService


class DataProfile(BaseModel):
    """数据概况"""
    rows: int = Field(0, description="行数")
    columns: int = Field(0, description="列数")
    column_names: List[str] = Field(default_factory=list, description="列名")
    column_types: Dict[str, str] = Field(default_factory=dict, description="列类型")
    missing_values: Dict[str, int] = Field(default_factory=dict, description="缺失值")
    numeric_stats: Dict[str, Dict[str, float]] = Field(default_factory=dict, description="数值统计")
    categorical_stats: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="分类统计")
    data_quality_score: float = Field(0.0, description="数据质量评分")


class AnalysisResult(BaseModel):
    """分析结果"""
    analysis_type: str = Field(..., description="分析类型")
    title: str = Field("", description="分析标题")
    description: str = Field("", description="分析描述")
    results: Dict[str, Any] = Field(default_factory=dict, description="分析结果")
    visualizations: List[Dict[str, Any]] = Field(default_factory=list, description="可视化配置")
    insights: List[str] = Field(default_factory=list, description="洞察")
    recommendations: List[str] = Field(default_factory=list, description="建议")
    statistical_tests: List[Dict[str, Any]] = Field(default_factory=list, description="统计检验")


class DataAnalysisAgent(AgentBase):
    """
    数据分析Agent
    
    负责数据清洗、统计分析、可视化和机器学习。
    
    Features:
        - 数据加载和清洗
        - 探索性数据分析
        - 统计检验
        - 相关性分析
        - 回归分析
        - 聚类分析
        - 可视化生成
        - 洞察提取
    """
    
    def __init__(self, llm_service: LLMService, name: str = "DataAnalysisAgent"):
        """
        初始化数据分析Agent
        
        Args:
            llm_service: LLM服务
            name: Agent名称
        """
        super().__init__(name=name)
        self.llm_service = llm_service
        self._logger = logger.bind(module="DataAnalysisAgent")
        
        # 数据存储
        self._dataframes: Dict[str, pd.DataFrame] = {}
        self._analysis_history: List[AnalysisResult] = []
    
    async def execute(self, **kwargs) -> AgentResult:
        """
        执行数据分析任务
        
        Args:
            **kwargs: 任务参数
                - action: 操作类型 (load, profile, analyze, visualize, clean, export)
                - data: 数据
                - data_id: 数据ID
                - analysis_type: 分析类型
                - columns: 列名
                
        Returns:
            AgentResult: 执行结果
        """
        action = kwargs.get("action", "analyze")
        
        try:
            if action == "load":
                result = await self.load_data(
                    data=kwargs["data"],
                    data_id=kwargs.get("data_id", "default"),
                    format=kwargs.get("format", "csv"),
                )
            elif action == "profile":
                result = await self.profile_data(kwargs["data_id"])
            elif action == "analyze":
                result = await self.analyze_data(
                    data_id=kwargs["data_id"],
                    analysis_type=kwargs.get("analysis_type", "descriptive"),
                    columns=kwargs.get("columns"),
                    params=kwargs.get("params", {}),
                )
            elif action == "visualize":
                result = await self.create_visualization(
                    data_id=kwargs["data_id"],
                    chart_type=kwargs.get("chart_type", "bar"),
                    columns=kwargs.get("columns", []),
                    params=kwargs.get("params", {}),
                )
            elif action == "clean":
                result = await self.clean_data(
                    data_id=kwargs["data_id"],
                    operations=kwargs.get("operations", []),
                )
            elif action == "export":
                result = await self.export_data(
                    data_id=kwargs["data_id"],
                    format=kwargs.get("format", "csv"),
                )
            elif action == "correlation":
                result = await self.correlation_analysis(
                    data_id=kwargs["data_id"],
                    columns=kwargs.get("columns"),
                )
            elif action == "regression":
                result = await self.regression_analysis(
                    data_id=kwargs["data_id"],
                    dependent_var=kwargs["dependent_var"],
                    independent_vars=kwargs["independent_vars"],
                )
            elif action == "cluster":
                result = await self.cluster_analysis(
                    data_id=kwargs["data_id"],
                    columns=kwargs.get("columns", []),
                    n_clusters=kwargs.get("n_clusters", 3),
                )
            elif action == "test":
                result = await self.statistical_test(
                    data_id=kwargs["data_id"],
                    test_type=kwargs.get("test_type", "t_test"),
                    columns=kwargs.get("columns", []),
                    params=kwargs.get("params", {}),
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
            self._logger.exception(f"Error in DataAnalysisAgent: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                agent_name=self.name,
            )
    
    async def load_data(
        self,
        data: Union[str, Dict, List],
        data_id: str = "default",
        format: str = "csv",
    ) -> Dict[str, Any]:
        """
        加载数据
        
        Args:
            data: 数据（文件路径、字典或列表）
            data_id: 数据ID
            format: 数据格式
            
        Returns:
            Dict[str, Any]: 加载结果
        """
        self._logger.info(f"Loading data: {data_id}")
        
        try:
            if isinstance(data, str):
                # 从文件加载
                if format == "csv":
                    df = pd.read_csv(data)
                elif format == "json":
                    df = pd.read_json(data)
                elif format == "excel":
                    df = pd.read_excel(data)
                else:
                    raise ValueError(f"Unsupported format: {format}")
            elif isinstance(data, dict):
                # 从字典加载
                df = pd.DataFrame(data)
            elif isinstance(data, list):
                # 从列表加载
                df = pd.DataFrame(data)
            else:
                raise ValueError(f"Unsupported data type: {type(data)}")
            
            # 存储数据
            self._dataframes[data_id] = df
            
            return {
                "data_id": data_id,
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns),
                "message": f"数据加载成功，共{len(df)}行{len(df.columns)}列",
            }
            
        except Exception as e:
            raise ValueError(f"Failed to load data: {e}")
    
    async def profile_data(self, data_id: str) -> DataProfile:
        """
        数据概况分析
        
        Args:
            data_id: 数据ID
            
        Returns:
            DataProfile: 数据概况
        """
        self._logger.info(f"Profiling data: {data_id}")
        
        if data_id not in self._dataframes:
            raise ValueError(f"Data {data_id} not found")
        
        df = self._dataframes[data_id]
        
        # 基本信息
        rows, columns = df.shape
        column_names = list(df.columns)
        column_types = {col: str(df[col].dtype) for col in df.columns}
        
        # 缺失值
        missing_values = df.isnull().sum().to_dict()
        
        # 数值统计
        numeric_stats = {}
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            numeric_stats[col] = {
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "q25": float(df[col].quantile(0.25)),
                "q75": float(df[col].quantile(0.75)),
                "skewness": float(df[col].skew()),
                "kurtosis": float(df[col].kurtosis()),
            }
        
        # 分类统计
        categorical_stats = {}
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        for col in categorical_cols:
            value_counts = df[col].value_counts().head(10).to_dict()
            categorical_stats[col] = {
                "unique_count": int(df[col].nunique()),
                "top_values": value_counts,
                "mode": df[col].mode().iloc[0] if not df[col].mode().empty else None,
            }
        
        # 数据质量评分
        missing_ratio = df.isnull().sum().sum() / (rows * columns)
        data_quality_score = 1.0 - missing_ratio
        
        profile = DataProfile(
            rows=rows,
            columns=columns,
            column_names=column_names,
            column_types=column_types,
            missing_values=missing_values,
            numeric_stats=numeric_stats,
            categorical_stats=categorical_stats,
            data_quality_score=data_quality_score,
        )
        
        return profile
    
    async def analyze_data(
        self,
        data_id: str,
        analysis_type: str = "descriptive",
        columns: Optional[List[str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """
        数据分析
        
        Args:
            data_id: 数据ID
            analysis_type: 分析类型
            columns: 分析列
            params: 额外参数
            
        Returns:
            AnalysisResult: 分析结果
        """
        self._logger.info(f"Analyzing data {data_id}: {analysis_type}")
        
        if data_id not in self._dataframes:
            raise ValueError(f"Data {data_id} not found")
        
        df = self._dataframes[data_id]
        params = params or {}
        
        # 选择列
        if columns:
            df = df[columns]
        
        # 根据分析类型执行分析
        if analysis_type == "descriptive":
            result = await self._descriptive_analysis(df, params)
        elif analysis_type == "inferential":
            result = await self._inferential_analysis(df, params)
        elif analysis_type == "trend":
            result = await self._trend_analysis(df, params)
        elif analysis_type == "comparison":
            result = await self._comparison_analysis(df, params)
        elif analysis_type == "distribution":
            result = await self._distribution_analysis(df, params)
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")
        
        # 生成洞察
        insights = await self._generate_insights(result, analysis_type)
        
        # 生成建议
        recommendations = await self._generate_recommendations(result, insights)
        
        # 创建分析结果
        analysis_result = AnalysisResult(
            analysis_type=analysis_type,
            title=f"{analysis_type.capitalize()} Analysis",
            description=f"对数据{data_id}进行{analysis_type}分析",
            results=result,
            insights=insights,
            recommendations=recommendations,
        )
        
        # 保存到历史
        self._analysis_history.append(analysis_result)
        
        return analysis_result
    
    async def _descriptive_analysis(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        描述性统计分析
        
        Args:
            df: 数据框
            params: 参数
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        result = {}
        
        # 数值列统计
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            result["numeric_summary"] = df[numeric_cols].describe().to_dict()
            
            # 计算变异系数
            cv = {}
            for col in numeric_cols:
                mean = df[col].mean()
                if mean != 0:
                    cv[col] = float(df[col].std() / abs(mean))
            result["coefficient_of_variation"] = cv
        
        # 分类列统计
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        if len(categorical_cols) > 0:
            result["categorical_summary"] = {}
            for col in categorical_cols:
                result["categorical_summary"][col] = {
                    "unique_count": int(df[col].nunique()),
                    "top_values": df[col].value_counts().head(5).to_dict(),
                }
        
        return result
    
    async def _inferential_analysis(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        推断性统计分析
        
        Args:
            df: 数据框
            params: 参数
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        result = {}
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) >= 2:
            # 计算置信区间
            confidence_level = params.get("confidence_level", 0.95)
            result["confidence_intervals"] = {}
            
            for col in numeric_cols:
                data = df[col].dropna()
                if len(data) > 1:
                    mean = data.mean()
                    se = stats.sem(data)
                    ci = stats.t.interval(confidence_level, len(data)-1, loc=mean, scale=se)
                    result["confidence_intervals"][col] = {
                        "mean": float(mean),
                        "ci_lower": float(ci[0]),
                        "ci_upper": float(ci[1]),
                    }
        
        return result
    
    async def _trend_analysis(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        趋势分析
        
        Args:
            df: 数据框
            params: 参数
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        result = {}
        
        # 检查是否有时间列
        time_column = params.get("time_column")
        if time_column and time_column in df.columns:
            df[time_column] = pd.to_datetime(df[time_column])
            df = df.sort_values(time_column)
            
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            for col in numeric_cols:
                # 计算移动平均
                window = params.get("window", 3)
                df[f"{col}_ma"] = df[col].rolling(window=window).mean()
                
                # 计算趋势
                x = np.arange(len(df))
                y = df[col].values
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                
                result[col] = {
                    "trend_slope": float(slope),
                    "trend_intercept": float(intercept),
                    "r_squared": float(r_value**2),
                    "p_value": float(p_value),
                    "trend_direction": "increasing" if slope > 0 else "decreasing",
                }
        
        return result
    
    async def _comparison_analysis(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        比较分析
        
        Args:
            df: 数据框
            params: 参数
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        result = {}
        
        group_column = params.get("group_column")
        value_column = params.get("value_column")
        
        if group_column and value_column:
            if group_column in df.columns and value_column in df.columns:
                # 按组统计
                grouped = df.groupby(group_column)[value_column]
                result["group_statistics"] = {
                    "mean": grouped.mean().to_dict(),
                    "median": grouped.median().to_dict(),
                    "std": grouped.std().to_dict(),
                    "count": grouped.count().to_dict(),
                }
                
                # ANOVA检验
                groups = [group[value_column].dropna().values for name, group in df.groupby(group_column)]
                if len(groups) >= 2:
                    f_stat, p_value = stats.f_oneway(*groups)
                    result["anova_test"] = {
                        "f_statistic": float(f_stat),
                        "p_value": float(p_value),
                        "significant": p_value < 0.05,
                    }
        
        return result
    
    async def _distribution_analysis(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        分布分析
        
        Args:
            df: 数据框
            params: 参数
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        result = {}
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            data = df[col].dropna()
            
            if len(data) > 0:
                # 正态性检验
                if len(data) >= 8:
                    stat, p_value = stats.shapiro(data[:5000])  # Shapiro-Wilk限制5000样本
                    normality_test = {
                        "test": "Shapiro-Wilk",
                        "statistic": float(stat),
                        "p_value": float(p_value),
                        "is_normal": p_value > 0.05,
                    }
                else:
                    normality_test = None
                
                # 分位数
                quantiles = {
                    "q1": float(data.quantile(0.25)),
                    "q2": float(data.quantile(0.5)),
                    "q3": float(data.quantile(0.75)),
                    "iqr": float(data.quantile(0.75) - data.quantile(0.25)),
                }
                
                # 异常值检测
                q1 = data.quantile(0.25)
                q3 = data.quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                outliers = data[(data < lower_bound) | (data > upper_bound)]
                
                result[col] = {
                    "normality_test": normality_test,
                    "quantiles": quantiles,
                    "outliers_count": len(outliers),
                    "outliers_percentage": float(len(outliers) / len(data) * 100),
                }
        
        return result
    
    async def _generate_insights(self, results: Dict[str, Any], analysis_type: str) -> List[str]:
        """
        生成洞察
        
        Args:
            results: 分析结果
            analysis_type: 分析类型
            
        Returns:
            List[str]: 洞察列表
        """
        prompt = f"""
        基于以下{analysis_type}分析结果，生成3-5条关键洞察：
        
        {json.dumps(results, indent=2, ensure_ascii=False)}
        
        请用简洁的语言描述每条洞察，每条洞察一行。
        """
        
        response = await self.llm_service.generate(prompt)
        insights = [line.strip() for line in response.split('\n') if line.strip()]
        
        return insights
    
    async def _generate_recommendations(self, results: Dict[str, Any], insights: List[str]) -> List[str]:
        """
        生成建议
        
        Args:
            results: 分析结果
            insights: 洞察列表
            
        Returns:
            List[str]: 建议列表
        """
        prompt = f"""
        基于以下分析结果和洞察，生成3-5条行动建议：
        
        分析结果：
        {json.dumps(results, indent=2, ensure_ascii=False)}
        
        洞察：
        {chr(10).join(insights)}
        
        请用简洁的语言描述每条建议，每条建议一行。
        """
        
        response = await self.llm_service.generate(prompt)
        recommendations = [line.strip() for line in response.split('\n') if line.strip()]
        
        return recommendations
    
    async def correlation_analysis(
        self,
        data_id: str,
        columns: Optional[List[str]] = None,
    ) -> AnalysisResult:
        """
        相关性分析
        
        Args:
            data_id: 数据ID
            columns: 分析列
            
        Returns:
            AnalysisResult: 分析结果
        """
        self._logger.info(f"Correlation analysis for data: {data_id}")
        
        if data_id not in self._dataframes:
            raise ValueError(f"Data {data_id} not found")
        
        df = self._dataframes[data_id]
        
        # 选择数值列
        if columns:
            df = df[columns]
        else:
            df = df.select_dtypes(include=[np.number])
        
        # 计算相关系数
        correlation_matrix = df.corr()
        
        # 找出强相关
        strong_correlations = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                corr = correlation_matrix.iloc[i, j]
                if abs(corr) > 0.7:
                    strong_correlations.append({
                        "var1": correlation_matrix.columns[i],
                        "var2": correlation_matrix.columns[j],
                        "correlation": float(corr),
                        "strength": "strong" if abs(corr) > 0.8 else "moderate",
                    })
        
        results = {
            "correlation_matrix": correlation_matrix.to_dict(),
            "strong_correlations": strong_correlations,
        }
        
        # 生成洞察
        insights = await self._generate_insights(results, "correlation")
        
        analysis_result = AnalysisResult(
            analysis_type="correlation",
            title="相关性分析",
            description=f"对数据{data_id}进行相关性分析",
            results=results,
            insights=insights,
        )
        
        self._analysis_history.append(analysis_result)
        
        return analysis_result
    
    async def regression_analysis(
        self,
        data_id: str,
        dependent_var: str,
        independent_vars: List[str],
    ) -> AnalysisResult:
        """
        回归分析
        
        Args:
            data_id: 数据ID
            dependent_var: 因变量
            independent_vars: 自变量列表
            
        Returns:
            AnalysisResult: 分析结果
        """
        self._logger.info(f"Regression analysis for data: {data_id}")
        
        if data_id not in self._dataframes:
            raise ValueError(f"Data {data_id} not found")
        
        df = self._dataframes[data_id]
        
        # 准备数据
        X = df[independent_vars].values
        y = df[dependent_var].values
        
        # 添加常数项
        X = np.column_stack([np.ones(len(X)), X])
        
        # 最小二乘法
        from numpy.linalg import lstsq
        coefficients, residuals, rank, singular_values = lstsq(X, y, rcond=None)
        
        # 预测
        y_pred = X @ coefficients
        
        # 统计量
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot)
        
        n = len(y)
        p = len(independent_vars)
        adj_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - p - 1)
        
        # 标准误差
        mse = ss_res / (n - p - 1)
        se = np.sqrt(np.diag(mse * np.linalg.inv(X.T @ X)))
        
        # t统计量和p值
        t_stats = coefficients / se
        p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), n - p - 1))
        
        results = {
            "coefficients": {
                "intercept": float(coefficients[0]),
                **{var: float(coeff) for var, coeff in zip(independent_vars, coefficients[1:])}
            },
            "r_squared": float(r_squared),
            "adj_r_squared": float(adj_r_squared),
            "standard_errors": {
                "intercept": float(se[0]),
                **{var: float(se_val) for var, se_val in zip(independent_vars, se[1:])}
            },
            "t_statistics": {
                "intercept": float(t_stats[0]),
                **{var: float(t_stat) for var, t_stat in zip(independent_vars, t_stats[1:])}
            },
            "p_values": {
                "intercept": float(p_values[0]),
                **{var: float(p_val) for var, p_val in zip(independent_vars, p_values[1:])}
            },
            "f_statistic": float((ss_tot - ss_res) / p / (ss_res / (n - p - 1))),
            "significant_variables": [
                var for var, p_val in zip(independent_vars, p_values[1:]) if p_val < 0.05
            ],
        }
        
        # 生成洞察
        insights = await self._generate_insights(results, "regression")
        
        analysis_result = AnalysisResult(
            analysis_type="regression",
            title="回归分析",
            description=f"对数据{data_id}进行回归分析",
            results=results,
            insights=insights,
        )
        
        self._analysis_history.append(analysis_result)
        
        return analysis_result
    
    async def cluster_analysis(
        self,
        data_id: str,
        columns: List[str],
        n_clusters: int = 3,
    ) -> AnalysisResult:
        """
        聚类分析
        
        Args:
            data_id: 数据ID
            columns: 分析列
            n_clusters: 聚类数
            
        Returns:
            AnalysisResult: 分析结果
        """
        self._logger.info(f"Cluster analysis for data: {data_id}")
        
        if data_id not in self._dataframes:
            raise ValueError(f"Data {data_id} not found")
        
        df = self._dataframes[data_id]
        
        # 准备数据
        X = df[columns].values
        
        # 标准化
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # K-means聚类
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)
        
        # 聚类中心
        centers = scaler.inverse_transform(kmeans.cluster_centers_)
        
        # 聚类统计
        cluster_stats = {}
        for i in range(n_clusters):
            cluster_data = df[columns][clusters == i]
            cluster_stats[f"cluster_{i}"] = {
                "size": int(len(cluster_data)),
                "percentage": float(len(cluster_data) / len(df) * 100),
                "means": cluster_data.mean().to_dict(),
                "stds": cluster_data.std().to_dict(),
            }
        
        results = {
            "n_clusters": n_clusters,
            "cluster_centers": {f"cluster_{i}": center.tolist() for i, center in enumerate(centers)},
            "cluster_stats": cluster_stats,
            "inertia": float(kmeans.inertia_),
            "labels": clusters.tolist(),
        }
        
        # 生成洞察
        insights = await self._generate_insights(results, "cluster")
        
        analysis_result = AnalysisResult(
            analysis_type="cluster",
            title="聚类分析",
            description=f"对数据{data_id}进行{n_clusters}类聚类分析",
            results=results,
            insights=insights,
        )
        
        self._analysis_history.append(analysis_result)
        
        return analysis_result
    
    async def statistical_test(
        self,
        data_id: str,
        test_type: str,
        columns: List[str],
        params: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """
        统计检验
        
        Args:
            data_id: 数据ID
            test_type: 检验类型
            columns: 分析列
            params: 额外参数
            
        Returns:
            AnalysisResult: 分析结果
        """
        self._logger.info(f"Statistical test for data: {data_id}: {test_type}")
        
        if data_id not in self._dataframes:
            raise ValueError(f"Data {data_id} not found")
        
        df = self._dataframes[data_id]
        params = params or {}
        
        test_result = {}
        
        if test_type == "t_test":
            # t检验
            if len(columns) == 2:
                data1 = df[columns[0]].dropna()
                data2 = df[columns[1]].dropna()
                
                # 独立样本t检验
                t_stat, p_value = stats.ttest_ind(data1, data2)
                
                test_result = {
                    "test": "Independent t-test",
                    "variable1": columns[0],
                    "variable2": columns[1],
                    "mean1": float(data1.mean()),
                    "mean2": float(data2.mean()),
                    "t_statistic": float(t_stat),
                    "p_value": float(p_value),
                    "significant": p_value < 0.05,
                }
        
        elif test_type == "paired_t_test":
            # 配对t检验
            if len(columns) == 2:
                data1 = df[columns[0]].dropna()
                data2 = df[columns[1]].dropna()
                
                t_stat, p_value = stats.ttest_rel(data1, data2)
                
                test_result = {
                    "test": "Paired t-test",
                    "variable1": columns[0],
                    "variable2": columns[1],
                    "mean_diff": float(data1.mean() - data2.mean()),
                    "t_statistic": float(t_stat),
                    "p_value": float(p_value),
                    "significant": p_value < 0.05,
                }
        
        elif test_type == "chi_square":
            # 卡方检验
            if len(columns) == 2:
                contingency_table = pd.crosstab(df[columns[0]], df[columns[1]])
                chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)
                
                test_result = {
                    "test": "Chi-square test",
                    "variable1": columns[0],
                    "variable2": columns[1],
                    "chi2_statistic": float(chi2),
                    "p_value": float(p_value),
                    "degrees_of_freedom": int(dof),
                    "significant": p_value < 0.05,
                }
        
        elif test_type == "mann_whitney":
            # Mann-Whitney U检验
            if len(columns) == 2:
                data1 = df[columns[0]].dropna()
                data2 = df[columns[1]].dropna()
                
                u_stat, p_value = stats.mannwhitneyu(data1, data2)
                
                test_result = {
                    "test": "Mann-Whitney U test",
                    "variable1": columns[0],
                    "variable2": columns[1],
                    "u_statistic": float(u_stat),
                    "p_value": float(p_value),
                    "significant": p_value < 0.05,
                }
        
        else:
            raise ValueError(f"Unknown test type: {test_type}")
        
        # 生成洞察
        insights = await self._generate_insights(test_result, "statistical_test")
        
        analysis_result = AnalysisResult(
            analysis_type="statistical_test",
            title=f"{test_type} 检验",
            description=f"对数据{data_id}进行{test_type}检验",
            results=test_result,
            insights=insights,
            statistical_tests=[test_result],
        )
        
        self._analysis_history.append(analysis_result)
        
        return analysis_result
    
    async def create_visualization(
        self,
        data_id: str,
        chart_type: str,
        columns: List[str],
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        创建可视化
        
        Args:
            data_id: 数据ID
            chart_type: 图表类型
            columns: 列名
            params: 额外参数
            
        Returns:
            Dict[str, Any]: 可视化配置
        """
        self._logger.info(f"Creating visualization for data: {data_id}")
        
        if data_id not in self._dataframes:
            raise ValueError(f"Data {data_id} not found")
        
        df = self._dataframes[data_id]
        params = params or {}
        
        # 生成图表配置
        chart_config = {
            "type": chart_type,
            "data_id": data_id,
            "columns": columns,
            "params": params,
            "title": params.get("title", f"{chart_type.capitalize()} Chart"),
            "x_label": params.get("x_label", columns[0] if columns else ""),
            "y_label": params.get("y_label", columns[1] if len(columns) > 1 else ""),
        }
        
        # 根据图表类型生成具体配置
        if chart_type == "bar":
            chart_config["data"] = df[columns[0]].value_counts().to_dict()
        elif chart_type == "line":
            chart_config["data"] = {
                "x": df[columns[0]].tolist(),
                "y": df[columns[1]].tolist() if len(columns) > 1 else [],
            }
        elif chart_type == "scatter":
            chart_config["data"] = {
                "x": df[columns[0]].tolist(),
                "y": df[columns[1]].tolist() if len(columns) > 1 else [],
            }
        elif chart_type == "histogram":
            chart_config["data"] = df[columns[0]].tolist()
            chart_config["bins"] = params.get("bins", 20)
        elif chart_type == "box":
            chart_config["data"] = {col: df[col].tolist() for col in columns}
        elif chart_type == "heatmap":
            if len(columns) >= 2:
                chart_config["data"] = df[columns].corr().to_dict()
        
        return chart_config
    
    async def clean_data(
        self,
        data_id: str,
        operations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        数据清洗
        
        Args:
            data_id: 数据ID
            operations: 清洗操作列表
            
        Returns:
            Dict[str, Any]: 清洗结果
        """
        self._logger.info(f"Cleaning data: {data_id}")
        
        if data_id not in self._dataframes:
            raise ValueError(f"Data {data_id} not found")
        
        df = self._dataframes[data_id]
        original_shape = df.shape
        
        for operation in operations:
            op_type = operation.get("type")
            
            if op_type == "drop_missing":
                # 删除缺失值
                columns = operation.get("columns")
                how = operation.get("how", "any")
                df = df.dropna(subset=columns, how=how)
            
            elif op_type == "fill_missing":
                # 填充缺失值
                columns = operation.get("columns")
                method = operation.get("method", "mean")
                value = operation.get("value")
                
                for col in (columns or df.columns):
                    if col in df.columns:
                        if method == "mean":
                            df[col] = df[col].fillna(df[col].mean())
                        elif method == "median":
                            df[col] = df[col].fillna(df[col].median())
                        elif method == "mode":
                            df[col] = df[col].fillna(df[col].mode().iloc[0])
                        elif method == "value":
                            df[col] = df[col].fillna(value)
            
            elif op_type == "drop_duplicates":
                # 删除重复值
                columns = operation.get("columns")
                df = df.drop_duplicates(subset=columns)
            
            elif op_type == "rename_columns":
                # 重命名列
                mapping = operation.get("mapping", {})
                df = df.rename(columns=mapping)
            
            elif op_type == "drop_columns":
                # 删除列
                columns = operation.get("columns", [])
                df = df.drop(columns=columns, errors='ignore')
            
            elif op_type == "convert_type":
                # 转换类型
                columns = operation.get("columns", {})
                for col, dtype in columns.items():
                    if col in df.columns:
                        try:
                            df[col] = df[col].astype(dtype)
                        except:
                            pass
            
            elif op_type == "filter_rows":
                # 过滤行
                column = operation.get("column")
                operator = operation.get("operator")
                value = operation.get("value")
                
                if column and operator and value is not None:
                    if operator == "==":
                        df = df[df[column] == value]
                    elif operator == "!=":
                        df = df[df[column] != value]
                    elif operator == ">":
                        df = df[df[column] > value]
                    elif operator == "<":
                        df = df[df[column] < value]
                    elif operator == ">=":
                        df = df[df[column] >= value]
                    elif operator == "<=":
                        df = df[df[column] <= value]
        
        # 更新数据
        self._dataframes[data_id] = df
        
        return {
            "data_id": data_id,
            "original_shape": original_shape,
            "cleaned_shape": df.shape,
            "rows_removed": original_shape[0] - df.shape[0],
            "columns_removed": original_shape[1] - df.shape[1],
            "operations_applied": len(operations),
        }
    
    async def export_data(
        self,
        data_id: str,
        format: str = "csv",
    ) -> Dict[str, Any]:
        """
        导出数据
        
        Args:
            data_id: 数据ID
            format: 导出格式
            
        Returns:
            Dict[str, Any]: 导出结果
        """
        self._logger.info(f"Exporting data: {data_id}")
        
        if data_id not in self._dataframes:
            raise ValueError(f"Data {data_id} not found")
        
        df = self._dataframes[data_id]
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{data_id}_{timestamp}.{format}"
        
        # 导出数据
        if format == "csv":
            df.to_csv(filename, index=False)
        elif format == "json":
            df.to_json(filename, orient="records", force_ascii=False)
        elif format == "excel":
            df.to_excel(filename, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        return {
            "data_id": data_id,
            "filename": filename,
            "format": format,
            "rows": len(df),
            "columns": len(df.columns),
            "message": f"数据已导出到 {filename}",
        }
    
    def get_analysis_history(self) -> List[Dict[str, Any]]:
        """
        获取分析历史
        
        Returns:
            List[Dict[str, Any]]: 分析历史
        """
        history = []
        for result in self._analysis_history:
            history.append({
                "analysis_type": result.analysis_type,
                "title": result.title,
                "description": result.description,
                "insights_count": len(result.insights),
                "recommendations_count": len(result.recommendations),
            })
        
        return history
    
    def clear_analysis_history(self) -> None:
        """清空分析历史"""
        self._analysis_history.clear()
        self._logger.info("Analysis history cleared")
    
    def get_data_ids(self) -> List[str]:
        """
        获取所有数据ID
        
        Returns:
            List[str]: 数据ID列表
        """
        return list(self._dataframes.keys())
    
    def remove_data(self, data_id: str) -> bool:
        """
        删除数据
        
        Args:
            data_id: 数据ID
            
        Returns:
            bool: 是否成功删除
        """
        if data_id in self._dataframes:
            del self._dataframes[data_id]
            self._logger.info(f"Data {data_id} removed")
            return True
        return False
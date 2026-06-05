"""
系统配置模块

包含所有系统配置项，支持环境变量和配置文件。
"""

import os
from typing import Optional, Dict, Any, List
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class LLMConfig(BaseSettings):
    """LLM配置"""
    # OpenAI配置
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4-turbo-preview", env="OPENAI_MODEL")
    openai_temperature: float = Field(0.7, env="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(4096, env="OPENAI_MAX_TOKENS")
    
    # Anthropic配置
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field("claude-3-opus-20240229", env="ANTHROPIC_MODEL")
    
    # 本地模型配置
    local_model_path: Optional[str] = Field(None, env="LOCAL_MODEL_PATH")
    local_model_device: str = Field("cuda", env="LOCAL_MODEL_DEVICE")
    
    class Config:
        env_prefix = "LLM_"


class DatabaseConfig(BaseSettings):
    """数据库配置"""
    host: str = Field("localhost", env="DB_HOST")
    port: int = Field(5432, env="DB_PORT")
    user: str = Field("postgres", env="DB_USER")
    password: str = Field("postgres", env="DB_PASSWORD")
    database: str = Field("research_agent", env="DB_NAME")
    pool_size: int = Field(20, env="DB_POOL_SIZE")
    max_overflow: int = Field(10, env="DB_MAX_OVERFLOW")
    
    @property
    def url(self) -> str:
        """获取数据库连接URL"""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    class Config:
        env_prefix = "DB_"


class RedisConfig(BaseSettings):
    """Redis配置"""
    host: str = Field("localhost", env="REDIS_HOST")
    port: int = Field(6379, env="REDIS_PORT")
    password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    db: int = Field(0, env="REDIS_DB")
    pool_size: int = Field(10, env="REDIS_POOL_SIZE")
    
    @property
    def url(self) -> str:
        """获取Redis连接URL"""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"
    
    class Config:
        env_prefix = "REDIS_"


class StorageConfig(BaseSettings):
    """存储配置"""
    # MinIO配置
    minio_endpoint: str = Field("localhost:9000", env="MINIO_ENDPOINT")
    minio_access_key: str = Field("minioadmin", env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field("minioadmin", env="MINIO_SECRET_KEY")
    minio_secure: bool = Field(False, env="MINIO_SECURE")
    minio_bucket: str = Field("research-agent", env="MINIO_BUCKET")
    
    # 本地存储配置
    local_storage_path: str = Field("./storage", env="LOCAL_STORAGE_PATH")
    
    class Config:
        env_prefix = "STORAGE_"


class CeleryConfig(BaseSettings):
    """Celery配置"""
    broker_url: str = Field("redis://localhost:6379/1", env="CELERY_BROKER_URL")
    result_backend: str = Field("redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    task_serializer: str = Field("json", env="CELERY_TASK_SERIALIZER")
    result_serializer: str = Field("json", env="CELERY_RESULT_SERIALIZER")
    accept_content: List[str] = Field(["json"], env="CELERY_ACCEPT_CONTENT")
    timezone: str = Field("Asia/Shanghai", env="CELERY_TIMEZONE")
    enable_utc: bool = Field(True, env="CELERY_ENABLE_UTC")
    
    class Config:
        env_prefix = "CELERY_"


class AgentConfig(BaseSettings):
    """Agent配置"""
    # 通用配置
    max_retries: int = Field(3, env="AGENT_MAX_RETRIES")
    timeout: int = Field(300, env="AGENT_TIMEOUT")  # 秒
    debug: bool = Field(False, env="AGENT_DEBUG")
    
    # 文献调研Agent配置
    literature_search_limit: int = Field(50, env="LITERATURE_SEARCH_LIMIT")
    literature_analysis_depth: str = Field("detailed", env="LITERATURE_ANALYSIS_DEPTH")
    
    # 研究设计Agent配置
    research_methodology: str = Field("mixed", env="RESEARCH_METHODOLOGY")
    
    # 代码Agent配置
    code_language: str = Field("python", env="CODE_LANGUAGE")
    code_style: str = Field("google", env="CODE_STYLE")
    
    # 数据分析Agent配置
    analysis_significance_level: float = Field(0.05, env="ANALYSIS_SIGNIFICANCE_LEVEL")
    
    # 写作Agent配置
    writing_style: str = Field("academic", env="WRITING_STYLE")
    citation_style: str = Field("apa", env="CITATION_STYLE")
    
    class Config:
        env_prefix = "AGENT_"


class Settings(BaseSettings):
    """主配置类"""
    # 应用配置
    app_name: str = Field("Research Agent", env="APP_NAME")
    app_version: str = Field("0.1.0", env="APP_VERSION")
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # 服务器配置
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    workers: int = Field(4, env="WORKERS")
    
    # 安全配置
    secret_key: str = Field("your-secret-key-here", env="SECRET_KEY")
    api_key_header: str = Field("X-API-Key", env="API_KEY_HEADER")
    cors_origins: List[str] = Field(["*"], env="CORS_ORIGINS")
    
    # 子配置
    llm: LLMConfig = Field(default_factory=LLMConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    celery: CeleryConfig = Field(default_factory=CeleryConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 导出配置实例
settings = get_settings()
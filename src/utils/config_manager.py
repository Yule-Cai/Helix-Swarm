"""
配置管理模块
支持 YAML 配置文件的加载、验证、合并和热重载
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

import yaml


class ConfigValidationError(Exception):
    """配置验证错误异常"""
    pass


class ConfigManager:
    """配置管理器"""
    
    # 必填字段及其类型
    REQUIRED_FIELDS = {
        "research_domain": str,
        "experiment_timeout": int,
        "output_format": str
    }
    
    # 有效输出格式
    VALID_OUTPUT_FORMATS = ["latex", "pdf", "docx"]
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path: Optional[str] = config_path
        self._config: Optional[Dict[str, Any]] = None
        self._last_modified_time: Optional[float] = None
    
    def load(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        从 YAML 文件加载配置
        
        Args:
            config_path: 配置文件路径，如果为 None 则使用初始化时的路径
            
        Returns:
            配置字典
            
        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML 解析错误
            ValueError: 配置为空
        """
        path = config_path or self.config_path
        
        if not path:
            raise ValueError("No config path specified")
        
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(path_obj, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if not config:
            raise ValueError("Config file is empty or invalid")
        
        self.config_path = path
        self._config = config
        self._last_modified_time = path_obj.stat().st_mtime
        
        return config
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """
        验证配置
        
        Args:
            config: 配置字典
            
        Returns:
            True 如果验证通过
            
        Raises:
            ConfigValidationError: 配置验证失败
        """
        # 检查必填字段
        for field, field_type in self.REQUIRED_FIELDS.items():
            if field not in config:
                raise ConfigValidationError(f"Missing required field: {field}")
            
            if not isinstance(config[field], field_type):
                raise ConfigValidationError(
                    f"Field '{field}' must be of type {field_type.__name__}, "
                    f"got {type(config[field]).__name__}"
                )
        
        # 验证输出格式
        output_format = config.get("output_format")
        if output_format not in self.VALID_OUTPUT_FORMATS:
            raise ConfigValidationError(
                f"Invalid output_format: {output_format}. "
                f"Must be one of: {self.VALID_OUTPUT_FORMATS}"
            )
        
        return True
    
    def merge(self, default_config: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并默认配置和用户配置（用户配置优先）
        
        Args:
            default_config: 默认配置
            user_config: 用户配置
            
        Returns:
            合并后的配置
        """
        merged = default_config.copy()
        merged.update(user_config)
        return merged
    
    def reload(self) -> Dict[str, Any]:
        """
        热重载配置（重新加载配置文件）
        
        Returns:
            重新加载后的配置
            
        Raises:
            ValueError: 没有指定配置文件路径
        """
        if not self.config_path:
            raise ValueError("No config path specified for reload")
        
        return self.load(self.config_path)
    
    def has_changed(self) -> bool:
        """
        检查配置文件是否已更改
        
        Returns:
            True 如果配置文件已更改
        """
        if not self.config_path:
            return False
        
        path_obj = Path(self.config_path)
        if not path_obj.exists():
            return False
        
        current_mtime = path_obj.stat().st_mtime
        return current_mtime != self._last_modified_time
    
    def __repr__(self) -> str:
        return f"ConfigManager(config_path={self.config_path})"

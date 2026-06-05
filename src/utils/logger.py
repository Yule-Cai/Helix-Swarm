"""
日志管理模块

提供结构化的日志功能，支持：
- 多级别日志（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- 文件和控制台输出
- 日志轮转（RotatingFileHandler）
- 自定义日志格式
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    设置并返回一个配置好的 logger
    
    Args:
        name: Logger 名称
        level: 日志级别（默认 INFO）
        log_file: 日志文件路径（可选）
        format_string: 自定义格式字符串（可选）
        max_bytes: 轮转文件最大字节数（默认 10MB）
        backup_count: 备份文件数量（默认 5）
    
    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # 默认格式
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(format_string)
    
    # 控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件 handler（如果指定了日志文件）
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取已存在的 logger，如果不存在则创建一个新的
    
    Args:
        name: Logger 名称
    
    Returns:
        Logger 实例
    """
    logger = logging.getLogger(name)
    
    # 如果 logger 没有 handler，调用 setup_logger 进行基本配置
    if not logger.handlers:
        return setup_logger(name)
    
    return logger


def close_logger(logger: logging.Logger) -> None:
    """
    关闭 logger 的所有 handlers，释放文件资源
    
    Args:
        logger: 要关闭的 Logger 实例
    """
    for handler in logger.handlers[:]:  # 使用切片创建副本以避免修改时出错
        handler.close()
        logger.removeHandler(handler)

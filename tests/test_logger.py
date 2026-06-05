"""
测试日志管理模块
"""
import pytest
import logging
import tempfile
import os
from src.utils.logger import setup_logger, get_logger


class TestSetupLogger:
    """测试 setup_logger 函数"""
    
    def test_setup_logger_creates_logger(self):
        """测试创建 logger 实例"""
        logger = setup_logger("test_logger")
        assert logger is not None
        assert isinstance(logger, logging.Logger)
    
    def test_logger_name(self):
        """测试 logger 名称设置"""
        logger = setup_logger("my_custom_logger")
        assert logger.name == "my_custom_logger"
    
    def test_logger_levels(self):
        """测试日志级别设置"""
        logger = setup_logger("test_levels", level=logging.DEBUG)
        assert logger.level == logging.DEBUG
        
        logger_info = setup_logger("test_info", level=logging.INFO)
        assert logger_info.level == logging.INFO
    
    def test_file_logging(self):
        """测试文件日志输出"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name
        
        logger = None
        try:
            logger = setup_logger("test_file", log_file=log_file)
            logger.info("Test message")
            
            # 关闭所有 handlers 以确保文件写入磁盘
            for handler in logger.handlers:
                handler.close()
                logger.removeHandler(handler)
            
            with open(log_file, 'r') as f:
                content = f.read()
                assert "Test message" in content
        finally:
            # 清理
            logging.shutdown()
            if os.path.exists(log_file):
                try:
                    os.unlink(log_file)
                except:
                    pass
    
    def test_console_output(self):
        """测试控制台输出（通过检查 handler 类型）"""
        logger = setup_logger("test_console")
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "StreamHandler" in handler_types or "FileHandler" in handler_types
    
    def test_logger_format(self):
        """测试日志格式"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name
        
        logger = None
        try:
            logger = setup_logger("test_format", log_file=log_file, level=logging.DEBUG)
            logger.info("Formatted message")
            
            # 关闭所有 handlers
            for handler in logger.handlers:
                handler.close()
                logger.removeHandler(handler)
            
            with open(log_file, 'r') as f:
                content = f.read()
                # 检查是否包含时间、级别、消息等格式元素
                assert "INFO" in content
                assert "Formatted message" in content
        finally:
            logging.shutdown()
            if os.path.exists(log_file):
                try:
                    os.unlink(log_file)
                except:
                    pass


class TestGetLogger:
    """测试 get_logger 函数"""
    
    def test_get_existing_logger(self):
        """测试获取已存在的 logger"""
        # 先创建一个 logger
        setup_logger("existing_logger")
        # 然后通过 get_logger 获取
        logger = get_logger("existing_logger")
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "existing_logger"
    
    def test_get_nonexistent_logger(self):
        """测试获取不存在的 logger（应该创建新的）"""
        logger = get_logger("new_logger_" + str(id(object)))
        assert logger is not None
        assert isinstance(logger, logging.Logger)


class TestLogFileRotation:
    """测试日志文件轮转"""
    
    def test_rotating_file_handler(self):
        """测试 RotatingFileHandler 配置"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name
        
        logger = None
        try:
            logger = setup_logger(
                "test_rotation", 
                log_file=log_file,
                max_bytes=1024,  # 1KB
                backup_count=3
            )
            # 检查是否有 RotatingFileHandler
            handler_types = [type(h).__name__ for h in logger.handlers]
            assert "RotatingFileHandler" in handler_types
        finally:
            logging.shutdown()
            if os.path.exists(log_file):
                try:
                    os.unlink(log_file)
                except:
                    pass
            # 清理备份文件
            for i in range(1, 4):
                backup = log_file + f".{i}"
                if os.path.exists(backup):
                    try:
                        os.unlink(backup)
                    except:
                        pass


class TestLoggerIntegration:
    """集成测试"""
    
    def test_multiple_loggers_independence(self):
        """测试多个 logger 之间相互独立"""
        logger1 = setup_logger("logger1", level=logging.DEBUG)
        logger2 = setup_logger("logger2", level=logging.INFO)
        
        assert logger1.level == logging.DEBUG
        assert logger2.level == logging.INFO
        assert logger1.name != logger2.name
    
    def test_logger_with_subdirectory(self, tmp_path):
        """测试日志文件在子目录中创建"""
        # 使用 pytest 的 tmp_path fixture，它会自动清理
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        log_file = str(subdir / "test.log")
        
        logger = setup_logger("test_subdir", log_file=log_file)
        logger.info("Message in subdirectory")
        
        # 验证文件已创建
        assert os.path.exists(log_file)
        
        # 清理
        logging.shutdown()

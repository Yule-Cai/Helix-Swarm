"""测试配置管理模块"""
import os
import tempfile
import pytest
import yaml
from src.utils.config_manager import ConfigManager, ConfigValidationError


class TestConfigManager:
    """配置管理器测试类"""
    
    def test_load_yaml_config(self):
        """测试从 YAML 文件加载配置"""
        config_mgr = ConfigManager()
        config = config_mgr.load("config/default_config.yaml")
        
        assert config is not None
        assert isinstance(config, dict)
        assert "research_domain" in config
        assert config["research_domain"] == "AI/ML"
    
    def test_config_validation_missing_required_field(self):
        """测试配置验证 - 缺少必填字段"""
        config_mgr = ConfigManager()
        
        # 缺少必填字段的配置
        invalid_config = {
            "output_format": "latex"
            # 缺少 research_domain, experiment_timeout 等必填字段
        }
        
        with pytest.raises(ConfigValidationError):
            config_mgr.validate(invalid_config)
    
    def test_config_validation_valid_config(self):
        """测试配置验证 - 有效配置"""
        config_mgr = ConfigManager()
        
        valid_config = {
            "research_domain": "AI/ML",
            "experiment_timeout": 300,
            "output_format": "latex",
            "max_ideas": 5
        }
        
        # 不应该抛出异常
        result = config_mgr.validate(valid_config)
        assert result is True
    
    def test_config_merge_default_and_user(self):
        """测试配置合并 - 默认配置 + 用户配置"""
        config_mgr = ConfigManager()
        
        default_config = {
            "research_domain": "AI/ML",
            "experiment_timeout": 300,
            "output_format": "latex",
            "max_ideas": 5
        }
        
        user_config = {
            "output_format": "pdf",  # 覆盖默认值
            "max_ideas": 10         # 覆盖默认值
        }
        
        merged = config_mgr.merge(default_config, user_config)
        
        assert merged["research_domain"] == "AI/ML"  # 保持默认值
        assert merged["experiment_timeout"] == 300    # 保持默认值
        assert merged["output_format"] == "pdf"       # 被用户配置覆盖
        assert merged["max_ideas"] == 10             # 被用户配置覆盖
    
    def test_config_hot_reload(self):
        """测试配置热重载"""
        config_mgr = ConfigManager()
        
        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"research_domain": "AI/ML", "version": 1}, f)
            temp_config_path = f.name
        
        try:
            # 首次加载
            config1 = config_mgr.load(temp_config_path)
            assert config1["version"] == 1
            
            # 修改文件
            with open(temp_config_path, 'w') as f:
                yaml.dump({"research_domain": "AI/ML", "version": 2}, f)
            
            # 热重载
            config2 = config_mgr.reload()
            assert config2["version"] == 2
        finally:
            os.unlink(temp_config_path)
    
    def test_load_nonexistent_file(self):
        """测试加载不存在的配置文件"""
        config_mgr = ConfigManager()
        
        with pytest.raises(FileNotFoundError):
            config_mgr.load("nonexistent_config.yaml")
    
    def test_output_format_validation(self):
        """测试输出格式验证"""
        config_mgr = ConfigManager()
        
        config = {
            "research_domain": "AI/ML",
            "experiment_timeout": 300,
            "output_format": "invalid_format"  # 无效格式
        }
        
        with pytest.raises(ConfigValidationError):
            config_mgr.validate(config)
    
    def test_experiment_timeout_type_validation(self):
        """测试实验超时时间类型验证"""
        config_mgr = ConfigManager()
        
        config = {
            "research_domain": "AI/ML",
            "experiment_timeout": "not_a_number",  # 应该是整数
            "output_format": "latex"
        }
        
        with pytest.raises(ConfigValidationError):
            config_mgr.validate(config)

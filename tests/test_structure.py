import os
import pytest

def test_directory_structure_exists():
    """测试项目基础目录结构是否存在"""
    required_dirs = ['src', 'tests', 'templates', 'config', 'skills']
    for dir_name in required_dirs:
        assert os.path.isdir(dir_name), f"目录 {dir_name} 不存在"

def test_src_subdirectories():
    """测试 src 下的子目录结构"""
    required_subdirs = [
        'src/idea_generation',
        'src/experiment_execution',
        'src/paper_writing',
        'src/utils'
    ]
    for subdir in required_subdirs:
        assert os.path.isdir(subdir), f"子目录 {subdir} 不存在"

def test_templates_exist():
    """测试模板文件是否存在"""
    required_templates = [
        'templates/paper_latex_template.tex',
        'templates/experiment_config.yaml'
    ]
    for template in required_templates:
        assert os.path.isfile(template), f"模板文件 {template} 不存在"

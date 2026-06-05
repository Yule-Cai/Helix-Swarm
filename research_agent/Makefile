.PHONY: help install install-dev test test-cov lint format type-check clean build publish

# 默认目标
help:
	@echo "可用命令:"
	@echo "  install      - 安装生产依赖"
	@echo "  install-dev  - 安装开发依赖"
	@echo "  test         - 运行测试"
	@echo "  test-cov     - 运行测试并生成覆盖率报告"
	@echo "  lint         - 运行代码检查"
	@echo "  format       - 格式化代码"
	@echo "  type-check   - 运行类型检查"
	@echo "  clean        - 清理构建文件"
	@echo "  build        - 构建项目"
	@echo "  publish      - 发布到PyPI"

# 安装生产依赖
install:
	pip install -e .

# 安装开发依赖
install-dev:
	pip install -e ".[dev]"
	pip install -e ".[docs]"

# 运行测试
test:
	pytest

# 运行测试并生成覆盖率报告
test-cov:
	pytest --cov=research_agent --cov-report=html --cov-report=term-missing

# 运行代码检查
lint:
	flake8 research_agent/
	black --check research_agent/
	isort --check-only research_agent/

# 格式化代码
format:
	black research_agent/
	isort research_agent/

# 运行类型检查
type-check:
	mypy research_agent/

# 清理构建文件
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

# 构建项目
build: clean
	python -m build

# 发布到PyPI
publish: build
	twine upload dist/*

# 运行应用
run:
	python -m research_agent interactive

# 运行搜索示例
search:
	python -m research_agent search "机器学习"

# 运行分析示例
analyze:
	python -m research_agent analyze paper.pdf

# 运行规划示例
plan:
	python -m research_agent plan "深度学习研究"

# 生成文档
docs:
	cd docs && make html

# 预览文档
docs-preview:
	cd docs && make html && open _build/html/index.html

# 检查依赖
check-deps:
	pip check

# 更新依赖
update-deps:
	pip install --upgrade pip
	pip install --upgrade -r requirements.txt

# 创建虚拟环境
venv:
	python -m venv venv
	@echo "激活虚拟环境:"
	@echo "  Linux/Mac: source venv/bin/activate"
	@echo "  Windows:   venv\\Scripts\\activate"

# 安装pre-commit钩子
pre-commit:
	pre-commit install

# 运行pre-commit
pre-commit-run:
	pre-commit run --all-files

# 生成requirements.txt
freeze:
	pip freeze > requirements.txt

# 检查代码质量
quality: lint type-check test

# 完整检查
full: quality build
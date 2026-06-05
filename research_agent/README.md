# 研究智能体 (Research Agent)

一个基于大语言模型的学术研究助手，帮助研究人员进行文献搜索、论文分析、研究规划等任务。

## 功能特性

### 核心功能

- **文献搜索**: 从多个学术数据库搜索相关文献
- **论文分析**: 自动分析论文内容，提取关键信息
- **研究规划**: 制定研究计划和时间表
- **知识管理**: 管理和组织研究知识

### 高级功能

- **工作流自动化**: 自动化研究流程
- **记忆系统**: 长期和短期记忆管理
- **多数据源集成**: 集成多个学术数据库
- **智能推荐**: 基于研究兴趣推荐相关文献

## 项目结构

```
research_agent/
├── core/                    # 核心模块
│   ├── __init__.py
│   ├── agent.py            # 研究智能体
│   ├── tasks.py            # 任务管理
│   ├── memory.py           # 记忆系统
│   └── workflows.py        # 工作流引擎
├── services/                # 服务模块
│   ├── __init__.py
│   ├── llm_service.py      # LLM服务
│   ├── search_service.py   # 搜索服务
│   └── storage_service.py  # 存储服务
├── tests/                   # 测试模块
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_tasks.py
│   ├── test_memory.py
│   ├── test_workflows.py
│   └── test_services.py
├── config.py                # 配置管理
├── main.py                  # 主入口
├── requirements.txt         # 依赖列表
└── README.md                # 项目说明
```

## 安装

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/research-agent.git
cd research-agent
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

创建 `.env` 文件：

```env
# LLM配置
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# 搜索配置
SEARCH_MAX_RESULTS=100
SEARCH_TIMEOUT=30

# 存储配置
STORAGE_DIR=data
LOG_LEVEL=INFO
```

## 使用方法

### 命令行界面

```bash
# 搜索文献
python -m research_agent search "机器学习"

# 分析论文
python -m research_agent analyze paper.pdf

# 制定研究计划
python -m research_agent plan "深度学习研究"

# 交互式界面
python -m research_agent interactive

# 查看状态
python -m research_agent status
```

### Python API

```python
from research_agent.core import ResearchAgent

# 创建智能体
agent = ResearchAgent()

# 搜索文献
results = await agent.search("机器学习")

# 分析论文
analysis = await agent.analyze("paper.pdf")

# 制定研究计划
plan = await agent.plan("深度学习研究")
```

### 交互式界面

启动交互式界面后，可以使用以下命令：

- `search <查询>` - 搜索学术文献
- `analyze <文件>` - 分析论文
- `plan <主题>` - 制定研究计划
- `status` - 查看系统状态
- `help` - 显示帮助
- `quit` - 退出

## 配置说明

### LLM配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `LLM_API_KEY` | API密钥 | - |
| `LLM_BASE_URL` | API基础URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | 模型名称 | `gpt-3.5-turbo` |
| `LLM_MAX_RETRIES` | 最大重试次数 | `3` |
| `LLM_TIMEOUT` | 超时时间(秒) | `60` |

### 搜索配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `SEARCH_SOURCES` | 数据源列表 | `semantic_scholar,arxiv,pubmed` |
| `SEARCH_MAX_RESULTS` | 最大结果数 | `100` |
| `SEARCH_TIMEOUT` | 超时时间(秒) | `30` |

### 存储配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `STORAGE_DIR` | 存储目录 | `data` |
| `STORAGE_AUTO_SAVE` | 自动保存 | `true` |
| `STORAGE_BACKUP_ENABLED` | 启用备份 | `true` |

## 开发

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_agent.py

# 运行带覆盖率的测试
pytest --cov=research_agent
```

### 代码格式化

```bash
# 使用black格式化
black research_agent/

# 使用isort排序导入
isort research_agent/
```

### 类型检查

```bash
# 使用mypy检查类型
mypy research_agent/
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 致谢

- [OpenAI](https://openai.com/) - 提供LLM API
- [Semantic Scholar](https://www.semanticscholar.org/) - 学术搜索API
- [arXiv](https://arxiv.org/) - 预印本数据库
- [PubMed](https://pubmed.ncbi.nlm.nih.gov/) - 生物医学文献数据库

## 联系方式

- 项目链接: https://github.com/yourusername/research-agent
- 问题反馈: https://github.com/yourusername/research-agent/issues

## 更新日志

### v1.0.0 (2024-01-01)

- 初始版本发布
- 实现核心功能
- 添加命令行界面
- 集成多个学术数据库
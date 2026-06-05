"""
研究智能体安装配置
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# 读取依赖
requirements = []
with open("requirements.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#"):
            requirements.append(line)

setup(
    name="research-agent",
    version="1.0.0",
    author="Research Agent Team",
    author_email="research@example.com",
    description="一个基于大语言模型的学术研究助手",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/research-agent",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/research-agent/issues",
        "Documentation": "https://github.com/yourusername/research-agent/wiki",
        "Source Code": "https://github.com/yourusername/research-agent",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "isort>=5.12.0",
            "mypy>=1.5.0",
            "flake8>=6.1.0",
        ],
        "docs": [
            "sphinx>=7.1.0",
            "sphinx-rtd-theme>=1.3.0",
            "myst-parser>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "research-agent=research_agent.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "research_agent": [
            "*.json",
            "*.yaml",
            "*.yml",
            "*.txt",
            "*.md",
        ],
    },
    zip_safe=False,
    keywords=[
        "research",
        "agent",
        "ai",
        "llm",
        "academic",
        "paper",
        "analysis",
        "search",
    ],
)
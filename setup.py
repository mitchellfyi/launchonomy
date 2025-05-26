#!/usr/bin/env python3
"""
Setup script for Launchonomy - Autonomous AI Business Orchestration System
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Autonomous AI Business Orchestration System"

# Read requirements from requirements.txt
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    requirements = []
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    requirements.append(line)
    return requirements

setup(
    name="launchonomy",
    version="0.1.0",
    author="Mitchell",
    author_email="hello@mitchell.fyi",
    description="Autonomous AI Business Orchestration System",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/mitchellfyi/launchonomy",
    project_urls={
        "Bug Tracker": "https://github.com/mitchellfyi/launchonomy/issues",
        "Documentation": "https://github.com/mitchellfyi/launchonomy/tree/main/docs",
        "Source Code": "https://github.com/mitchellfyi/launchonomy",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "launchonomy=launchonomy.cli:main",
            "launchonomy-cli=launchonomy.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "launchonomy": [
            "registry/*.json",
            "templates/*.txt",
            "templates/*.json",
        ],
    },
    zip_safe=False,
    keywords=[
        "ai",
        "agents",
        "autogen",
        "business",
        "automation",
        "orchestration",
        "machine-learning",
        "artificial-intelligence",
        "multi-agent",
        "workflow",
    ],
) 
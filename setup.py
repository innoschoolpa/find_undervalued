"""
리팩토링된 분석 시스템 설치 스크립트

모듈별 독립 배포를 위한 패키지 설정
"""

from setuptools import setup, find_packages
import os

# README 파일 읽기
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "리팩토링된 분석 시스템"

# requirements.txt 읽기
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements_optimized.txt')
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # 주석과 빈 줄 제거
            return [line.strip() for line in lines 
                   if line.strip() and not line.strip().startswith('#')]
    return []

setup(
    name="enhanced-analyzer-system",
    version="2.0.0",
    author="Enhanced Analyzer Team",
    author_email="team@enhanced-analyzer.com",
    description="리팩토링된 고성능 주식 분석 시스템",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/enhanced-analyzer/enhanced-analyzer-system",
    packages=find_packages(exclude=['tests*', 'docs*']),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.2.0",
            "pytest-cov>=2.12.0",
            "pytest-mock>=3.6.0",
            "black>=21.0.0",
            "flake8>=3.9.0",
            "mypy>=0.910",
        ],
        "docs": [
            "sphinx>=4.0.0",
            "sphinx-rtd-theme>=0.5.0",
        ],
        "performance": [
            "numba>=0.53.0",
            "cython>=0.29.0",
        ],
        "visualization": [
            "matplotlib>=3.3.0",
            "plotly>=5.0.0",
        ],
        "database": [
            "sqlalchemy>=1.4.0",
        ],
        "caching": [
            "redis>=3.5.0",
            "memcached>=1.59.0",
        ],
        "parallel": [
            "joblib>=1.0.0",
            "dask>=2021.5.0",
        ],
        "ml": [
            "xgboost>=1.5.0",
            "lightgbm>=3.2.0",
        ],
        "web": [
            "fastapi>=0.68.0",
            "uvicorn>=0.15.0",
        ],
        "monitoring": [
            "prometheus-client>=0.11.0",
            "grafana-api>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "enhanced-analyzer=enhanced_integrated_analyzer_refactored:main",
            "analyzer-cli=cli:main",
        ],
    },
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.csv", "*.txt"],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="stock analysis, value investing, financial analysis, portfolio management",
    project_urls={
        "Bug Reports": "https://github.com/enhanced-analyzer/enhanced-analyzer-system/issues",
        "Source": "https://github.com/enhanced-analyzer/enhanced-analyzer-system",
        "Documentation": "https://enhanced-analyzer-system.readthedocs.io/",
    },
)














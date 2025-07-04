"""Setup script for DAS Trader Python API client."""

from setuptools import setup, find_packages

setup(
    name="das-trader-client",
    version="1.0.0",
    author="DAS Bridge Contributors",
    author_email="noreply@example.com",
    description="Professional Python client for DAS Trader Pro CMD API",
    long_description="Professional Python client for DAS Trader Pro CMD API that enables automated trading, order management, position tracking, and real-time market data streaming. Features comprehensive order types, short locate integration, Level 1/2 market data, and multi-platform notifications.",
    long_description_content_type="text/plain",
    url="https://github.com/jefrnc/das-bridge",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        # Core requirements only (no optional deps)
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
            "isort>=5.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
        "analysis": [
            "numpy>=1.21.0",
            "pandas>=1.3.0",
            "matplotlib>=3.5.0",
            "plotly>=5.0.0",
        ],
        "monitoring": [
            "structlog>=22.0.0",
            "prometheus-client>=0.14.0",
        ],
        "full": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "numpy>=1.21.0",
            "pandas>=1.3.0",
            "structlog>=22.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "das-trader=das_trader.cli:main",
        ],
    },
    keywords="trading, finance, api, das-trader, stocks, automated-trading",
    project_urls={
        "Bug Reports": "https://github.com/jefrnc/das-bridge/issues",
        "Source": "https://github.com/jefrnc/das-bridge",
        "Documentation": "https://github.com/jefrnc/das-bridge/wiki",
    },
)
"""Setup script for NexusEnrichmentAgent."""

from setuptools import setup, find_packages

setup(
    name="NexusEnrichmentAgent",
    version="1.0",
    packages=find_packages(where="src", exclude=("test",)),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "strands-agents",
        "boto3",
        "pydantic>=2.0",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
            "black",
            "isort",
            "mypy",
            "flake8",
        ],
    },
    author="Nexus Team",
    description="Multi-agent enrichment system for compliance control mapping",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)

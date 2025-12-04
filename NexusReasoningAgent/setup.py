"""Setup script for NexusReasoningAgent."""

from setuptools import setup, find_packages

setup(
    name="NexusReasoningAgent",
    version="1.0",
    packages=find_packages(where="src", exclude=("test",)),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "boto3",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "moto",
            "black",
            "isort",
            "mypy",
            "flake8",
        ],
    },
    author="Nexus Team",
    description="Reasoning generator for compliance control mapping rationale",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)

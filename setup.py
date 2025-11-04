from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="adpa",
    version="0.1.0",
    author="DATA650 Group - Archit Golatkar, Umesh Adari, Girik Tripathi",
    author_email="your-email@example.com",
    description="Autonomous Data Pipeline Agent - AI-driven end-to-end ML pipeline automation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-group/adpa",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "boto3>=1.34.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "scikit-learn>=1.3.0",
        "pydantic>=2.0.0",
        "flask>=2.3.0",
        "requests>=2.31.0",
        "opentelemetry-api>=1.20.0",
        "prometheus-client>=0.17.0",
        "pyyaml>=6.0.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "docs": [
            "sphinx>=7.1.0",
            "sphinx-rtd-theme>=1.3.0",
        ],
        "local": [
            "docker>=6.1.0",
            "airflow>=2.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "adpa=adpa.cli:main",
        ],
    },
)
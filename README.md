# Autonomous Data Pipeline Agent (ADPA)

An AI agent that automatically plans, builds, executes, monitors, and reports end-to-end ML pipelines with minimal human intervention.

## Team Members
- **Archit Golatkar** - Agent Planning & Orchestration + Core Logic
- **Umesh Adari** - Data/ETL, Feature Engineering, Model Training & Evaluation  
- **Girik Tripathi** - Monitoring, Security, API/UI, & Comparative Baseline

## Project Overview

ADPA tackles the challenge of manual, brittle data pipeline creation by providing an autonomous agent that:

- **Automatically plans** pipeline steps based on dataset characteristics and objectives
- **Dynamically adapts** when steps fail with intelligent fallback strategies
- **Learns from experience** to optimize future pipeline executions
- **Provides comprehensive observability** with monitoring and reporting
- **Compares cloud vs local** implementations for concrete benefits analysis

## Current Progress

### ✅ Completed (Phase 1)
- [x] Project structure and development environment
- [x] Core agent framework with reasoning capabilities
- [x] Pipeline planner with intelligent step selection
- [x] Step executor with retry logic and error handling
- [x] Memory manager for learning from past executions
- [x] Basic pipeline components (ingestion, cleaning)
- [x] Configuration management system

### 🚧 In Progress
- [ ] Feature engineering pipeline step
- [ ] ML training and evaluation steps
- [ ] AWS service integrations
- [ ] Monitoring and observability framework

### 📋 Planned
- [ ] Local baseline implementation
- [ ] API and user interface
- [ ] Security and authentication
- [ ] Comprehensive testing suite
- [ ] Documentation and deployment

## Architecture

```
ADPA Agent
├── Agent Core (Planning & Reasoning)
├── Pipeline Steps (Ingestion → Cleaning → Feature Engineering → Training → Evaluation)
├── AWS Integration (S3, Lambda, Glue, SageMaker, Step Functions)
├── Monitoring (CloudWatch, X-Ray, Custom Metrics)
└── Memory System (Learning from past executions)
```

## Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd adpa

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run basic example (coming soon)
python -m src.agent.core.agent
```

## Configuration

Copy `.env.example` to `.env` and configure your settings:

```bash
cp .env.example .env
# Edit .env with your AWS credentials and other settings
```

## Development

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests (coming soon)
pytest

# Code formatting
black src/
flake8 src/
```

## Contributing

1. Create feature branch from main
2. Make changes following code style guidelines
3. Add tests for new functionality
4. Submit pull request for review

## License

MIT License - see LICENSE file for details

---

**Course:** DATA650 - Big Data Analytics  
**Institution:** University of Maryland  
**Semester:** Fall 2025
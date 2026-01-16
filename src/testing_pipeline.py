# Testing Pipeline Configuration
# Fixed version of testing_pipeline.py

# GitHub Actions workflow for CI/CD
GITHUB_WORKFLOW = {
    "name": "Crypto Predict Monitor CI/CD",
    "on": {
        "push": {
            "branches": ["main", "develop"]
        },
        "pull_request": {
            "branches": ["main"]
        }
    },
    "jobs": {
        "test": {
            "runs-on": "ubuntu-latest",
            "strategy": {
                "matrix": {
                    "python-version": ["3.11"]
                }
            },
            "steps": [
                {
                    "name": "Checkout code",
                    "uses": "actions/checkout@v3"
                },
                {
                    "name": "Set up Python ${{ matrix.python-version }}",
                    "uses": "actions/setup-python@v4",
                    "with": {
                        "python-version": "${{ matrix.python-version }}"
                    }
                },
                {
                    "name": "Install dependencies",
                    "run": "pip install -r requirements.txt && pip install -r pnl_requirements.txt && pip install pytest pytest-cov black flake8 mypy bandit"
                },
                {
                    "name": "Run code quality checks",
                    "run": "black --check src/ && flake8 src/ --max-line-length=100 && mypy src/ --ignore-missing-imports && bandit -r src/ -f json -o bandit-report.json"
                },
                {
                    "name": "Run tests",
                    "run": "pytest tests/ --cov=src --cov-report=xml --cov-report=html"
                },
                {
                    "name": "Upload coverage",
                    "uses": "codecov/codecov-action@v3",
                    "with": {
                        "file": "./coverage.xml"
                    }
                }
            ]
        }
    }
}

# Test configuration
TEST_CONFIG = {
    "test_paths": ["tests/unit", "tests/integration"],
    "coverage_threshold": 80,
    "max_line_length": 100,
    "python_version": "3.11"
}

# Quality checks
QUALITY_CHECKS = {
    "black": True,
    "flake8": True,
    "mypy": True,
    "bandit": True,
    "pytest": True
}

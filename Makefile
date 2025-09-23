# Makefile for das-bridge development

.PHONY: help install install-dev clean test test-cov lint format type-check security docs build pre-commit run-ci

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
PROJECT := das_trader
TESTS := tests

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)DAS-Bridge Development Commands$(NC)"
	@echo "================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install production dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

install-dev: install ## Install development dependencies
	$(PIP) install -r requirements-dev.txt
	pre-commit install

clean: ## Clean build artifacts and cache files
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	rm -rf build/ dist/ *.egg-info
	rm -rf htmlcov/ .coverage coverage.xml
	rm -rf .pytest_cache/ .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	@echo "$(GREEN)✓ Cleaned$(NC)"

test: ## Run unit tests
	@echo "$(YELLOW)Running tests...$(NC)"
	pytest $(TESTS) -v --tb=short

test-cov: ## Run tests with coverage report
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	pytest $(TESTS) -v --cov=$(PROJECT) --cov-report=html --cov-report=term-missing

test-fast: ## Run fast tests only (no integration tests)
	@echo "$(YELLOW)Running fast tests...$(NC)"
	pytest $(TESTS) -v -m "not slow and not integration" --tb=short

test-watch: ## Run tests in watch mode
	@echo "$(YELLOW)Running tests in watch mode...$(NC)"
	pytest-watch $(TESTS) -- -v --tb=short

lint: ## Run all linters
	@echo "$(YELLOW)Running linters...$(NC)"
	@echo "Running flake8..."
	flake8 $(PROJECT) $(TESTS)
	@echo "Running pylint..."
	pylint $(PROJECT) --exit-zero
	@echo "$(GREEN)✓ Linting complete$(NC)"

format: ## Format code with black and isort
	@echo "$(YELLOW)Formatting code...$(NC)"
	black $(PROJECT) $(TESTS)
	isort $(PROJECT) $(TESTS)
	@echo "$(GREEN)✓ Formatting complete$(NC)"

format-check: ## Check code formatting without changes
	@echo "$(YELLOW)Checking code format...$(NC)"
	black --check $(PROJECT) $(TESTS)
	isort --check-only $(PROJECT) $(TESTS)

type-check: ## Run type checking with mypy
	@echo "$(YELLOW)Running type checker...$(NC)"
	mypy $(PROJECT)

security: ## Run security checks
	@echo "$(YELLOW)Running security checks...$(NC)"
	bandit -r $(PROJECT) -ll
	safety check --json 2>/dev/null || echo "$(YELLOW)Warning: Some packages may have known vulnerabilities$(NC)"

pre-commit: ## Run pre-commit hooks on all files
	@echo "$(YELLOW)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files

docs: ## Build documentation
	@echo "$(YELLOW)Building documentation...$(NC)"
	cd docs && $(MAKE) clean && $(MAKE) html
	@echo "$(GREEN)✓ Documentation built in docs/_build/html$(NC)"

build: clean ## Build distribution packages
	@echo "$(YELLOW)Building distribution packages...$(NC)"
	$(PYTHON) -m build
	@echo "$(GREEN)✓ Build complete$(NC)"

publish-test: build ## Publish to TestPyPI
	@echo "$(YELLOW)Publishing to TestPyPI...$(NC)"
	twine upload --repository testpypi dist/*

publish: build ## Publish to PyPI
	@echo "$(RED)Publishing to PyPI...$(NC)"
	@echo "$(RED)Are you sure? [y/N]$(NC)"
	@read -r response; if [ "$$response" = "y" ]; then \
		twine upload dist/*; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

run-ci: ## Run full CI pipeline locally
	@echo "$(YELLOW)Running full CI pipeline...$(NC)"
	$(MAKE) clean
	$(MAKE) install-dev
	$(MAKE) format-check
	$(MAKE) lint
	$(MAKE) type-check
	$(MAKE) security
	$(MAKE) test-cov
	@echo "$(GREEN)✓ CI pipeline complete$(NC)"

dev-server: ## Run development server (if applicable)
	@echo "$(YELLOW)Starting development environment...$(NC)"
	$(PYTHON) -c "import das_trader; print('DAS-Bridge ready for development')"

profile: ## Profile code performance
	@echo "$(YELLOW)Profiling code...$(NC)"
	$(PYTHON) -m cProfile -o profile.stats examples/basic_usage.py
	$(PYTHON) -m pstats profile.stats

deps-check: ## Check for outdated dependencies
	@echo "$(YELLOW)Checking dependencies...$(NC)"
	$(PIP) list --outdated

deps-update: ## Update all dependencies
	@echo "$(YELLOW)Updating dependencies...$(NC)"
	$(PIP) install --upgrade -r requirements.txt
	$(PIP) install --upgrade -r requirements-dev.txt

# Development shortcuts
.PHONY: t tc l f s
t: test ## Shortcut for test
tc: test-cov ## Shortcut for test-cov
l: lint ## Shortcut for lint
f: format ## Shortcut for format
s: security ## Shortcut for security
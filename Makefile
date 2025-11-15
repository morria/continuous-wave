.PHONY: help install install-dev test test-verbose test-coverage lint format type-check clean pre-commit all

# Default target
.DEFAULT_GOAL := help

# Color output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo '$(BLUE)Available targets:$(NC)'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install production dependencies
	@echo '$(BLUE)Installing production dependencies...$(NC)'
	pip install -r requirements.txt
	@echo '$(GREEN)✓ Production dependencies installed$(NC)'

install-dev: ## Install development dependencies
	@echo '$(BLUE)Installing development dependencies...$(NC)'
	pip install -r requirements-dev.txt
	pip install -e .
	@echo '$(GREEN)✓ Development environment ready$(NC)'

test: ## Run tests with coverage
	@echo '$(BLUE)Running tests with coverage...$(NC)'
	python -m pytest tests/ -v --cov=continuous_wave --cov-report=term-missing --cov-fail-under=90
	@echo '$(GREEN)✓ Tests passed$(NC)'

test-verbose: ## Run tests with verbose output
	@echo '$(BLUE)Running tests with verbose output...$(NC)'
	python -m pytest tests/ -vv --cov=continuous_wave --cov-report=term-missing --cov-report=html
	@echo '$(GREEN)✓ Tests completed. Coverage report: htmlcov/index.html$(NC)'

test-unit: ## Run only unit tests
	@echo '$(BLUE)Running unit tests...$(NC)'
	python -m pytest tests/unit/ -v --cov=continuous_wave --cov-report=term-missing
	@echo '$(GREEN)✓ Unit tests passed$(NC)'

test-integration: ## Run only integration tests
	@echo '$(BLUE)Running integration tests...$(NC)'
	python -m pytest tests/integration/ -v
	@echo '$(GREEN)✓ Integration tests passed$(NC)'

test-watch: ## Run tests in watch mode (requires pytest-watch)
	@echo '$(BLUE)Running tests in watch mode...$(NC)'
	pytest-watch tests/ -- -v --cov=continuous_wave

lint: ## Run linting checks
	@echo '$(BLUE)Running ruff linter...$(NC)'
	ruff check src/ tests/
	@echo '$(GREEN)✓ Linting passed$(NC)'

lint-fix: ## Run linting with auto-fix
	@echo '$(BLUE)Running ruff with auto-fix...$(NC)'
	ruff check src/ tests/ --fix
	@echo '$(GREEN)✓ Linting fixes applied$(NC)'

format: ## Format code with black and ruff
	@echo '$(BLUE)Formatting code...$(NC)'
	black src/ tests/
	ruff check src/ tests/ --fix
	@echo '$(GREEN)✓ Code formatted$(NC)'

format-check: ## Check if code is formatted correctly
	@echo '$(BLUE)Checking code formatting...$(NC)'
	black --check src/ tests/
	@echo '$(GREEN)✓ Code formatting is correct$(NC)'

type-check: ## Run type checking with mypy
	@echo '$(BLUE)Running mypy type checker...$(NC)'
	python -m mypy src/continuous_wave --strict
	@echo '$(GREEN)✓ Type checking passed$(NC)'

pre-commit: format lint type-check test ## Run all pre-commit checks
	@echo '$(GREEN)✓ All pre-commit checks passed$(NC)'

ci: lint type-check test ## Run CI pipeline checks
	@echo '$(GREEN)✓ All CI checks passed$(NC)'

clean: ## Clean up generated files
	@echo '$(BLUE)Cleaning up...$(NC)'
	rm -rf build/ dist/ *.egg-info htmlcov/ .coverage .pytest_cache/ .ruff_cache/ .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	@echo '$(GREEN)✓ Cleaned up$(NC)'

build: clean ## Build distribution packages
	@echo '$(BLUE)Building distribution packages...$(NC)'
	python -m build
	@echo '$(GREEN)✓ Build complete$(NC)'

publish-test: build ## Publish to TestPyPI
	@echo '$(BLUE)Publishing to TestPyPI...$(NC)'
	twine upload --repository testpypi dist/*
	@echo '$(GREEN)✓ Published to TestPyPI$(NC)'

publish: build ## Publish to PyPI
	@echo '$(BLUE)Publishing to PyPI...$(NC)'
	twine upload dist/*
	@echo '$(GREEN)✓ Published to PyPI$(NC)'

all: install-dev pre-commit ## Install and run all checks
	@echo '$(GREEN)✓ Everything is ready!$(NC)'

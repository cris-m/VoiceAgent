.PHONY: help install dev serve test lint format clean

# Default target
help:
	@echo "VoiceAgent Backend Commands"
	@echo ""
	@echo "  make install    Install dependencies"
	@echo "  make dev        Start development server"
	@echo "  make serve      Start production server"
	@echo "  make test       Run tests"
	@echo "  make lint       Run linter"
	@echo "  make format     Format code"
	@echo "  make clean      Clean cache files"
	@echo ""

# Install dependencies
install:
	uv sync

# Development server with auto-reload
dev:
	uv run python -m cli.main dev

# Production server
serve:
	uv run python -m cli.main serve

# Run tests
test:
	uv run pytest tests/ -v

# Lint code
lint:
	uv run ruff check .

# Format code
format:
	uv run ruff format .

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

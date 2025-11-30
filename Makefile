.PHONY: install install-backend install-frontend test test-verbose run-backend run-frontend run clean help

# Default target
help:
	@echo "E2B Data Apps Builder - Available commands:"
	@echo ""
	@echo "  make install          - Install all dependencies (backend + frontend)"
	@echo "  make install-backend  - Install backend Python dependencies"
	@echo "  make install-frontend - Install frontend Node dependencies"
	@echo ""
	@echo "  make test             - Run backend tests"
	@echo "  make test-verbose     - Run backend tests with verbose output"
	@echo ""
	@echo "  make run-backend      - Start backend server (port 8000)"
	@echo "  make run-frontend     - Start frontend dev server (port 5173)"
	@echo "  make run              - Start both backend and frontend"
	@echo ""
	@echo "  make clean            - Clean generated files and caches"

# Installation
install: install-backend install-frontend

install-backend:
	@echo "Installing backend dependencies..."
	python -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# Testing
test:
	@echo "Running backend tests..."
	. .venv/bin/activate && python -m pytest tests/

test-verbose:
	@echo "Running backend tests (verbose)..."
	. .venv/bin/activate && python -m pytest tests/ -v --tb=short

# Running
run-backend:
	@echo "Starting backend server..."
	. .venv/bin/activate && SANDBOX_MODE=local uvicorn backend.app.main:app --reload --port 8000

run-frontend:
	@echo "Starting frontend dev server..."
	cd frontend && npm run dev

run:
	@echo "Starting both servers (backend in background)..."
	@make run-backend &
	@sleep 2
	@make run-frontend

# Cleanup
clean:
	@echo "Cleaning up..."
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -rf backend/__pycache__
	rm -rf backend/app/__pycache__
	rm -rf tests/__pycache__
	rm -rf .venv
	rm -rf frontend/node_modules
	rm -rf frontend/dist
	rm -rf logs/
	@echo "Done."

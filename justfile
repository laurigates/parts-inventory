# parts-inventory task runner — `just` lists recipes

# List available recipes
default:
    @just --list

# Run the capture app with reload (http://localhost:8000)
dev:
    uv run uvicorn app.server:app --reload

# Regenerate exports/ in the data dir from inventory.db
export:
    uv run parts-inventory export

# Run the test suite
test *args:
    uv run pytest {{args}}

# Lint with ruff
lint:
    uv run ruff check .

# Check formatting with ruff
format-check:
    uv run ruff format --check .

# Apply ruff fixes and formatting
fix:
    uv run ruff check --fix .
    uv run ruff format .

# Type-check with ty
typecheck:
    uv run ty check

# All gates CI runs: lint, format, types, tests
check: lint format-check typecheck test

# Install dependencies and git hooks
setup:
    uv sync
    uv run pre-commit install --hook-type pre-commit --hook-type commit-msg

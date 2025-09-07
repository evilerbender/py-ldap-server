# py-ldap-server uv Configuration

This project is configured to work seamlessly with [uv](https://github.com/astral-sh/uv), the fast Python package manager.

## Quick Commands

```bash
# Run the server with JSON backend
uv run py-ldap-server --json data.json

# Run with custom port and host
uv run py-ldap-server --port 389 --bind-host 0.0.0.0 --json data.json

# Use the convenience script
./run-server.sh

# Install additional dependencies
uv add <package-name>

# Sync dependencies from pyproject.toml
uv sync

# Run tests
uv run pytest

# Format code
uv run black src/ tests/
uv run isort src/ tests/
```

## Project Structure

- `pyproject.toml`: Project configuration with dependencies and scripts
- `src/ldap_server/`: Main source code
- `data.json`: Sample LDAP data for JSON backend
- `run-server.sh`: Convenience script to start the server
- `tests/`: Unit tests

## Features

- **No virtual environment needed**: uv manages Python environments automatically
- **Fast dependency resolution**: Much faster than pip
- **Script entries**: Use `uv run py-ldap-server` directly
- **Hot reload**: JSON backend supports live data reloading

## Dependencies

The project automatically installs:
- `ldaptor>=21.2.0`: LDAP protocol implementation
- `twisted>=22.10.0`: Async networking framework  
- `watchdog>=3.0.0`: File system monitoring for hot reload

## Development Dependencies

Use `uv sync --dev` to also install:
- `pytest`, `pytest-twisted`, `pytest-cov`: Testing
- `black`, `isort`: Code formatting
- `flake8`, `mypy`: Linting and type checking

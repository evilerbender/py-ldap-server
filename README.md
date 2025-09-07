# py-ldap-server

A Python implementation of an LDAP (Lightweight Directory Access Protocol) server using Ldaptor and Twisted.

## Features

- RFC 4511 compliant LDAP protocol implementation
- Built on Twisted for async networking
- Pluggable storage backends
- Support for standard LDAP operations (bind, search, add, modify, delete)
- TLS/LDAPS support
- Compatible with standard LDAP clients

## Quick Start

### Running with uv/uvx

You can use [uv](https://github.com/astral-sh/uv) for fast dependency management and environment isolation:

```bash
# Install uv (if not already installed)
pip install uv
# or
curl -Ls https://astral.sh/uv/install.sh | bash

# Run the LDAP server directly with uv (recommended)
uv run py-ldap-server --json data.json

# Or run with additional options
uv run py-ldap-server --port 1389 --bind-host localhost --json data.json

# Alternative: Use the provided script
./run-server.sh

# Or use uvx for one-off execution
uvx --from . py-ldap-server --json data.json
```

### Installation with pip

```bash
# Clone the repository
git clone https://github.com/evilerbender/py-ldap-server.git
cd py-ldap-server

# Install in development mode
pip install -e .[dev]
```

### Running the Server

```bash
# Start the LDAP server on port 1389 (with uv - recommended)
uv run py-ldap-server --port 1389 --bind-host localhost

# Or with pip installation
py-ldap-server --port 1389 --bind-host localhost

# Using JSON backend with hot reload
uv run py-ldap-server --json data.json

# Run on all interfaces with custom port
uv run py-ldap-server --port 389 --bind-host 0.0.0.0 --json data.json
```

### Testing with ldapsearch

```bash
# Test anonymous bind and search
ldapsearch -x -H ldap://localhost:1389 -b "dc=example,dc=com" -s base "(objectClass=*)"
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
black src/ tests/
isort src/ tests/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

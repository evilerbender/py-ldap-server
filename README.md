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

### Installation

```bash
# Clone the repository
git clone https://github.com/evilerbender/py-ldap-server.git
cd py-ldap-server

# Install in development mode
pip install -e .[dev]
```

### Running the Server

```bash
# Start the LDAP server on port 1389
py-ldap-server --port 1389 --bind-host localhost
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

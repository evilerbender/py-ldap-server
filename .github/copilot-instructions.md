# py-ldap-server - GitHub Copilot Instructions

## Project Overview
This is a Python implementation of an LDAP (Lightweight Directory Access Protocol) server. The project has completed Phase 1 (MVP) and has comprehensive documentation structure in place.

## Current Status (v0.2.0)
- ✅ **Phase 1 Complete**: Foundation & Basic Server (MVP)
- ✅ **Comprehensive Documentation**: 26 documentation files across 6 categories
- ✅ **Python 3.12+**: Modern Python requirements and tooling
- ✅ **Enhanced Testing**: 42 unit tests with comprehensive coverage
- ✅ **Authentication System**: Basic bind operations and password management
- ✅ **Multiple Storage Backends**: In-memory and JSON file-based storage
- 🚧 **Phase 2 Ready**: Core LDAP Operations development can begin

## 4-Phase Development Outline

### Phase 1: Foundation & Basic Server (MVP)
**Goal**: Get a minimal LDAP server running that can handle basic operations

**Deliverables**:
- Project setup with `pyproject.toml` and development dependencies
- Basic Ldaptor server that starts and accepts connections
- Simple in-memory directory tree with sample data
- Anonymous bind support
- Basic search operations (base scope only)
- Unit tests for core components
- Basic logging and error handling

**Key Files to Implement**:
- `src/ldap_server/__init__.py`
- `src/ldap_server/server.py` - Main entry point
- `src/ldap_server/factory.py` - Basic LDAPServerFactory
- `src/ldap_server/storage/memory.py` - In-memory storage
- `tests/unit/test_server.py` - Basic server tests
- `pyproject.toml` - Project configuration

**Success Criteria**: `ldapsearch -x -H ldap://localhost:1389 -b "dc=example,dc=com" -s base` returns root entry

### Phase 2: Core LDAP Operations
**Goal**: Implement full LDAP search capabilities and basic authentication

**Deliverables**:
- Complete search scope support (base, one-level, subtree)
- LDAP filter parsing and evaluation
- Simple bind authentication (username/password)
- Basic schema validation
- LDIF data loading capabilities
- Integration tests with real LDAP clients
- Proper error responses and LDAP result codes

**Key Files to Implement**:
- `src/ldap_server/handlers/search.py` - Advanced search logic
- `src/ldap_server/handlers/bind.py` - Authentication handlers
- `src/ldap_server/auth/simple.py` - Simple bind implementation
- `src/ldap_server/schema/core.py` - Basic schema handling
- `src/ldap_server/storage/ldif_tree.py` - LDIF extensions
- `tests/integration/test_ldap_clients.py` - Client compatibility tests

**Success Criteria**: Full LDAP search operations work with ldapsearch, authenticated binds succeed

### Phase 3: Write Operations & Advanced Features
**Goal**: Support directory modifications and advanced LDAP features

**Deliverables**:
- Add, modify, delete operations
- UPN-style authentication (Active Directory compatibility)
- Multi-backend storage support (file-based, database)
- LDAPS (TLS) support
- Access control and authorization
- Performance optimizations
- Comprehensive test suite

**Key Files to Implement**:
- `src/ldap_server/handlers/modify.py` - Write operations
- `src/ldap_server/auth/upn.py` - UPN authentication
- `src/ldap_server/storage/backend.py` - Storage abstraction
- `src/ldap_server/storage/file.py` - File-based storage
- TLS configuration and certificate handling
- Access control policies

**Success Criteria**: Can modify directory entries, TLS connections work, compatibility with PAM/SSSD

### Phase 4: Production Features & Extensions
**Goal**: Production-ready server with monitoring and advanced capabilities

**Deliverables**:
- Monitoring and metrics integration
- Configuration management system
- REST API for directory operations
- Backup and replication features
- Performance tuning and optimization
- Comprehensive documentation
- Docker containerization
- CI/CD pipeline

**Key Files to Implement**:
- REST API endpoints and OpenAPI specs
- Monitoring dashboards and health checks
- Configuration file parsing
- Backup/restore utilities
- Docker and deployment scripts
- Complete API documentation

**Success Criteria**: Production deployment ready, monitoring active, REST API functional

## Architecture Guidelines

### Core Components
- **LDAP Protocol Handler**: Implement RFC 4511 LDAP protocol parsing and response generation
- **Directory Data Store**: Backend storage abstraction (AWS S3, in-memory, file-based, or database)
- **Authentication Module**: Handle bind operations and access control
- **Support both anonymous and authenticated access**: Allow unauthenticated queries while enforcing security for write operations
- **Schema Engine**: Manage LDAP schema definitions and validation
- **Search Engine**: Process LDAP search operations with filters
- **Supported Ldap Clients**: Ensure compatibility with common LDAP clients (e.g., ldapsearch, PAM, SSSD, OpenLDAP)
- **All configuration and operational parameters should be easily adjustable via env vars or env file**: Use a configuration file or environment variables for settings like port, bind host, TLS options, etc.
- **Solution should be containerized**: Provide Docker support for easy deployment

### Stretch Goals
- **Monitoring and Logging**: Integrate with monitoring tools and provide detailed logging
- **REST API**: Optionally expose a REST API for directory operations
- **Advanced Documentation**: Expand documentation with tutorials, troubleshooting guides, and performance optimization

### Recommended Project Structure
```
src/
├── ldap_server/
│   ├── __init__.py
│   ├── server.py          # Main server entry point using Ldaptor
│   ├── factory.py         # Custom LDAPServerFactory
│   ├── handlers/          # Custom LDAP operation handlers
│   │   ├── __init__.py
│   │   ├── bind.py        # Custom bind operations
│   │   ├── search.py      # Search customizations
│   │   └── modify.py      # Modify/add/delete operations
│   ├── storage/           # Data storage backends
│   │   ├── __init__.py
│   │   ├── backend.py     # Storage interface
│   │   ├── ldif_tree.py   # LDIFTreeEntry extensions
│   │   └── memory.py      # In-memory implementation
│   ├── schema/            # LDAP schema handling
│   │   ├── __init__.py
│   │   └── core.py        # Schema validation with Ldaptor
│   └── auth/              # Authentication and authorization
│       ├── __init__.py
│       ├── simple.py      # Simple bind authentication
│       └── upn.py         # UPN-style authentication (like AD)
tests/
├── unit/
├── integration/
└── fixtures/              # Test LDAP data (LDIF format)
scripts/                   # Deployment and utility scripts
docs/                      # Comprehensive documentation structure
├── README.md              # Documentation overview and navigation
├── guides/                # User-focused guides
│   ├── README.md          # Guide navigation
│   ├── quick-start.md     # Getting started quickly  
│   ├── configuration.md   # Comprehensive configuration
│   └── authentication.md  # Authentication setup
├── api/                   # Technical API reference
│   ├── README.md          # API documentation overview
│   ├── server.md          # Main server component
│   ├── factory.md         # LDAP server factory
│   ├── handlers/          # Operation handlers
│   ├── auth/              # Authentication modules
│   └── storage/           # Storage backends
├── deployment/            # Production deployment
│   ├── README.md          # Deployment overview
│   ├── systemd.md         # SystemD service setup
│   └── security.md        # Security hardening
├── development/           # Developer documentation
│   ├── README.md          # Development overview
│   ├── architecture.md    # System architecture
│   ├── contributing.md    # Contribution guidelines
│   ├── testing.md         # Testing strategies
│   ├── roadmap.md         # Development roadmap
│   └── PHASE*_TODOS.md    # Phase-specific tasks
└── examples/              # Configuration examples
    ├── README.md          # Examples overview
    └── configuration/     # Sample configurations
requirements.txt           # Dependencies (ldaptor, twisted)
pyproject.toml             # Modern Python packaging
```

## Development Patterns

### LDAP Protocol Implementation
- Use **Ldaptor** as the primary LDAP library - provides Twisted-based server/client with built-in protocol handling
- Leverage Ldaptor's `LDAPServer` class and `LDIFTreeEntry` for directory storage
- Implement custom server classes by extending `ldaptor.protocols.ldap.ldapserver.LDAPServer`
- Use Ldaptor's built-in BER/ASN.1 parsing and LDAP filter handling

### Twisted Integration
- Build on Twisted's reactor pattern for async networking
- Use `ServerFactory` and protocol classes for connection handling
- Register adapters for `IConnectedLDAPEntry` interface to connect factory to directory tree
- Implement custom `handle_LDAPBindRequest` and other operation handlers as needed

### Error Handling
- Use Ldaptor's built-in LDAP exception classes from `ldaptor.protocols.ldap.ldaperrors`
- Return proper LDAP result codes using `pureldap.LDAPBindResponse` and similar classes
- Log detailed errors server-side but return RFC-compliant responses to clients

### Testing Strategy
- Use `pytest` with Twisted support (`pytest-twisted`)
- Create test fixtures using Ldaptor's `LDIFTreeEntry` for sample directory data
- Test against common LDAP clients (ldapsearch, Apache Directory Studio)
- Use Ldaptor's client classes for integration testing

### Dependencies
- **Core**: `ldaptor` (includes Twisted, BER/ASN.1 handling, LDAP protocol)
- **Testing**: `pytest`, `pytest-twisted`, `pytest-cov`
- **Optional**: `python-ldap` (for additional client testing), `cryptography` (for TLS)

### Known Issues & Workarounds
- **Deprecation Warnings**: The project includes warning filters for known deprecation warnings from dependencies:
  - `passlib` library uses deprecated `crypt` module (will be addressed in future passlib releases)
  - `ldaptor` DistinguishedName `__str__` method deprecation (use `.getText()` instead)
- These warnings are filtered in `pyproject.toml` and `server.py` to provide clean output

## Key Implementation Notes

### LDAP Message Flow
1. Client connects via TCP (default port 389)
2. Parse BER-encoded LDAP messages using ASN.1 decoder
3. Route to appropriate operation handler (bind, search, add, modify, delete)
4. Execute operation against data store
5. Return BER-encoded LDAP response

### Ldaptor-Specific Patterns
- Extend `LDAPServer` class for custom server behavior
- Use `LDIFTreeEntry` for in-memory directory storage
- Register adapters: `registerAdapter(lambda x: x.root, LDAPServerFactory, IConnectedLDAPEntry)`
- Override `handle_LDAPBindRequest` for custom authentication
- Use `pureldap` classes for LDAP message construction

### Distinguished Names (DN)
- Implement proper DN parsing and normalization
- Use case-insensitive attribute name matching
- Support multi-valued RDNs and proper escaping

### Search Operations
- Implement LDAP filter parsing (RFC 4515)
- Support scope: base, one-level, subtree
- Handle paging controls for large result sets
- Implement proper alias dereferencing

## Security Considerations
- Implement rate limiting for bind attempts
- Support LDAPS (LDAP over TLS) on port 636
- Validate all input to prevent injection attacks
- Implement proper access controls based on bind DN

## Common Commands
```bash
# Development setup (recommended with uv)
uv sync
uv run py-ldap-server --help

# Alternative setup with pip
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e .[dev]

# Testing
uv run pytest tests/ -v                    # Run all tests
uv run pytest tests/ --cov=src/ldap_server # With coverage
pytest tests/ -v                           # If using pip/venv

# Run server
uv run py-ldap-server --port 1389 --bind-host localhost
uv run py-ldap-server --json data.json     # With JSON backend
py-ldap-server --port 1389 --bind-host localhost  # If using pip/venv

# Test with ldapsearch
ldapsearch -x -H ldap://localhost:1389 -b "dc=example,dc=com" -s base "(objectClass=*)"
ldapsearch -x -H ldap://localhost:1389 -b "dc=example,dc=com" -s sub "(cn=*)"

# Documentation access
docs/README.md                             # Start here for documentation
docs/guides/quick-start.md                 # Quick start guide
docs/api/README.md                         # API documentation
docs/development/README.md                 # Development guide
```

When implementing new features, prioritize RFC compliance and compatibility with standard LDAP clients over custom extensions.

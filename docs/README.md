# py-ldap-server Documentation

Welcome to the comprehensive documentation for py-ldap-server - a Python implementation of an LDAP (Lightweight Directory Access Protocol) server built on ldaptor and Twisted.

## 📚 **Documentation Structure**

This documentation is organized to mirror the project's code structure, making it easy to find relevant information whether you're a user, developer, or systems administrator.

```
docs/
├── README.md                    # This file - main documentation index
├── guides/                      # User and administrator guides
│   ├── README.md               # Guides overview
│   ├── quick-start.md          # Getting started quickly
│   ├── configuration.md        # Server configuration options
│   ├── authentication.md       # Authentication setup and usage
│   └── ldap-operations.md      # LDAP operations and client usage
├── api/                        # Technical API documentation
│   ├── README.md               # API documentation overview
│   ├── server.md               # Core server classes and methods
│   ├── factory.md              # LDAP server factory documentation
│   ├── auth/                   # Authentication system documentation
│   │   ├── README.md           # Authentication overview
│   │   ├── password.md         # Password management and security
│   │   └── bind.md             # LDAP bind operations
│   ├── storage/                # Storage backend documentation
│   │   ├── README.md           # Storage systems overview
│   │   ├── memory.md           # In-memory storage backend
│   │   └── json.md             # Unified JSON storage with federation support
│   └── handlers/               # LDAP protocol handlers (future)
│       └── README.md           # Protocol handlers overview
├── deployment/                 # Production deployment documentation
│   ├── README.md               # Deployment overview
│   ├── systemd.md              # SystemD service configuration
│   ├── docker.md               # Container deployment (future)
│   └── security.md             # Security hardening and best practices
├── development/                # Developer documentation
│   ├── README.md               # Development overview
│   ├── architecture.md         # System architecture and design
│   ├── contributing.md         # How to contribute to the project
│   ├── testing.md              # Testing guidelines and practices
│   └── roadmap.md              # Development roadmap and phases
├── examples/                   # Code examples and tutorials
│   ├── README.md               # Examples overview
│   ├── basic-usage.md          # Basic server usage examples
│   ├── client-examples.md      # LDAP client integration examples
│   └── configuration/          # Example configuration files
└── PROJECT_PHASES.md           # Project development phases (existing)
```

## 🚀 **Quick Navigation**

### 👤 **For Users & Administrators**
- **[📖 Quick Start Guide](guides/quick-start.md)** - Get up and running in 5 minutes
- **[⚙️ Configuration Guide](guides/configuration.md)** - Server configuration options
- **[🔐 Authentication Guide](guides/authentication.md)** - Setting up user authentication
- **[🚀 Deployment Guide](deployment/README.md)** - Production deployment options

### 👨‍💻 **For Developers**
- **[🏗️ Architecture Overview](development/architecture.md)** - System design and components
- **[📊 API Reference](api/README.md)** - Complete API documentation
- **[🧪 Testing Guide](development/testing.md)** - Running and writing tests
- **[🛣️ Development Roadmap](development/roadmap.md)** - Project phases and future plans

### 🔧 **For System Administrators**
- **[🛡️ Security Guide](deployment/security.md)** - Security hardening and best practices
- **[⚙️ SystemD Deployment](deployment/systemd.md)** - Linux service configuration
- **[📊 Monitoring & Logging](deployment/README.md#monitoring)** - Operational monitoring

## 📋 **Project Status**

- **✅ Phase 1**: Foundation & Basic Server - **COMPLETE** (20/20 tasks)
- **🚧 Phase 2**: Core LDAP Operations - **IN PROGRESS** (1/10 tasks)
- **⏳ Phase 3**: Write Operations & Advanced Features - **NOT STARTED** (0/14 tasks)
- **⏳ Phase 4**: Production Features & Extensions - **NOT STARTED** (0/16 tasks)

**Overall Progress**: 21/60 tasks completed (35%)

See **[📋 Project Phases](PROJECT_PHASES.md)** for detailed roadmap.

## 🎯 **Current Capabilities**

### ✅ **Implemented Features**
- **LDAP Server**: Complete server using ldaptor/Twisted
- **Storage Backends**: Memory and unified JSON storage with single-file and federated multi-file support
- **Authentication**: Anonymous and simple bind authentication
- **Security**: bcrypt password hashing and security hardening
- **Data Integrity**: Atomic writes, file locking, and automatic backups for JSON storage
- **Federation Support**: Multiple JSON files merged into single directory tree
- **Hot Reload**: File watching with automatic data reloading
- **Read-Only Mode**: External configuration management support
- **Concurrent Access**: Thread-safe operations with file locking protection
- **Testing**: 72 comprehensive unit tests covering all functionality
- **Deployment**: SystemD service configuration

### 🚧 **In Development (Phase 2)**
- Advanced LDAP search operations with filters
- Schema validation and LDIF data loading
- Enhanced error handling with proper LDAP result codes

## 🔗 **External Links**

- **[GitHub Repository](https://github.com/evilerbender/py-ldap-server)** - Source code and issues
- **[LDAP RFC 4511](https://tools.ietf.org/html/rfc4511)** - LDAP protocol specification
- **[ldaptor Documentation](https://ldaptor.readthedocs.io/)** - Core LDAP library we use
- **[Twisted Documentation](https://docs.twistedmatrix.com/)** - Networking framework

## 🤝 **Contributing**

We welcome contributions! Please see:
- **[📝 Contributing Guide](development/contributing.md)** - How to contribute
- **[🧪 Testing Guide](development/testing.md)** - Running tests and test development
- **[🏗️ Architecture Guide](development/architecture.md)** - Understanding the codebase

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

---

**Last Updated**: September 7, 2025  
**Documentation Version**: Aligned with Phase 1 completion

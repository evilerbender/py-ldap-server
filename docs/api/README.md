# API Documentation

This section provides technical documentation for py-ldap-server's API, classes, and internal components. This documentation is primarily intended for developers working with or contributing to the codebase.

## 🏗️ **Architecture Overview**

py-ldap-server is built on a modular architecture that mirrors the structure of LDAP itself:

```
ldap_server/
├── server.py          # Core LDAP server implementation
├── factory.py         # Twisted ServerFactory for LDAP connections  
├── auth/              # Authentication and authorization
│   ├── password.py    # Password management and hashing
│   └── bind.py        # LDAP bind operation handlers
├── storage/           # Data storage backends
│   ├── memory.py      # In-memory storage implementation
│   └── json.py        # JSON file-based storage
└── handlers/          # LDAP protocol message handlers (future)
```

## 📚 **API Reference by Component**

### 🖥️ **Core Server Components**
- **[🎛️ Server](server.md)** - `LDAPServerService` and main server class
- **[🏭 Factory](factory.md)** - `LDAPServerFactory` and `CustomLDAPServer`

### 🔐 **Authentication System**
- **[📁 Authentication Overview](auth/README.md)** - Authentication system architecture
- **[🔒 Password Management](auth/password.md)** - `PasswordManager` class and security
- **[🔑 Bind Operations](auth/bind.md)** - `BindHandler` and LDAP bind processing

### 💾 **Storage Backends**
- **[📁 Storage Overview](storage/README.md)** - Storage system architecture
- **[💿 Memory Storage](storage/memory.md)** - `MemoryStorage` in-memory backend
- **[📄 JSON Storage](storage/json.md)** - `JSONStorage` file-based backend

### 🔧 **Protocol Handlers** (Future - Phase 2)
- **[📁 Handlers Overview](handlers/README.md)** - LDAP message handlers architecture

## 🎯 **Key Design Principles**

### 🧩 **Modular Architecture**
Each component has a clear responsibility and can be developed/tested independently:
- **Storage backends** are interchangeable via a common interface
- **Authentication methods** can be extended without changing core server
- **Protocol handlers** will be pluggable for different LDAP operations

### 🔌 **Plugin-Based Design**
The server supports multiple implementations of core components:
- **Storage**: Memory, JSON file, database (future)
- **Authentication**: Anonymous, simple bind, UPN (future)
- **Protocol**: Standard LDAP, extensions (future)

### 🔒 **Security First**
Security is built into every component:
- **Password hashing** uses bcrypt with configurable rounds
- **Input validation** prevents injection attacks
- **Access control** is designed for fine-grained permissions

## 📋 **Class Hierarchy**

### Core Server Classes
```python
LDAPServerService              # Main server service class
├── LDAPServerFactory         # Twisted ServerFactory
    └── CustomLDAPServer      # Custom LDAP protocol handler
```

### Storage Classes
```python
StorageBackend (interface)     # Common storage interface
├── MemoryStorage             # In-memory implementation
└── JSONStorage               # File-based implementation
```

### Authentication Classes
```python
PasswordManager               # Password hashing and verification
BindHandler                   # LDAP bind operation processing
```

## 🧪 **Testing Architecture**

Our test suite mirrors the API structure:
- **`tests/unit/test_server.py`** - Server and factory tests
- **`tests/unit/test_bind.py`** - Authentication and bind tests
- **`tests/unit/test_password.py`** - Password management tests
- **`tests/unit/test_json_storage.py`** - JSON storage backend tests

**Total Coverage**: 42 comprehensive unit tests

## 🔄 **Data Flow**

### LDAP Request Processing
```
Client Request → CustomLDAPServer → BindHandler → Storage Backend
                                 ↓
Client Response ← LDAPResponse   ← Authentication ← Data Retrieval
```

### Storage Operations
```
Application → Storage Interface → Backend Implementation → Data Store
            ← Common Response   ← Backend Response      ← Storage Result
```

## 📖 **Usage Examples**

### Basic Server Setup
```python
from ldap_server.server import LDAPServerService
from ldap_server.storage.memory import MemoryStorage

storage = MemoryStorage()
server = LDAPServerService(
    port=1389,
    bind_host='localhost',
    storage=storage,
    debug=True
)
server.start()
```

### Custom Storage Backend
```python
from ldap_server.storage.json import JSONStorage

storage = JSONStorage(json_file='my_directory.json')
server = LDAPServerService(storage=storage)
```

## 🚀 **Extension Points**

The API is designed for extension in Phase 2 and beyond:

### Custom Storage Backends
Implement the storage interface for new backends:
```python
class CustomStorage:
    def get_root(self):
        """Return root LDIF entry"""
        pass
    
    def cleanup(self):
        """Clean up resources"""
        pass
```

### Custom Authentication
Extend authentication for new methods:
```python
class CustomAuthenticator:
    def authenticate(self, dn, password):
        """Authenticate user credentials"""
        pass
```

## 🔗 **Related Documentation**

- **[🏗️ Architecture Guide](../development/architecture.md)** - High-level system design
- **[🧪 Testing Guide](../development/testing.md)** - Testing patterns and practices
- **[📝 Contributing Guide](../development/contributing.md)** - How to extend the API

---

**API Version**: Phase 1 Complete  
**Last Updated**: September 7, 2025

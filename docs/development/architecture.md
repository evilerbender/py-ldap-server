# System Architecture

This document provides a comprehensive overview of py-ldap-server's architecture, design patterns, and system components.

## 🏛️ **Architecture Overview**

py-ldap-server is built on a modular, plugin-based architecture that prioritizes extensibility, security, and RFC compliance. The system is designed around the LDAP protocol specification (RFC 4511) while providing modern Python development practices.

### 🎯 **Core Design Principles**

#### 🧩 **Modular Architecture**
Each component has clear responsibilities and can be developed independently:
- **Server Core**: LDAP protocol handling using ldaptor/Twisted
- **Storage Backends**: Pluggable data persistence layers
- **Authentication System**: Extensible authentication mechanisms
- **Protocol Handlers**: Modular LDAP operation processors

#### 🔒 **Security First**
Security is integrated at every architectural level:
- **Password Security**: bcrypt hashing with configurable rounds
- **Input Validation**: Comprehensive sanitization and validation
- **Access Control**: Fine-grained permission system (Phase 3)
- **Audit Logging**: Complete operation tracking (Phase 3)

#### 📊 **RFC Compliance**
Strict adherence to LDAP standards:
- **RFC 4511**: LDAP Protocol Specification
- **RFC 4515**: LDAP Search Filters (Phase 2)
- **RFC 4519**: LDAP Schema Definitions (Phase 2)
- **RFC 4518**: LDAP String Representation (Phase 3)

### 🏗️ **System Components**

```
┌─────────────────────────────────────────────────────────────┐
│                    LDAP Clients                             │
│  (ldapsearch, Apache Directory Studio, Python ldap3, etc.) │
└─────────────────────┬───────────────────────────────────────┘
                      │ LDAP Protocol (RFC 4511)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 LDAP Server Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ CustomLDAPServer│  │ LDAPServerFactory│  │ Protocol    │ │
│  │ (Protocol Handler)│  │ (Connection Mgmt) │  │ Handlers    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │ Internal API
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                Authentication Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   BindHandler   │  │ PasswordManager │  │ Access      │ │
│  │ (LDAP Bind Ops) │  │ (Security)      │  │ Control     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │ Storage Interface
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Storage Layer                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  MemoryStorage  │  │   JSONStorage   │  │ Database    │ │
│  │  (In-Memory)    │  │ (File-Based)    │  │ Storage*    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │ Data Persistence
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Store                               │
│     RAM / JSON Files / Database / External Systems         │
└─────────────────────────────────────────────────────────────┘
```

*DatabaseStorage planned for Phase 3

### 🔧 **Technology Stack**

#### 🐍 **Core Technologies**
- **Python 3.12+**: Modern Python with enhanced type hints and async support
- **ldaptor**: Twisted-based LDAP library for protocol handling
- **Twisted**: Event-driven networking framework
- **bcrypt**: Industry-standard password hashing

#### 🧪 **Development Tools**
- **pytest**: Testing framework with Twisted integration
- **black**: Code formatting for consistency
- **mypy**: Static type checking
- **flake8**: Code linting and quality checks

#### 📦 **Package Management**
- **pyproject.toml**: Modern Python packaging
- **uv**: Fast Python package installer (optional)
- **pip**: Standard package management

### 📊 **Performance Characteristics**

#### ⚡ **Current Performance (Phase 1)**
- **Startup Time**: < 1 second for MemoryStorage
- **Connection Handling**: Twisted's efficient event loop
- **Memory Usage**: ~50MB base + data size
- **Concurrent Connections**: Limited by system resources

#### 🚀 **Planned Optimizations (Phase 2-3)**
- **Connection Pooling**: Reuse authentication state
- **Query Caching**: Cache search results
- **Database Indexing**: Optimize large directory searches
- **Async Operations**: Non-blocking I/O for all operations

## 🔌 **Plugin Architecture**

The plugin architecture enables extensibility without modifying core components. This design supports the project's evolution from Phase 1 through Phase 4.

### 🧩 **Plugin Types**

#### 💾 **Storage Backend Plugins**
```python
class StorageBackend:
    """Base interface for storage plugins."""
    
    def get_root(self) -> LDIFTreeEntry:
        """Return root directory entry."""
        
    def find_entry_by_dn(self, dn: str) -> Optional[LDIFTreeEntry]:
        """Find entry by distinguished name."""
        
    def cleanup(self) -> None:
        """Clean up resources."""
```

**Available Plugins**:
- ✅ **MemoryStorage**: Fast in-memory storage for development
- ✅ **JSONStorage**: File-based storage with hot reload
- 🚧 **DatabaseStorage**: SQL backend (Phase 3)
- 🚧 **LDIFStorage**: Standard LDIF files (Phase 3)

#### 🔐 **Authentication Plugins**
```python
class AuthenticationBackend:
    """Base interface for authentication plugins."""
    
    def authenticate(self, dn: str, credentials: Any) -> bool:
        """Authenticate user credentials."""
        
    def get_permissions(self, dn: str) -> List[str]:
        """Get user permissions."""
```

**Planned Plugins**:
- ✅ **SimpleAuth**: Username/password authentication
- 🚧 **UPNAuth**: Active Directory style (user@domain.com)
- 🚧 **CertificateAuth**: X.509 certificate authentication
- 🚧 **SAMLAuth**: SAML SSO integration

#### 🔧 **Protocol Handler Plugins**
```python
class ProtocolHandler:
    """Base interface for LDAP operation handlers."""
    
    def handle_request(self, request: LDAPRequest) -> LDAPResponse:
        """Process LDAP operation request."""
```

**Planned Handlers** (Phase 2):
- 🚧 **SearchHandler**: Advanced search with filters
- 🚧 **ModifyHandler**: Add/modify/delete operations
- 🚧 **CompareHandler**: LDAP compare operations
- 🚧 **ExtendedHandler**: Extended operations

### 🔌 **Plugin Registration**

```python
# Plugin registration system (Phase 2)
class PluginRegistry:
    def register_storage(self, name: str, backend_class: Type[StorageBackend]):
        """Register storage backend plugin."""
        
    def register_auth(self, name: str, auth_class: Type[AuthenticationBackend]):
        """Register authentication plugin."""
        
    def get_storage(self, name: str) -> StorageBackend:
        """Get registered storage backend."""

# Usage example
registry = PluginRegistry()
registry.register_storage("redis", RedisStorage)
registry.register_auth("ldap", LDAPAuthentication)
```

## 🔄 **Data Flow**

Understanding how data flows through py-ldap-server helps developers work with the system effectively.

### 📥 **Request Processing Flow**

```
1. Client Connection
   │
   ▼
2. Protocol Parsing (ldaptor)
   │
   ▼  
3. Authentication Check
   │
   ▼
4. Operation Routing
   │
   ▼
5. Storage Access
   │
   ▼
6. Response Generation
   │
   ▼
7. Client Response
```

#### 1️⃣ **Client Connection**
```python
# Twisted ServerFactory handles incoming connections
class LDAPServerFactory(ServerFactory):
    def buildProtocol(self, addr):
        """Create new protocol instance for each connection."""
        return CustomLDAPServer(self)
```

#### 2️⃣ **Protocol Parsing**
```python
# ldaptor handles LDAP BER/ASN.1 parsing automatically
class CustomLDAPServer(LDAPServer):
    def handle_LDAPBindRequest(self, request, controls, reply):
        """Parse and route LDAP bind requests."""
```

#### 3️⃣ **Authentication Check**
```python
# BindHandler processes authentication
class BindHandler:
    def handle_bind(self, dn: str, password: str, storage) -> bool:
        """Authenticate user against storage backend."""
```

#### 4️⃣ **Operation Routing**
```python
# Route to appropriate handler based on operation type
def route_operation(request):
    if isinstance(request, LDAPSearchRequest):
        return SearchHandler().handle(request)
    elif isinstance(request, LDAPBindRequest):
        return BindHandler().handle(request)
```

#### 5️⃣ **Storage Access**
```python
# Storage backend provides data access
storage = JSONStorage("directory.json")
entry = storage.find_entry_by_dn("cn=user,dc=example,dc=com")
```

#### 6️⃣ **Response Generation**
```python
# ldaptor generates RFC-compliant responses
response = LDAPSearchResultEntry(
    objectName="cn=user,dc=example,dc=com",
    attributes=entry.attributes
)
```

### 🔄 **Authentication Flow**

```
Client                    Server                     Storage
  │                        │                          │
  ├─── LDAP Bind Request ──►│                          │
  │                        │                          │
  │                        ├─── Parse Credentials ────┤
  │                        │                          │
  │                        ├─── Find User Entry ─────►│
  │                        │                          │
  │                        │◄─── Return User Data ────┤
  │                        │                          │
  │                        ├─── Verify Password ──────┤
  │                        │                          │
  │                        ├─── Set Auth State ───────┤
  │                        │                          │
  │◄─── Bind Response ─────┤                          │
```

### 🔍 **Search Flow**

```
Client                    Server                     Storage
  │                        │                          │
  ├─── Search Request ─────►│                          │
  │    (base DN, filter)    │                          │
  │                        ├─── Check Authentication ─┤
  │                        │                          │
  │                        ├─── Parse Filter ─────────┤
  │                        │                          │
  │                        ├─── Get Base Entry ──────►│
  │                        │                          │
  │                        │◄─── Return Entry ────────┤
  │                        │                          │
  │                        ├─── Apply Scope ──────────┤
  │                        │                          │
  │                        ├─── Evaluate Filter ──────┤
  │                        │                          │
  │◄─── Search Results ────┤                          │
  │◄─── Search Done ───────┤                          │
```

### 💾 **Storage Flow**

```
Application              Storage Interface           Backend
     │                        │                        │
     ├─── find_entry_by_dn ──►│                        │
     │                        │                        │
     │                        ├─── Backend Specific ──►│
     │                        │    Implementation      │
     │                        │                        │
     │                        │◄─── LDIFTreeEntry ────┤
     │                        │                        │
     │◄─── Entry Object ──────┤                        │
```

## 🎯 **Design Patterns**

### 🏭 **Factory Pattern**
Used for creating server instances and storage backends:
```python
class LDAPServerFactory(ServerFactory):
    def __init__(self, storage, debug=False):
        self.storage = storage
        self.debug = debug
        
    def buildProtocol(self, addr):
        return CustomLDAPServer(self)
```

### 🔌 **Strategy Pattern**
Storage backends use strategy pattern for interchangeable implementations:
```python
# Different strategies for data storage
storage = MemoryStorage()      # Fast, temporary
storage = JSONStorage()        # Persistent, file-based
storage = DatabaseStorage()    # Scalable, SQL-based
```

### 🎭 **Adapter Pattern**
ldaptor integration uses adapter pattern:
```python
# Adapt storage to ldaptor's interface
registerAdapter(lambda x: x.root, LDAPServerFactory, IConnectedLDAPEntry)
```

### 👁️ **Observer Pattern**
File watching in JSONStorage uses observer pattern:
```python
class JSONStorage:
    def __init__(self, json_file, enable_watcher=True):
        if enable_watcher:
            self.observer = Observer()
            self.observer.schedule(self.handler, path, recursive=False)
```

## 🚀 **Evolution Path**

### ✅ **Phase 1: Foundation** (Complete)
- Basic LDAP server with ldaptor/Twisted
- Memory and JSON storage backends
- Simple bind authentication
- Comprehensive test suite

### 🚧 **Phase 2: Core LDAP** (In Progress)
- Advanced search operations
- LDAP filter parsing (RFC 4515)
- Schema validation
- Enhanced error handling

### ⏳ **Phase 3: Write Operations** (Planned)
- Add/modify/delete operations
- UPN authentication
- Database storage backend
- TLS support

### ⏳ **Phase 4: Production** (Planned)
- REST API and web interface
- Monitoring and metrics
- Container deployment
- High availability

## 🔗 **Related Documentation**

- **[🖥️ Server Components](../api/README.md)** - Core server classes
- **[💾 Storage Architecture](../api/storage/README.md)** - Storage system design
- **[🔐 Authentication Design](../api/auth/README.md)** - Authentication architecture
- **[🧪 Testing Guide](testing.md)** - Testing architecture and patterns

---

**Architecture Status**: Phase 1 complete, extensible foundation ready  
**Design Philosophy**: Modular, secure, RFC-compliant, extensible  
**Last Updated**: September 7, 2025

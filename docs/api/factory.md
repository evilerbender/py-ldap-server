# Factory API

This document covers the `LDAPServerFactory` and `CustomLDAPServer` classes that handle LDAP protocol connections in py-ldap-server.

## 🏭 **LDAPServerFactory Class**

The `LDAPServerFactory` class is a Twisted ServerFactory that creates `CustomLDAPServer` instances for each LDAP client connection.

### Class Definition

```python
class LDAPServerFactory(ServerFactory):
    """Twisted ServerFactory for LDAP connections"""
    
    def __init__(self, storage_backend, debug=False):
        """Initialize LDAP server factory"""
        
    def buildProtocol(self, addr) -> CustomLDAPServer:
        """Create CustomLDAPServer for new connections"""
        
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        
    def cleanup(self) -> None:
        """Clean up factory resources"""
```

### 🏗️ **Constructor**

#### `LDAPServerFactory(storage_backend, debug=False)`

Creates a new LDAP server factory.

**Parameters:**
- `storage_backend`: Storage backend instance (MemoryStorage, JSONStorage, etc.)
- `debug` (bool): Enable debug logging (default: False)

**Example:**
```python
from ldap_server.factory import LDAPServerFactory
from ldap_server.storage.memory import MemoryStorage

storage = MemoryStorage()
factory = LDAPServerFactory(storage_backend=storage, debug=True)
```

### 🔄 **Methods**

#### `buildProtocol(addr) -> CustomLDAPServer`

Creates a new `CustomLDAPServer` instance for each client connection.

**Parameters:**
- `addr`: Client address information from Twisted

**Returns:**
- `CustomLDAPServer`: New protocol instance for the connection

**Called by Twisted when:**
- New client connects to LDAP port
- Each connection gets its own protocol instance
- Protocol handles all LDAP operations for that client

**Example:**
```python
# Twisted automatically calls this when clients connect
protocol = factory.buildProtocol(client_address)
# protocol is now a CustomLDAPServer instance
```

#### `get_connection_count() -> int`

Returns the number of active LDAP connections.

**Returns:**
- `int`: Number of currently connected clients

**Example:**
```python
factory = LDAPServerFactory(storage)
count = factory.get_connection_count()
print(f"Active connections: {count}")
```

#### `cleanup() -> None`

Cleans up factory resources and closes all connections.

**Behavior:**
- Closes all active client connections
- Cleans up storage backend resources
- Resets connection tracking

**Example:**
```python
# Called during server shutdown
factory.cleanup()
```

## 🖥️ **CustomLDAPServer Class**

The `CustomLDAPServer` class extends Ldaptor's `LDAPServer` to provide custom LDAP protocol handling for each client connection.

### Class Definition

```python
class CustomLDAPServer(LDAPServer):
    """Custom LDAP protocol handler extending Ldaptor's LDAPServer"""
    
    def __init__(self, storage_backend, bind_handler, debug=False):
        """Initialize custom LDAP server protocol"""
        
    def handle_LDAPBindRequest(self, request, reply):
        """Handle LDAP bind requests"""
        
    def handle_LDAPSearchRequest(self, request, reply):
        """Handle LDAP search requests"""
        
    def connectionMade(self):
        """Called when client connects"""
        
    def connectionLost(self, reason):
        """Called when client disconnects"""
```

### 🏗️ **Constructor**

#### `CustomLDAPServer(storage_backend, bind_handler, debug=False)`

Creates a new custom LDAP protocol handler.

**Parameters:**
- `storage_backend`: Storage backend for directory data
- `bind_handler`: BindHandler instance for authentication
- `debug` (bool): Enable debug logging

**Example:**
```python
from ldap_server.factory import CustomLDAPServer
from ldap_server.auth.bind import BindHandler
from ldap_server.auth.password import PasswordManager

storage = MemoryStorage()
password_manager = PasswordManager()
bind_handler = BindHandler(storage, password_manager)

server = CustomLDAPServer(
    storage_backend=storage,
    bind_handler=bind_handler,
    debug=True
)
```

### 🔐 **Protocol Handlers**

#### `handle_LDAPBindRequest(request, reply)`

Processes LDAP bind requests (authentication).

**Parameters:**
- `request`: LDAPBindRequest from client
- `reply`: Callback function to send response

**LDAP Bind Types Supported:**
- **Anonymous Bind**: Empty DN and password
- **Simple Bind**: Username/password authentication

**Example Flow:**
```python
def handle_LDAPBindRequest(self, request, reply):
    # Extract credentials from request
    dn = str(request.dn)
    password = request.auth.password
    
    # Process through BindHandler
    response = self.bind_handler.handle_bind_request(dn, password)
    
    # Track authentication state
    if response.resultCode == 0:  # Success
        self.bound_dn = dn
        if self.debug:
            print(f"Successful bind: {dn}")
    else:
        self.bound_dn = None
        if self.debug:
            print(f"Failed bind: {dn}")
    
    # Send response to client
    reply(response)
```

#### `handle_LDAPSearchRequest(request, reply)`

Processes LDAP search requests.

**Parameters:**
- `request`: LDAPSearchRequest from client
- `reply`: Callback function to send response

**Search Features:**
- **Base DN**: Starting point for search
- **Scope**: base, one-level, subtree (Phase 1: base only)
- **Filter**: LDAP filter expression (Phase 1: basic)
- **Attributes**: Requested attributes

**Example Flow:**
```python
def handle_LDAPSearchRequest(self, request, reply):
    # Extract search parameters
    base_dn = str(request.baseObject)
    scope = request.scope
    filter_expr = request.filter
    attributes = request.attributes
    
    # Check authentication for search access
    if not self._check_search_permission(base_dn):
        reply(LDAPSearchResultDone(resultCode=50))  # Insufficient Access
        return
    
    # Perform search via storage backend
    try:
        entries = self.storage_backend.search(
            base_dn=base_dn,
            scope=scope,
            filter=filter_expr,
            attributes=attributes
        )
        
        # Send search result entries
        for entry in entries:
            reply(LDAPSearchResultEntry(entry))
        
        # Send search completion
        reply(LDAPSearchResultDone(resultCode=0))
        
    except Exception as e:
        if self.debug:
            print(f"Search error: {e}")
        reply(LDAPSearchResultDone(resultCode=1))  # Operations Error
```

### 🔌 **Connection Lifecycle**

#### `connectionMade()`

Called when a client establishes a connection.

**Behavior:**
- Initializes connection state
- Sets up per-connection variables
- Logs connection if debug enabled

**Example:**
```python
def connectionMade(self):
    super().connectionMade()
    self.bound_dn = None  # No authentication yet
    self.connection_id = id(self)
    
    if self.debug:
        client_addr = self.transport.getPeer()
        print(f"Client connected: {client_addr.host}:{client_addr.port}")
```

#### `connectionLost(reason)`

Called when a client disconnects.

**Parameters:**
- `reason`: Twisted disconnect reason

**Behavior:**
- Cleans up connection state
- Logs disconnection if debug enabled
- Updates connection tracking

**Example:**
```python
def connectionLost(self, reason):
    if self.debug:
        print(f"Client disconnected: {reason.getErrorMessage()}")
    
    # Clean up connection state
    self.bound_dn = None
    
    super().connectionLost(reason)
```

## 🔄 **Protocol Flow**

### Connection Establishment
```
Client                    CustomLDAPServer
  │                              │
  ├─ TCP Connection ──────────→  │ connectionMade()
  │                              │ ├─ Initialize state
  │                              │ ├─ bound_dn = None
  │                              │ └─ Setup logging
  │                              │
```

### LDAP Bind Operation
```
Client                    CustomLDAPServer
  │                              │
  ├─ LDAPBindRequest ──────────→ │ handle_LDAPBindRequest()
  │   dn: cn=user,dc=example,dc=com │ ├─ Extract credentials
  │   password: "secret"         │ ├─ Call bind_handler.handle_bind_request()
  │                              │ ├─ Update bound_dn on success
  │                              │ └─ Generate LDAPBindResponse
  │ ←─────────── LDAPBindResponse ┤
  │   resultCode: 0 (Success)    │
  │                              │
```

### LDAP Search Operation
```
Client                    CustomLDAPServer
  │                              │
  ├─ LDAPSearchRequest ────────→ │ handle_LDAPSearchRequest()
  │   baseObject: dc=example,dc=com │ ├─ Check authentication
  │   scope: base               │ ├─ Validate search parameters
  │   filter: (objectClass=*)   │ ├─ Call storage_backend.search()
  │                              │ ├─ Send LDAPSearchResultEntry(s)
  │                              │ └─ Send LDAPSearchResultDone
  │ ←─── LDAPSearchResultEntry   ┤
  │ ←─── LDAPSearchResultDone    ┤
  │   resultCode: 0 (Success)    │
  │                              │
```

## 🛡️ **Security Features**

### Authentication State
- **Per-Connection**: Each connection tracks its own authentication
- **bound_dn**: Stores authenticated user DN
- **Access Control**: Operations check authentication state

### Permission Checking
```python
def _check_search_permission(self, base_dn: str) -> bool:
    """Check if current user can search base DN"""
    
    # Anonymous users can only search if allowed
    if self.bound_dn is None:
        return self.allow_anonymous_search
    
    # Authenticated users have broader access
    # Future: Implement fine-grained ACLs
    return True

def _check_modify_permission(self, target_dn: str) -> bool:
    """Check if current user can modify target DN"""
    
    # Modifications require authentication
    if self.bound_dn is None:
        return False
    
    # Future: Check specific modify permissions
    return True
```

### Error Handling
- **Input Validation**: Validate all LDAP requests
- **Exception Handling**: Graceful error responses
- **Information Disclosure**: Prevent data leakage in errors

## 🧪 **Testing**

### Unit Tests

The factory and protocol are tested in `tests/unit/test_server.py`:

```python
def test_factory_creation():
    """Test LDAPServerFactory initialization"""
    storage = MemoryStorage()
    factory = LDAPServerFactory(storage_backend=storage, debug=True)
    
    assert factory.storage_backend == storage
    assert factory.debug is True
    assert factory.get_connection_count() == 0

def test_protocol_creation():
    """Test CustomLDAPServer creation via factory"""
    storage = MemoryStorage()
    factory = LDAPServerFactory(storage_backend=storage)
    
    # Simulate Twisted creating protocol
    protocol = factory.buildProtocol(None)
    
    assert isinstance(protocol, CustomLDAPServer)
    assert protocol.storage_backend == storage
    assert protocol.bound_dn is None

def test_bind_request_handling():
    """Test LDAP bind request processing"""
    # Setup
    storage = MemoryStorage()
    factory = LDAPServerFactory(storage_backend=storage)
    protocol = factory.buildProtocol(None)
    
    # Create mock bind request
    from ldaptor.protocols.ldap import pureldap
    request = pureldap.LDAPBindRequest(
        dn='cn=admin,dc=example,dc=com',
        auth=pureldap.LDAPBindRequest_auth_simple('admin')
    )
    
    # Test bind handling
    responses = []
    def reply(response):
        responses.append(response)
    
    protocol.handle_LDAPBindRequest(request, reply)
    
    assert len(responses) == 1
    assert responses[0].resultCode == 0  # Success
```

### Integration Tests

```python
def test_full_ldap_session():
    """Test complete LDAP client session"""
    import ldap
    
    # Start server
    storage = MemoryStorage()
    factory = LDAPServerFactory(storage_backend=storage)
    # ... start server with factory
    
    # Connect with LDAP client
    conn = ldap.initialize('ldap://localhost:1389')
    
    # Test anonymous bind
    result = conn.simple_bind_s('', '')
    assert result[0] == 97  # Bind response
    
    # Test search
    results = conn.search_s(
        'dc=example,dc=com',
        ldap.SCOPE_BASE,
        '(objectClass=*)'
    )
    assert len(results) > 0
    
    # Test authenticated bind
    result = conn.simple_bind_s(
        'cn=admin,dc=example,dc=com',
        'admin'
    )
    assert result[0] == 97  # Bind response
```

## 🚀 **Usage Examples**

### Basic Factory Setup

```python
from ldap_server.factory import LDAPServerFactory
from ldap_server.storage.memory import MemoryStorage
from twisted.internet import reactor

# Create factory
storage = MemoryStorage()
factory = LDAPServerFactory(storage_backend=storage, debug=True)

# Start listening
reactor.listenTCP(1389, factory, interface='localhost')
print("LDAP server listening on localhost:1389")

# Run reactor
reactor.run()
```

### Factory with Custom Protocol

```python
from ldap_server.factory import LDAPServerFactory, CustomLDAPServer

class ExtendedLDAPServer(CustomLDAPServer):
    """Extended LDAP server with custom operations"""
    
    def handle_LDAPSearchRequest(self, request, reply):
        # Add custom search logic
        print(f"Search request: {request.baseObject}")
        
        # Call parent implementation
        super().handle_LDAPSearchRequest(request, reply)

class ExtendedLDAPServerFactory(LDAPServerFactory):
    """Factory that creates extended LDAP servers"""
    
    def buildProtocol(self, addr):
        protocol = ExtendedLDAPServer(
            storage_backend=self.storage_backend,
            bind_handler=self.bind_handler,
            debug=self.debug
        )
        protocol.factory = self
        return protocol

# Use extended factory
factory = ExtendedLDAPServerFactory(storage_backend=storage)
```

### Production Factory Configuration

```python
from ldap_server.factory import LDAPServerFactory
from ldap_server.storage.json import JSONStorage
from ldap_server.auth.bind import BindHandler
from ldap_server.auth.password import PasswordManager

def create_production_factory():
    # Initialize components
    storage = JSONStorage(json_file='/etc/ldap/directory.json')
    password_manager = PasswordManager(rounds=14)  # High security
    bind_handler = BindHandler(storage, password_manager)
    
    # Create factory
    factory = LDAPServerFactory(
        storage_backend=storage,
        debug=False  # Disable debug in production
    )
    
    return factory

# Production setup
factory = create_production_factory()
reactor.listenTCP(389, factory, interface='0.0.0.0')
```

## 📋 **Error Handling**

### Protocol Error Responses

```python
# Common LDAP error responses
LDAP_ERRORS = {
    'success': 0,
    'operations_error': 1,
    'protocol_error': 2,
    'time_limit_exceeded': 3,
    'size_limit_exceeded': 4,
    'compare_false': 5,
    'compare_true': 6,
    'auth_method_not_supported': 7,
    'stronger_auth_required': 8,
    'partial_results': 9,
    'referral': 10,
    'admin_limit_exceeded': 11,
    'unavailable_critical_extension': 12,
    'confidentiality_required': 13,
    'sasl_bind_in_progress': 14,
    'no_such_attribute': 16,
    'undefined_attribute_type': 17,
    'inappropriate_matching': 18,
    'constraint_violation': 19,
    'attribute_or_value_exists': 20,
    'invalid_attribute_syntax': 21,
    'no_such_object': 32,
    'alias_problem': 33,
    'invalid_dn_syntax': 34,
    'is_leaf': 35,
    'alias_dereferencing_problem': 36,
    'inappropriate_authentication': 48,
    'invalid_credentials': 49,
    'insufficient_access_rights': 50,
    'busy': 51,
    'unavailable': 52,
    'unwilling_to_perform': 53,
    'loop_detect': 54,
    'naming_violation': 64,
    'object_class_violation': 65,
    'not_allowed_on_non_leaf': 66,
    'not_allowed_on_rdn': 67,
    'entry_already_exists': 68,
    'object_class_mods_prohibited': 69,
    'affects_multiple_dsas': 71,
    'other': 80
}
```

### Exception Handling

```python
def handle_LDAPSearchRequest(self, request, reply):
    """Search request with comprehensive error handling"""
    try:
        # Validate request
        if not self._validate_search_request(request):
            reply(LDAPSearchResultDone(resultCode=2))  # Protocol Error
            return
        
        # Check permissions
        if not self._check_search_permission(str(request.baseObject)):
            reply(LDAPSearchResultDone(resultCode=50))  # Insufficient Access
            return
        
        # Perform search
        results = self.storage_backend.search(...)
        
        # Send results
        for entry in results:
            reply(LDAPSearchResultEntry(entry))
        reply(LDAPSearchResultDone(resultCode=0))
        
    except ValueError as e:
        # Invalid search parameters
        if self.debug:
            print(f"Search validation error: {e}")
        reply(LDAPSearchResultDone(resultCode=2))  # Protocol Error
        
    except PermissionError:
        # Access denied
        reply(LDAPSearchResultDone(resultCode=50))  # Insufficient Access
        
    except Exception as e:
        # Unexpected error
        if self.debug:
            print(f"Search error: {e}")
        reply(LDAPSearchResultDone(resultCode=1))  # Operations Error
```

## 🔄 **Future Enhancements** (Phase 2+)

### Advanced Protocol Features
- **LDAP Modify Operations**: Add, modify, delete entries
- **LDAP Compare Operations**: Attribute value comparison
- **Extended Operations**: Custom LDAP extensions
- **Referrals**: Multi-server directory support

### Performance Optimizations
- **Connection Pooling**: Reuse connections efficiently
- **Request Caching**: Cache frequent search results
- **Async Operations**: Non-blocking request processing
- **Batch Operations**: Process multiple requests together

### Security Enhancements
- **SASL Authentication**: Advanced authentication methods
- **TLS Support**: Encrypted LDAP connections (LDAPS)
- **Access Control Lists**: Fine-grained permissions
- **Audit Logging**: Security event tracking

### Monitoring and Management
- **Connection Metrics**: Track connection statistics
- **Performance Monitoring**: Request timing and throughput
- **Health Checks**: Server health and status monitoring
- **Admin Operations**: Management interface

## 🔗 **Integration Points**

### With LDAPServerService
```python
# Server creates and manages factory
class LDAPServerService:
    def start(self):
        self.factory = LDAPServerFactory(
            storage_backend=self.storage_backend,
            debug=self.debug
        )
        reactor.listenTCP(self.port, self.factory)
```

### With Twisted Reactor
```python
# Factory integrates with Twisted networking
from twisted.internet import reactor

reactor.listenTCP(port, factory, interface=bind_host)
reactor.run()  # Start event loop
```

### With Storage Backends
```python
# Factory passes storage to each protocol instance
def buildProtocol(self, addr):
    protocol = CustomLDAPServer(
        storage_backend=self.storage_backend,  # Shared storage
        bind_handler=self.bind_handler,
        debug=self.debug
    )
    return protocol
```

## 📚 **Related Documentation**

- **[🎛️ Server API](server.md)** - LDAPServerService main server class
- **[🔐 Authentication](auth/README.md)** - BindHandler integration
- **[💾 Storage](storage/README.md)** - Storage backend integration
- **[🏗️ Architecture Guide](../development/architecture.md)** - System design overview
- **[🧪 Testing Guide](../development/testing.md)** - Testing protocol components

---

**Component**: Server Factory & Protocol  
**Phase**: 1 (Complete)  
**Last Updated**: September 7, 2025

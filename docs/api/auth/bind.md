# Bind Operations API

This document covers the `BindHandler` class and LDAP bind operation processing in py-ldap-server.

## 🔑 **BindHandler Class**

The `BindHandler` class processes LDAP bind requests and manages authentication for the LDAP server.

### Class Definition

```python
class BindHandler:
    """Handles LDAP bind operations and authentication"""
    
    def __init__(self, storage_backend, password_manager: PasswordManager):
        """Initialize with storage and password manager"""
        
    def handle_bind_request(self, dn: str, password: str) -> LDAPBindResponse:
        """Process LDAP bind request"""
        
    def authenticate_user(self, dn: str, password: str) -> bool:
        """Authenticate user credentials"""
        
    def get_user_entry(self, dn: str) -> Optional[dict]:
        """Retrieve user entry from storage"""
```

### 🏗️ **Constructor**

#### `BindHandler(storage_backend, password_manager)`

Creates a new bind handler instance.

**Parameters:**
- `storage_backend`: Storage backend instance (MemoryStorage, JSONStorage, etc.)
- `password_manager`: PasswordManager instance for password verification

**Example:**
```python
from ldap_server.auth.bind import BindHandler
from ldap_server.auth.password import PasswordManager
from ldap_server.storage.memory import MemoryStorage

storage = MemoryStorage()
password_manager = PasswordManager(rounds=12)
bind_handler = BindHandler(storage, password_manager)
```

### 🔐 **Methods**

#### `handle_bind_request(dn: str, password: str) -> LDAPBindResponse`

Processes an LDAP bind request and returns appropriate response.

**Parameters:**
- `dn` (str): Distinguished Name of user attempting to bind
- `password` (str): Password provided by client

**Returns:**
- `LDAPBindResponse`: LDAP protocol response object

**LDAP Result Codes:**
- `0` (Success): Authentication successful
- `49` (Invalid Credentials): Authentication failed
- `32` (No Such Object): User DN not found
- `2` (Protocol Error): Malformed request

**Example:**
```python
bind_handler = BindHandler(storage, password_manager)

# Successful bind
response = bind_handler.handle_bind_request(
    dn="cn=admin,dc=example,dc=com",
    password="admin_password"
)
print(response.resultCode)  # 0 (Success)

# Failed bind
response = bind_handler.handle_bind_request(
    dn="cn=admin,dc=example,dc=com", 
    password="wrong_password"
)
print(response.resultCode)  # 49 (Invalid Credentials)
```

#### `authenticate_user(dn: str, password: str) -> bool`

Authenticates user credentials against stored password hash.

**Parameters:**
- `dn` (str): Distinguished Name of user
- `password` (str): Plain text password to verify

**Returns:**
- `bool`: `True` if authentication successful, `False` otherwise

**Authentication Flow:**
1. Retrieve user entry from storage backend
2. Extract password hash from `userPassword` attribute
3. Verify password using PasswordManager
4. Return authentication result

**Example:**
```python
# Authenticate user
is_authenticated = bind_handler.authenticate_user(
    dn="cn=user,dc=example,dc=com",
    password="user_password"
)

if is_authenticated:
    print("User authenticated successfully")
else:
    print("Authentication failed")
```

#### `get_user_entry(dn: str) -> Optional[dict]`

Retrieves user entry from storage backend.

**Parameters:**
- `dn` (str): Distinguished Name of user

**Returns:**
- `Optional[dict]`: User entry dictionary or `None` if not found

**Example:**
```python
user_entry = bind_handler.get_user_entry("cn=admin,dc=example,dc=com")
if user_entry:
    print(f"User found: {user_entry['cn']}")
    print(f"Object classes: {user_entry['objectClass']}")
else:
    print("User not found")
```

## 🔄 **LDAP Bind Process Flow**

### Standard Bind Sequence

```
Client                    Server (BindHandler)
  │                              │
  ├─ LDAPBindRequest ──────────→ │
  │   dn: cn=user,dc=example,dc=com │ 1. Validate DN format
  │   password: "user_pass"      │ 2. Lookup user in storage
  │                              │ 3. Verify password hash
  │                              │ 4. Generate response
  │ ←─────────── LDAPBindResponse ┤
  │   resultCode: 0 (Success)    │
  │                              │
```

### Anonymous Bind Sequence

```
Client                    Server (BindHandler)
  │                              │
  ├─ LDAPBindRequest ──────────→ │
  │   dn: ""                    │ 1. Detect empty DN
  │   password: ""              │ 2. Allow anonymous access
  │                              │ 3. Set anonymous context
  │ ←─────────── LDAPBindResponse ┤
  │   resultCode: 0 (Success)    │
  │                              │
```

## 🛡️ **Security Features**

### Authentication Security
- **Password Verification**: Uses bcrypt for secure hash comparison
- **Timing Attack Protection**: Constant-time password verification
- **DN Validation**: Proper LDAP DN format validation
- **Error Handling**: Secure error messages (no information leakage)

### Access Control
- **Anonymous Bind**: Configurable anonymous access
- **Simple Bind**: Username/password authentication
- **Future**: SASL authentication methods (Phase 2+)

### Security Best Practices

```python
# Secure bind handling
class BindHandler:
    def authenticate_user(self, dn: str, password: str) -> bool:
        try:
            # Always perform lookup to prevent timing attacks
            user_entry = self.get_user_entry(dn)
            
            if not user_entry:
                # Still verify against dummy hash to prevent timing
                self.password_manager.verify_password(
                    password, 
                    "$2b$12$dummy.hash.to.prevent.timing.attacks"
                )
                return False
            
            # Verify actual password
            stored_hash = user_entry.get('userPassword', '')
            return self.password_manager.verify_password(password, stored_hash)
            
        except Exception:
            # Never leak internal errors
            return False
```

## 🧪 **Testing**

### Unit Tests

The bind handler is tested in `tests/unit/test_bind.py`:

```python
def test_successful_authentication():
    """Test successful LDAP bind"""
    storage = MemoryStorage()
    pm = PasswordManager()
    bind_handler = BindHandler(storage, pm)
    
    # Test valid credentials
    response = bind_handler.handle_bind_request(
        dn="cn=admin,dc=example,dc=com",
        password="admin"
    )
    
    assert response.resultCode == 0  # Success

def test_failed_authentication():
    """Test failed LDAP bind"""
    bind_handler = BindHandler(storage, pm)
    
    # Test invalid credentials
    response = bind_handler.handle_bind_request(
        dn="cn=admin,dc=example,dc=com",
        password="wrong_password"
    )
    
    assert response.resultCode == 49  # Invalid Credentials

def test_nonexistent_user():
    """Test bind with non-existent user"""
    response = bind_handler.handle_bind_request(
        dn="cn=missing,dc=example,dc=com",
        password="any_password"
    )
    
    assert response.resultCode == 49  # Invalid Credentials (not 32)

def test_anonymous_bind():
    """Test anonymous bind"""
    response = bind_handler.handle_bind_request(dn="", password="")
    assert response.resultCode == 0  # Success
```

### Test Coverage
- ✅ Successful authentication with valid credentials
- ✅ Failed authentication with invalid credentials
- ✅ Non-existent user handling
- ✅ Anonymous bind support
- ✅ Malformed DN handling
- ✅ Security timing considerations

## 🔧 **Configuration**

### Server Integration

```python
from ldap_server.server import LDAPServerService
from ldap_server.auth.bind import BindHandler

# Server automatically creates BindHandler
server = LDAPServerService(
    port=1389,
    bind_host='localhost',
    storage=storage,
    allow_anonymous=True,  # Configure anonymous access
    debug=True
)
```

### Authentication Policies

```python
# Configure bind handler policies
bind_handler = BindHandler(
    storage_backend=storage,
    password_manager=password_manager,
    allow_anonymous=True,      # Allow anonymous binds
    require_secure=False,      # Require TLS for binds (future)
    max_bind_attempts=3        # Rate limiting (future)
)
```

## 🚀 **Usage Examples**

### Basic Authentication

```python
from ldap_server.auth.bind import BindHandler
from ldap_server.auth.password import PasswordManager
from ldap_server.storage.memory import MemoryStorage

# Setup components
storage = MemoryStorage()
password_manager = PasswordManager()
bind_handler = BindHandler(storage, password_manager)

# Authenticate user
dn = "cn=user,dc=example,dc=com"
password = "user_password"

response = bind_handler.handle_bind_request(dn, password)

if response.resultCode == 0:
    print("Authentication successful")
    # Proceed with LDAP operations
else:
    print(f"Authentication failed: {response.resultCode}")
    # Handle authentication error
```

### Integration with LDAP Server

```python
# CustomLDAPServer uses BindHandler
class CustomLDAPServer(LDAPServer):
    def __init__(self, storage_backend, bind_handler):
        super().__init__()
        self.storage_backend = storage_backend
        self.bind_handler = bind_handler
        self.bound_dn = None  # Track authenticated user
    
    def handle_LDAPBindRequest(self, request, reply):
        """Handle LDAP bind requests"""
        dn = str(request.dn)
        password = request.auth.password
        
        # Process bind through BindHandler
        response = self.bind_handler.handle_bind_request(dn, password)
        
        if response.resultCode == 0:
            self.bound_dn = dn  # Store authenticated DN
            
        reply(response)
```

### Anonymous vs Authenticated Access

```python
def check_access_permissions(bound_dn: Optional[str], operation: str) -> bool:
    """Check if user has permission for operation"""
    
    if bound_dn is None:
        # Anonymous user - read-only access
        return operation in ['search', 'compare']
    else:
        # Authenticated user - full access
        return True

# Usage in LDAP operations
if check_access_permissions(self.bound_dn, 'modify'):
    # Allow modify operation
    return process_modify_request(request)
else:
    # Return insufficient access rights
    return LDAPResult(resultCode=50)  # Insufficient Access Rights
```

## 📋 **Error Handling**

### LDAP Result Codes

The bind handler returns standard LDAP result codes:

| Code | Constant | Description | When Used |
|------|----------|-------------|-----------|
| 0 | Success | Authentication successful | Valid credentials |
| 2 | Protocol Error | Malformed request | Invalid bind format |
| 32 | No Such Object | User not found | Non-existent DN |
| 49 | Invalid Credentials | Authentication failed | Wrong password or DN |

### Error Response Examples

```python
# Successful bind
LDAPBindResponse(resultCode=0, matchedDN='', errorMessage='')

# Invalid credentials
LDAPBindResponse(
    resultCode=49, 
    matchedDN='', 
    errorMessage='Invalid credentials'
)

# Protocol error
LDAPBindResponse(
    resultCode=2,
    matchedDN='',
    errorMessage='Invalid bind request format'
)
```

## 🔄 **Future Enhancements** (Phase 2+)

### SASL Authentication
- DIGEST-MD5 authentication
- GSSAPI/Kerberos integration
- EXTERNAL authentication for TLS client certificates

### Enhanced Security
- Rate limiting for failed bind attempts
- Account lockout policies
- Password policy enforcement
- Audit logging for authentication events

### Performance Optimizations
- Authentication result caching
- Connection pooling for backend storage
- Async authentication processing

### Advanced Features
- Multi-domain authentication
- LDAP proxy authentication
- SSO integration capabilities

## 🔗 **Integration Points**

### With CustomLDAPServer
```python
class CustomLDAPServer(LDAPServer):
    def handle_LDAPBindRequest(self, request, reply):
        response = self.bind_handler.handle_bind_request(...)
        reply(response)
```

### With Storage Backends
```python
# BindHandler works with any storage backend
memory_bind = BindHandler(MemoryStorage(), password_manager)
json_bind = BindHandler(JSONStorage(), password_manager)
```

### With Password Manager
```python
# BindHandler delegates password verification
class BindHandler:
    def authenticate_user(self, dn, password):
        stored_hash = self.get_user_password(dn)
        return self.password_manager.verify_password(password, stored_hash)
```

## 📚 **Related Documentation**

- **[🔒 Password Management](password.md)** - Password hashing and verification
- **[📁 Authentication Overview](README.md)** - Complete authentication system
- **[🖥️ Server API](../server.md)** - Main server class integration
- **[🏭 Factory API](../factory.md)** - LDAP server factory and protocol handler
- **[🧪 Testing Guide](../../development/testing.md)** - Testing authentication flows

---

**Component**: Bind Operations  
**Phase**: 1 (Complete)  
**Last Updated**: September 7, 2025

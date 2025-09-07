# Authentication System Documentation

The authentication system in py-ldap-server provides secure user authentication for LDAP operations. This system is designed to be extensible, supporting multiple authentication methods while maintaining security best practices.

## 🏗️ **Architecture Overview**

```
auth/
├── password.py         # PasswordManager - secure password handling
└── bind.py            # BindHandler - LDAP bind operation processing
```

The authentication system follows a two-layer approach:
1. **Password Management**: Secure hashing, verification, and upgrade utilities
2. **Bind Handling**: LDAP protocol bind operation processing

## 🔐 **Authentication Components**

### 🔒 **PasswordManager** (`password.py`)
Handles all password-related security operations:
- **bcrypt Hashing**: Secure password hashing with configurable rounds
- **Password Verification**: Constant-time password comparison
- **Legacy Support**: Backward compatibility with plain-text passwords
- **Secure Generation**: Cryptographically secure password generation

### 🔑 **BindHandler** (`bind.py`)
Processes LDAP bind requests:
- **Anonymous Bind**: No authentication required
- **Simple Bind**: Username/password authentication
- **Error Handling**: Proper LDAP error responses
- **Integration**: Seamless storage backend integration

## 🎯 **Supported Authentication Methods**

### ✅ **Currently Implemented**

#### Anonymous Bind
```python
# No credentials required
bind_dn = ""
password = ""
# Allows read-only access to directory
```

#### Simple Bind
```python
# Username and password authentication
bind_dn = "cn=admin,dc=example,dc=com"
password = "secure_password"
# Full access based on user permissions
```

### 🚧 **Future Authentication Methods** (Phase 3)

#### UPN Authentication
```python
# Active Directory style authentication
bind_dn = "user@example.com"
password = "secure_password"
# Support for user principal name format
```

#### SASL Authentication
```python
# Advanced authentication mechanisms
# Kerberos, DIGEST-MD5, EXTERNAL
```

## 🔒 **Security Features**

### 🛡️ **Password Security**
- **bcrypt Hashing**: Industry-standard password hashing
- **Configurable Rounds**: Adjustable computational cost (default: 12)
- **Salt Generation**: Unique salt for each password
- **Timing Attack Protection**: Constant-time comparison

### 🔄 **Password Upgrade System**
Automatic upgrade from legacy passwords:
```python
# Legacy plain-text password
"plain_password"

# Automatically upgraded to
"$2b$12$XxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXxXx"
```

### 🔍 **Security Validation**
- **Input Sanitization**: Prevent injection attacks
- **Rate Limiting**: Protection against brute force *(Phase 3)*
- **Audit Logging**: Track authentication attempts *(Phase 3)*

## 📚 **API Reference**

### PasswordManager Class

#### Core Methods
```python
class PasswordManager:
    def hash_password(self, password: str, rounds: int = 12) -> str:
        """Hash password using bcrypt with specified rounds."""
        
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash with timing attack protection."""
        
    def generate_secure_password(self, length: int = 16) -> str:
        """Generate cryptographically secure random password."""
        
    def upgrade_plain_passwords(self, data: dict) -> dict:
        """Upgrade plain-text passwords to bcrypt hashes."""
```

#### Usage Examples
```python
from ldap_server.auth.password import PasswordManager

pm = PasswordManager()

# Hash a new password
hashed = pm.hash_password("user_password")

# Verify password
is_valid = pm.verify_password("user_password", hashed)

# Generate secure password
new_password = pm.generate_secure_password(length=20)
```

### BindHandler Class

#### Core Methods
```python
class BindHandler:
    def handle_bind(self, dn: str, password: str, storage) -> bool:
        """Process LDAP bind request with authentication."""
        
    def _anonymous_bind(self, dn: str, password: str) -> bool:
        """Handle anonymous bind (empty DN and password)."""
        
    def _simple_bind(self, dn: str, password: str, storage) -> bool:
        """Handle simple bind with DN and password."""
```

#### Integration Example
```python
from ldap_server.auth.bind import BindHandler
from ldap_server.storage.memory import MemoryStorage

handler = BindHandler()
storage = MemoryStorage()

# Process bind request
success = handler.handle_bind(
    dn="cn=admin,dc=example,dc=com",
    password="admin_password",
    storage=storage
)
```

## 🧪 **Testing**

### 🔬 **Test Coverage**
The authentication system has comprehensive test coverage:
- **Password Management**: 16 test cases covering all security scenarios
- **Bind Operations**: 13 test cases covering LDAP bind scenarios
- **Integration Tests**: Cross-component authentication testing

### 🧪 **Test Examples**
```python
def test_password_hashing():
    """Test secure password hashing."""
    pm = PasswordManager()
    password = "test_password"
    hashed = pm.hash_password(password)
    
    assert hashed.startswith("$2b$")
    assert pm.verify_password(password, hashed)

def test_simple_bind_success():
    """Test successful LDAP simple bind."""
    handler = BindHandler()
    storage = MemoryStorage()
    
    result = handler.handle_bind(
        dn="cn=admin,dc=example,dc=com",
        password="admin",
        storage=storage
    )
    assert result is True
```

## ⚙️ **Configuration**

### 🔧 **Password Security Settings**
```python
# Default configuration
PASSWORD_ROUNDS = 12        # bcrypt rounds (computational cost)
MIN_PASSWORD_LENGTH = 8     # Minimum password length
SECURE_PASSWORD_LENGTH = 16 # Default generated password length

# High security configuration
PASSWORD_ROUNDS = 15        # Higher computational cost
MIN_PASSWORD_LENGTH = 12    # Longer minimum length
```

### 🛡️ **Authentication Policies**
```python
# Authentication settings
ANONYMOUS_BIND_ENABLED = True   # Allow anonymous access
REQUIRE_AUTHENTICATION = False  # Require auth for all operations
BIND_TIMEOUT = 30              # Bind operation timeout (seconds)
```

## 🔄 **Integration Points**

### 💾 **Storage Integration**
Authentication integrates with storage backends:
```python
# Memory storage
storage = MemoryStorage()
user_entry = storage.get_entry_by_dn(bind_dn)
password_hash = user_entry.get_password()

# JSON storage
storage = JSONStorage("users.json")
user_data = storage.find_user_by_dn(bind_dn)
```

### 🖥️ **Server Integration**
Authentication is integrated into the LDAP server:
```python
class CustomLDAPServer(LDAPServer):
    def handle_LDAPBindRequest(self, request, controls, reply):
        """Handle LDAP bind with authentication."""
        handler = BindHandler()
        success = handler.handle_bind(
            dn=request.dn,
            password=request.auth,
            storage=self.factory.storage
        )
```

## 🚀 **Extension Points**

### 🔌 **Custom Authentication Methods**
Extend authentication for new methods:
```python
class CustomAuthenticator:
    def authenticate(self, dn: str, credentials: any) -> bool:
        """Custom authentication logic."""
        # Implement custom authentication
        return True

# Register custom authenticator
bind_handler.register_authenticator("custom", CustomAuthenticator())
```

### 🔑 **External Authentication**
Integrate with external authentication systems:
```python
class LDAPAuthenticator:
    def authenticate(self, dn: str, password: str) -> bool:
        """Authenticate against external LDAP."""
        # Connect to external LDAP server
        # Perform authentication
        return external_ldap.authenticate(dn, password)
```

## 📊 **Performance Considerations**

### ⚡ **Password Hashing Performance**
```python
# bcrypt rounds vs. performance
Rounds  | Time per hash | Security level
--------|---------------|---------------
10      | ~100ms       | Basic
12      | ~400ms       | Recommended (default)
15      | ~3200ms      | High security
```

### 🔄 **Caching Strategies** (Phase 3)
Future performance optimizations:
- **Authentication Cache**: Cache successful authentications
- **Password Hash Cache**: Cache bcrypt computations
- **Connection Pooling**: Reuse authentication state

## 🔗 **Related Documentation**

- **[🔒 Password API](password.md)** - Detailed PasswordManager documentation
- **[🔑 Bind API](bind.md)** - Detailed BindHandler documentation
- **[🛡️ Security Guide](../../deployment/security.md)** - Production security setup
- **[🧪 Testing Guide](../../development/testing.md)** - Authentication testing

---

**Authentication Status**: Phase 1 complete - Anonymous and simple bind implemented  
**Security Level**: Production-ready with bcrypt password hashing  
**Test Coverage**: 29 comprehensive test cases  
**Last Updated**: September 7, 2025

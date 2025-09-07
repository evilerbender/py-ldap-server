# Password Management API

This document covers the `PasswordManager` class and password security implementation in py-ldap-server.

## 🔒 **PasswordManager Class**

The `PasswordManager` class handles secure password hashing and verification for LDAP authentication.

### Class Definition

```python
class PasswordManager:
    """Secure password management using bcrypt hashing"""
    
    def __init__(self, rounds: int = 12):
        """Initialize with bcrypt rounds (default: 12)"""
        
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
```

### 🏗️ **Constructor**

#### `PasswordManager(rounds=12)`

Creates a new password manager instance.

**Parameters:**
- `rounds` (int): bcrypt hashing rounds (default: 12)
  - Higher values = more secure but slower
  - Recommended range: 10-15
  - Each increment doubles computation time

**Example:**
```python
from ldap_server.auth.password import PasswordManager

# Default security (12 rounds)
pm = PasswordManager()

# High security (15 rounds)
pm_secure = PasswordManager(rounds=15)

# Fast testing (10 rounds)
pm_test = PasswordManager(rounds=10)
```

### 🔐 **Methods**

#### `hash_password(password: str) -> str`

Generates a secure bcrypt hash for a password.

**Parameters:**
- `password` (str): Plain text password to hash

**Returns:**
- `str`: bcrypt hash string (includes salt and rounds)

**Security Features:**
- Uses cryptographically secure random salt
- Configurable bcrypt rounds
- Resistant to rainbow table attacks
- Compatible with standard bcrypt implementations

**Example:**
```python
pm = PasswordManager(rounds=12)
password_hash = pm.hash_password("user_password_123")
print(password_hash)
# Output: $2b$12$ABC123...DEF456 (60 characters)
```

**Hash Format:**
```
$2b$12$22charSalt.38charHash
│ │ │  │          │
│ │ │  │          └─ 38-char hash
│ │ │  └─ 22-char salt
│ │ └─ rounds (12)
│ └─ bcrypt variant (2b)
└─ bcrypt identifier
```

#### `verify_password(password: str, hashed: str) -> bool`

Verifies a plain text password against its hash.

**Parameters:**
- `password` (str): Plain text password to verify
- `hashed` (str): bcrypt hash to check against

**Returns:**
- `bool`: `True` if password matches, `False` otherwise

**Security Features:**
- Constant-time comparison (prevents timing attacks)
- Handles malformed hashes gracefully
- Works with any bcrypt rounds value

**Example:**
```python
pm = PasswordManager()
password = "user_password_123"
password_hash = pm.hash_password(password)

# Verify correct password
is_valid = pm.verify_password(password, password_hash)
print(is_valid)  # True

# Verify incorrect password
is_valid = pm.verify_password("wrong_password", password_hash)
print(is_valid)  # False
```

## 🛡️ **Security Features**

### Bcrypt Algorithm
- **Salt Generation**: Cryptographically secure random salts
- **Key Stretching**: Configurable rounds for future-proofing
- **Standard Compliance**: Compatible with RFC 2898 and bcrypt specification

### Attack Resistance
- **Rainbow Tables**: Each password has unique salt
- **Brute Force**: Configurable rounds increase computation cost
- **Timing Attacks**: Constant-time comparison in verification

### Performance Considerations
```python
# Rounds vs Security vs Performance
rounds_10 = PasswordManager(rounds=10)  # ~100ms hash time
rounds_12 = PasswordManager(rounds=12)  # ~400ms hash time  
rounds_15 = PasswordManager(rounds=15)  # ~3200ms hash time
```

## 🧪 **Testing**

### Unit Tests

The password manager is thoroughly tested in `tests/unit/test_password.py`:

```python
def test_password_hashing():
    """Test password hashing and verification"""
    pm = PasswordManager()
    password = "test_password_123"
    
    # Hash password
    hashed = pm.hash_password(password)
    assert isinstance(hashed, str)
    assert len(hashed) == 60  # Standard bcrypt length
    
    # Verify correct password
    assert pm.verify_password(password, hashed)
    
    # Verify incorrect password
    assert not pm.verify_password("wrong_password", hashed)

def test_different_rounds():
    """Test different bcrypt rounds"""
    pm10 = PasswordManager(rounds=10)
    pm12 = PasswordManager(rounds=12)
    
    password = "test_password"
    hash10 = pm10.hash_password(password)
    hash12 = pm12.hash_password(password)
    
    # Different rounds produce different hashes
    assert hash10 != hash12
    
    # Both verify correctly with their own manager
    assert pm10.verify_password(password, hash10)
    assert pm12.verify_password(password, hash12)
```

### Test Coverage
- ✅ Password hashing functionality
- ✅ Password verification (correct/incorrect)
- ✅ Different bcrypt rounds
- ✅ Edge cases (empty passwords, malformed hashes)
- ✅ Performance characteristics

## 🔧 **Configuration**

### Environment Variables

Configure password security via environment:

```bash
# Bcrypt rounds (default: 12)
export LDAP_PASSWORD_ROUNDS=14

# Enable password complexity requirements (future)
export LDAP_PASSWORD_POLICY=strict
```

### Runtime Configuration

```python
from ldap_server.auth.password import PasswordManager
import os

# Get rounds from environment
rounds = int(os.getenv('LDAP_PASSWORD_ROUNDS', 12))
pm = PasswordManager(rounds=rounds)
```

## 🚀 **Usage Examples**

### Basic Authentication Flow

```python
from ldap_server.auth.password import PasswordManager

# Initialize password manager
pm = PasswordManager(rounds=12)

# User registration (store hash in directory)
user_password = "secure_password_123"
password_hash = pm.hash_password(user_password)

# Store in LDAP entry
user_entry = {
    'dn': 'cn=user,dc=example,dc=com',
    'userPassword': password_hash,
    'cn': 'user'
}

# Authentication (verify submitted password)
submitted_password = "secure_password_123"
is_authenticated = pm.verify_password(submitted_password, password_hash)

if is_authenticated:
    print("Authentication successful")
else:
    print("Authentication failed")
```

### Integration with LDAP Server

```python
from ldap_server.server import LDAPServerService
from ldap_server.auth.password import PasswordManager

# Configure server with password manager
server = LDAPServerService(
    port=1389,
    bind_host='localhost',
    password_manager=PasswordManager(rounds=12)
)
```

## 🔗 **Integration Points**

### With BindHandler
The `PasswordManager` integrates with `BindHandler` for LDAP authentication:

```python
# BindHandler uses PasswordManager for verification
class BindHandler:
    def __init__(self, password_manager: PasswordManager):
        self.password_manager = password_manager
    
    def authenticate(self, dn: str, password: str) -> bool:
        # Get stored hash from directory
        stored_hash = self.get_user_password(dn)
        
        # Verify using PasswordManager
        return self.password_manager.verify_password(password, stored_hash)
```

### With Storage Backends
Password hashes are stored in the directory data structure:

```python
# Memory storage example
user_data = {
    'cn=admin,dc=example,dc=com': {
        'objectClass': ['person', 'organizationalPerson'],
        'cn': 'admin',
        'userPassword': '$2b$12$...',  # bcrypt hash
        'sn': 'Administrator'
    }
}
```

## 📋 **Error Handling**

### Exception Types

```python
# Password manager handles these gracefully:
try:
    is_valid = pm.verify_password(password, malformed_hash)
except ValueError as e:
    print(f"Invalid hash format: {e}")
    is_valid = False
```

### Common Issues

1. **Malformed Hash**: Returns `False` instead of raising
2. **Empty Password**: Hashes normally (some systems allow empty)
3. **Unicode Issues**: UTF-8 encoding handled automatically

## 🔄 **Future Enhancements** (Phase 2+)

### Password Policies
- Minimum length requirements
- Complexity requirements (uppercase, numbers, symbols)
- Password history and rotation
- Account lockout after failed attempts

### Additional Hash Methods
- Argon2 support for next-generation security
- LDAP-style SSHA hashes for compatibility
- Migration utilities between hash types

### Performance Optimizations
- Async password verification
- Caching for frequently accessed hashes
- Hardware acceleration support

## 📚 **Related Documentation**

- **[🔑 Bind Operations](bind.md)** - How passwords are used in LDAP bind
- **[📁 Authentication Overview](README.md)** - Complete authentication system
- **[🏗️ Architecture Guide](../../development/architecture.md)** - System design patterns
- **[🧪 Testing Guide](../../development/testing.md)** - Testing authentication components

---

**Component**: Password Management  
**Phase**: 1 (Complete)  
**Last Updated**: September 7, 2025

# Authentication Guide

This guide covers user authentication, password management, and security features in py-ldap-server.

## 🔐 **Authentication Overview**

py-ldap-server provides secure authentication with modern password security practices. The authentication system is designed to be secure by default while maintaining compatibility with standard LDAP clients.

### ✅ **Current Authentication Features**
- **Anonymous Bind**: No credentials required for read access
- **Simple Bind**: Username/password authentication with DN
- **Password Security**: bcrypt hashing with configurable rounds
- **Password Upgrade**: Automatic upgrade from plain text to bcrypt
- **Security Hardening**: Timing attack protection and input validation

### 🚧 **Planned Authentication Features** (Phase 3)
- **UPN Authentication**: Active Directory style (user@domain.com)
- **SASL Authentication**: Advanced authentication mechanisms
- **Certificate Authentication**: X.509 certificate-based authentication
- **Multi-Factor Authentication**: TOTP and other 2FA methods

## 🔑 **Authentication Methods**

### 🌐 **Anonymous Bind**
Anonymous access allows read-only operations without credentials:

```bash
# Anonymous LDAP search
ldapsearch -x -H ldap://localhost:1389 -b "dc=example,dc=com" "(objectClass=*)"

# No username or password required
# Read access to public directory information
```

**Use Cases:**
- **Public Directory**: Company phone directory
- **Service Discovery**: Finding available services
- **Development**: Quick testing without authentication setup

**Configuration:**
```python
# Enable/disable anonymous access
ANONYMOUS_BIND_ENABLED = True   # Default: enabled
```

### 🔐 **Simple Bind Authentication**
Standard LDAP authentication with username and password:

```bash
# Authenticate with DN and password
ldapsearch -x -H ldap://localhost:1389 \
    -D "cn=admin,ou=people,dc=example,dc=com" \
    -w "admin_password" \
    -b "dc=example,dc=com" "(cn=*)"

# Authentication flow:
# 1. Client sends bind request with DN and password
# 2. Server finds user entry by DN
# 3. Server verifies password against stored hash
# 4. Server returns success/failure response
```

**Supported DN Formats:**
```bash
# Common Name format
cn=username,ou=people,dc=example,dc=com

# User ID format  
uid=username,ou=people,dc=example,dc=com

# Email format (Phase 3)
mail=user@example.com,ou=people,dc=example,dc=com
```

## 👥 **User Management**

### 📝 **Creating User Accounts**

#### JSON Storage User Creation
Add users to your JSON directory file:

```json
{
  "entries": [
    {
      "dn": "cn=jdoe,ou=people,dc=example,dc=com",
      "objectClass": ["person", "organizationalPerson", "inetOrgPerson"],
      "cn": "jdoe",
      "sn": "Doe", 
      "givenName": "John",
      "displayName": "John Doe",
      "mail": "john.doe@example.com",
      "userPassword": "initial_password",
      "employeeNumber": "12345",
      "department": "Engineering",
      "title": "Software Engineer"
    }
  ]
}
```

**Password Handling:**
- **Plain Text**: Automatically upgraded to bcrypt on first server start
- **bcrypt Hash**: Used directly for authentication
- **Automatic Backup**: Original file backed up before password upgrade

#### Memory Storage User Creation
For development, users are pre-created in memory storage:

```python
# Default users in MemoryStorage
users = [
    ("cn=admin,ou=people,dc=example,dc=com", "admin"),
    ("cn=alice,ou=people,dc=example,dc=com", "alice123"),
    ("cn=bob,ou=people,dc=example,dc=com", "bob456")
]
```

### 🔒 **Password Security**

#### Password Hashing
All passwords use bcrypt hashing for security:

```python
from ldap_server.auth.password import PasswordManager

pm = PasswordManager()

# Hash a new password
hashed = pm.hash_password("user_password", rounds=12)
# Result: "$2b$12$salt_and_hash..."

# Verify password
is_valid = pm.verify_password("user_password", hashed)
# Result: True
```

#### Password Strength Requirements
```python
# Recommended password policies
MIN_PASSWORD_LENGTH = 12        # Minimum length
REQUIRE_MIXED_CASE = True       # Upper and lowercase
REQUIRE_NUMBERS = True          # At least one digit
REQUIRE_SPECIAL_CHARS = True    # Special characters
PASSWORD_HISTORY = 5            # Prevent reuse (Phase 3)
```

#### Secure Password Generation
```python
# Generate secure passwords
secure_password = pm.generate_secure_password(length=16)
# Result: "K7mN$qR9@vL3#xP6"

# Customizable character sets
import string
charset = string.ascii_letters + string.digits + "!@#$%^&*"
custom_password = pm.generate_secure_password(length=20, charset=charset)
```

### 🛡️ **Security Features**

#### Timing Attack Protection
Authentication has consistent timing to prevent timing attacks:

```python
def handle_bind(self, dn: str, password: str, storage) -> bool:
    """Handle bind with timing attack protection."""
    # Always perform same operations regardless of user existence
    user_entry = storage.find_entry_by_dn(dn)
    
    if user_entry:
        stored_password = user_entry.get_password()
        return self.password_manager.verify_password(password, stored_password)
    else:
        # Perform dummy verification to maintain consistent timing
        self.password_manager.verify_password(password, "$2b$12$dummy_hash")
        return False
```

#### Input Validation
All authentication inputs are validated:

```python
def validate_bind_request(dn: str, password: str) -> bool:
    """Validate bind request inputs."""
    # DN validation
    if not dn or len(dn) > 255:
        return False
    
    # Password validation
    if len(password) > 1024:  # Prevent memory exhaustion
        return False
    
    # Character validation
    if contains_control_characters(dn):
        return False
    
    return True
```

## 🔧 **Authentication Configuration**

### ⚙️ **Server Configuration**
```bash
# Basic authentication setup
py-ldap-server --port 1389 --storage json --storage-file users.json

# With authentication debugging
py-ldap-server --port 1389 --debug
```

### 📄 **JSON Configuration**
```json
{
  "base_dn": "dc=company,dc=com",
  "entries": [
    {
      "dn": "dc=company,dc=com",
      "objectClass": ["dcObject", "organization"],
      "o": "Company Inc",
      "dc": "company"
    },
    {
      "dn": "ou=people,dc=company,dc=com",
      "objectClass": ["organizationalUnit"],
      "ou": "people"
    },
    {
      "dn": "cn=admin,ou=people,dc=company,dc=com",
      "objectClass": ["person", "organizationalPerson"],
      "cn": "admin",
      "sn": "Administrator",
      "userPassword": "secure_admin_password",
      "mail": "admin@company.com"
    },
    {
      "dn": "cn=user1,ou=people,dc=company,dc=com", 
      "objectClass": ["person", "organizationalPerson"],
      "cn": "user1",
      "sn": "User",
      "givenName": "Test",
      "userPassword": "secure_user_password",
      "mail": "user1@company.com"
    }
  ]
}
```

### 🔒 **Security Configuration**
```python
# Authentication settings
AUTH_CONFIG = {
    "anonymous_bind_enabled": True,      # Allow anonymous access
    "require_authentication": False,    # Require auth for all operations
    "password_rounds": 12,              # bcrypt rounds (12-15 recommended)
    "bind_timeout": 30,                 # Authentication timeout (seconds)
    "max_bind_attempts": 5,             # Rate limiting (Phase 3)
    "audit_authentication": True        # Log auth attempts (Phase 3)
}
```

## 🧪 **Testing Authentication**

### ✅ **Authentication Tests**
```bash
# Test anonymous access
ldapsearch -x -H ldap://localhost:1389 -b "dc=example,dc=com" -s base

# Test successful authentication
ldapsearch -x -H ldap://localhost:1389 \
    -D "cn=admin,ou=people,dc=example,dc=com" \
    -w "admin" \
    -b "dc=example,dc=com" "(cn=*)"

# Test failed authentication (wrong password)
ldapsearch -x -H ldap://localhost:1389 \
    -D "cn=admin,ou=people,dc=example,dc=com" \
    -w "wrong_password" \
    -b "dc=example,dc=com" "(cn=*)"
# Expected: ldap_bind: Invalid credentials (49)

# Test non-existent user
ldapsearch -x -H ldap://localhost:1389 \
    -D "cn=nonexistent,ou=people,dc=example,dc=com" \
    -w "any_password" \
    -b "dc=example,dc=com" "(cn=*)"
# Expected: ldap_bind: Invalid credentials (49)
```

### 🐍 **Python Client Testing**
```python
import ldap3

# Test with Python ldap3 library
server = ldap3.Server('ldap://localhost:1389')

# Anonymous connection
conn = ldap3.Connection(server, auto_bind=True)
conn.search('dc=example,dc=com', '(objectClass=*)', search_scope=ldap3.BASE)
print(f"Anonymous search: {len(conn.entries)} entries")
conn.unbind()

# Authenticated connection
conn = ldap3.Connection(
    server, 
    user='cn=admin,ou=people,dc=example,dc=com', 
    password='admin',
    auto_bind=True
)
conn.search('ou=people,dc=example,dc=com', '(cn=*)')
print(f"Authenticated search: {len(conn.entries)} entries")
conn.unbind()
```

## 🔍 **Troubleshooting Authentication**

### 🐛 **Common Issues**

#### Authentication Always Fails
```bash
# Check user exists in directory
ldapsearch -x -H ldap://localhost:1389 -b "ou=people,dc=example,dc=com" "(cn=username)"

# Check password format in JSON
cat directory.json | jq '.entries[] | select(.cn == "username") | .userPassword'

# Enable debug logging
py-ldap-server --debug
# Look for authentication-related log messages
```

#### Password Not Upgraded
```bash
# Check if password is still plain text
cat directory.json | jq '.entries[] | .userPassword'

# Force password upgrade by restarting server
py-ldap-server --storage json --storage-file directory.json

# Check backup file was created
ls -la directory.json.backup
```

#### Connection Refused
```bash
# Check server is running
ps aux | grep py-ldap-server

# Check port binding
ss -tuln | grep 1389

# Test basic connectivity
telnet localhost 1389
```

### 📊 **Debug Authentication**
```python
# Enable authentication debugging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run server with debug mode
py-ldap-server --debug

# Debug output will show:
# - Bind requests received
# - User lookup attempts
# - Password verification results
# - Authentication success/failure
```

## 🌐 **Client Integration**

### 🔧 **Application Integration**

#### Apache Authentication
```apache
# /etc/apache2/sites-available/app.conf
<Location "/secure">
    AuthType Basic
    AuthName "Company Directory"
    AuthBasicProvider ldap
    AuthLDAPURL "ldap://localhost:1389/ou=people,dc=example,dc=com?cn?sub?(objectClass=person)"
    AuthLDAPBindDN "cn=admin,ou=people,dc=example,dc=com"
    AuthLDAPBindPassword "admin_password"
    Require valid-user
</Location>
```

#### Nginx Authentication
```nginx
# /etc/nginx/sites-available/app
location /secure {
    auth_ldap "Company Directory";
    auth_ldap_servers company_ldap;
    # ... rest of configuration
}

upstream company_ldap {
    server localhost:1389;
}
```

#### PAM Integration (Phase 3)
```bash
# /etc/pam.d/common-auth
auth [success=2 default=ignore] pam_ldap.so
auth [success=1 default=ignore] pam_unix.so

# /etc/ldap/ldap.conf
URI ldap://localhost:1389
BASE dc=example,dc=com
BINDDN cn=admin,ou=people,dc=example,dc=com
BINDPW admin_password
```

### 📱 **Modern Applications**

#### Single Sign-On (Phase 4)
```yaml
# SAML configuration (planned)
saml:
  identity_provider: py-ldap-server
  ldap_url: ldap://localhost:1389
  base_dn: ou=people,dc=example,dc=com
  bind_dn: cn=admin,ou=people,dc=example,dc=com
```

#### REST API Authentication (Phase 4)
```python
# JWT token generation with LDAP backend
def authenticate_user(username, password):
    """Authenticate user and return JWT token."""
    # LDAP authentication
    if ldap_authenticate(username, password):
        return generate_jwt_token(username)
    return None
```

## 🔐 **Security Best Practices**

### 🛡️ **Password Policies**
- **Minimum Length**: 12 characters or more
- **Complexity**: Mix of uppercase, lowercase, numbers, symbols
- **Rotation**: Regular password changes (90-180 days)
- **History**: Prevent reuse of recent passwords
- **Strength**: Use password strength meters

### 🔒 **Server Security**
- **TLS Encryption**: Use LDAPS in production (Phase 3)
- **Access Control**: Restrict network access to LDAP ports
- **Monitoring**: Log all authentication attempts
- **Rate Limiting**: Prevent brute force attacks
- **Regular Updates**: Keep server and dependencies updated

### 📊 **Monitoring Authentication**
```bash
# Monitor authentication attempts
journalctl -u py-ldap-server | grep "authentication"

# Failed authentication monitoring
journalctl -u py-ldap-server | grep "authentication failed"

# Successful authentication monitoring  
journalctl -u py-ldap-server | grep "authentication successful"
```

## 🔗 **Related Documentation**

- **[⚙️ Configuration Guide](configuration.md)** - Server configuration options
- **[🚀 Quick Start Guide](quick-start.md)** - Getting started with authentication
- **[🛡️ Security Guide](../deployment/security.md)** - Production security setup
- **[🔐 Authentication API](../api/auth/README.md)** - Technical authentication details

---

**Authentication Status**: Simple bind and anonymous access implemented (Phase 1)  
**Security Level**: Production-ready with bcrypt password hashing  
**Next Features**: UPN authentication and SASL support (Phase 3)  
**Last Updated**: September 7, 2025

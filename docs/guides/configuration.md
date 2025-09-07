# Configuration Guide

This guide covers all configuration options available in py-ldap-server, from basic setup to advanced production configurations.

## ⚙️ **Basic Configuration**

### 🚀 **Command Line Options**

py-ldap-server supports various command-line options for quick configuration:

```bash
# Basic server startup
py-ldap-server --port 1389 --bind-host localhost

# All available options
py-ldap-server --help
```

#### 📋 **Available Options**
```
Options:
  --port INTEGER           Port to bind LDAP server (default: 1389)
  --bind-host TEXT         Host address to bind (default: localhost)
  --storage [memory|json]  Storage backend type (default: memory)
  --storage-file TEXT      Storage file path (for JSON storage)
  --debug                  Enable debug mode with verbose logging
  --help                   Show this message and exit
```

#### 💡 **Common Usage Examples**
```bash
# Development server with debug logging
py-ldap-server --port 1389 --debug

# Production server with JSON storage
py-ldap-server --port 389 --bind-host 0.0.0.0 --storage json --storage-file /etc/ldap/directory.json

# Testing server on alternate port
py-ldap-server --port 3389 --bind-host 127.0.0.1
```

## 💾 **Storage Configuration**

### 🧠 **Memory Storage** (Default)
Perfect for development and testing:

```bash
# Explicit memory storage (default)
py-ldap-server --storage memory

# Memory storage comes with pre-loaded sample data
# No additional configuration needed
```

**Characteristics:**
- **Performance**: Fastest access (no I/O)
- **Persistence**: Data lost on restart
- **Memory Usage**: ~10MB for sample data
- **Use Cases**: Development, testing, demonstrations

### 📄 **JSON Storage**
File-based persistent storage:

```bash
# Basic JSON storage
py-ldap-server --storage json --storage-file directory.json

# With custom file location
py-ldap-server --storage json --storage-file /var/lib/ldap/company.json
```

**JSON File Format:**
```json
{
  "base_dn": "dc=company,dc=com",
  "entries": [
    {
      "dn": "dc=company,dc=com",
      "objectClass": ["dcObject", "organization"],
      "o": "Company Name",
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
      "userPassword": "$2b$12$hash...",
      "mail": "admin@company.com"
    }
  ]
}
```

**JSON Storage Features:**
- **Hot Reload**: Automatic file change detection
- **Password Upgrade**: Plain passwords automatically hashed
- **Backup Creation**: Automatic backups before upgrades
- **Error Handling**: Graceful handling of malformed files

## 🔐 **Security Configuration**

### 🔒 **Password Security**
Configure password hashing strength:

```python
# Default configuration (secure)
PASSWORD_ROUNDS = 12        # bcrypt rounds
MIN_PASSWORD_LENGTH = 8     # Minimum password length

# High security configuration
PASSWORD_ROUNDS = 15        # Higher computational cost
MIN_PASSWORD_LENGTH = 12    # Longer passwords required
```

### 🛡️ **Authentication Settings**
```python
# Authentication configuration
ANONYMOUS_BIND_ENABLED = True   # Allow anonymous access
REQUIRE_AUTHENTICATION = False  # Require auth for all ops
BIND_TIMEOUT = 30              # Bind operation timeout
```

### 📊 **Security Best Practices**
- **Use bcrypt hashing**: Automatically enabled for all passwords
- **Strong passwords**: Minimum 12 characters for production
- **Regular updates**: Keep dependencies updated
- **Access control**: Restrict network access to LDAP port
- **TLS encryption**: Enable LDAPS in production (Phase 3)

## 🌐 **Network Configuration**

### 🔌 **Port and Binding**
```bash
# Standard LDAP port (requires root)
sudo py-ldap-server --port 389 --bind-host 0.0.0.0

# Non-privileged port for development
py-ldap-server --port 1389 --bind-host localhost

# Listen on specific interface
py-ldap-server --port 1389 --bind-host 192.168.1.100
```

### 🔒 **Firewall Configuration**
```bash
# Ubuntu/Debian firewall
sudo ufw allow 389/tcp  # LDAP
sudo ufw allow 636/tcp  # LDAPS (Phase 3)

# CentOS/RHEL firewall
sudo firewall-cmd --permanent --add-port=389/tcp
sudo firewall-cmd --permanent --add-port=636/tcp
sudo firewall-cmd --reload
```

## 📁 **Directory Structure Configuration**

### 🏗️ **Base DN Configuration**
The base DN defines your directory's root:

```json
{
  "base_dn": "dc=example,dc=com",
  "entries": [...]
}
```

**Common Base DN Patterns:**
- **Organization**: `dc=company,dc=com`
- **Department**: `ou=engineering,dc=company,dc=com`
- **Geographic**: `l=newyork,dc=company,dc=com`
- **Mixed**: `ou=people,dc=engineering,dc=company,dc=com`

### 👥 **User Organization**
Organize users in organizational units:

```json
{
  "entries": [
    {
      "dn": "ou=people,dc=company,dc=com",
      "objectClass": ["organizationalUnit"],
      "ou": "people",
      "description": "All user accounts"
    },
    {
      "dn": "ou=groups,dc=company,dc=com", 
      "objectClass": ["organizationalUnit"],
      "ou": "groups",
      "description": "Access groups"
    },
    {
      "dn": "ou=services,dc=company,dc=com",
      "objectClass": ["organizationalUnit"], 
      "ou": "services",
      "description": "Service accounts"
    }
  ]
}
```

### 🔑 **User Entry Format**
Standard user entry structure:

```json
{
  "dn": "cn=jdoe,ou=people,dc=company,dc=com",
  "objectClass": ["person", "organizationalPerson", "inetOrgPerson"],
  "cn": "jdoe",
  "sn": "Doe",
  "givenName": "John",
  "displayName": "John Doe",
  "mail": "john.doe@company.com",
  "userPassword": "$2b$12$hash...",
  "employeeNumber": "12345",
  "department": "Engineering",
  "title": "Software Engineer",
  "telephoneNumber": "+1-555-123-4567",
  "mobile": "+1-555-987-6543"
}
```

## 🔧 **Environment Variables**

### 📋 **Supported Variables**
```bash
# Server configuration
export LDAP_PORT=389
export LDAP_HOST=0.0.0.0
export LDAP_DEBUG=false

# Storage configuration  
export LDAP_STORAGE_TYPE=json
export LDAP_STORAGE_FILE=/etc/ldap/directory.json

# Security configuration
export LDAP_PASSWORD_ROUNDS=12
export LDAP_ANONYMOUS_BIND=true
```

### 🐳 **Docker Environment**
```yaml
# docker-compose.yml (Phase 4)
version: '3.12'
services:
  ldap-server:
    image: py-ldap-server:latest
    environment:
      - LDAP_PORT=389
      - LDAP_HOST=0.0.0.0
      - LDAP_STORAGE_TYPE=json
      - LDAP_STORAGE_FILE=/data/directory.json
    ports:
      - "389:389"
    volumes:
      - ./data:/data
```

## 📊 **Logging Configuration**

### 🔍 **Debug Mode**
Enable verbose logging for troubleshooting:

```bash
# Enable debug mode
py-ldap-server --debug

# Debug output example
# 2025-09-07 10:30:15 DEBUG LDAP Server starting on localhost:1389
# 2025-09-07 10:30:15 DEBUG Using MemoryStorage with sample data  
# 2025-09-07 10:30:15 DEBUG Authentication system initialized
# 2025-09-07 10:30:15 INFO  LDAP Server ready for connections
```

### 📝 **Log Levels**
```python
# Available log levels
CRITICAL = 50   # Critical errors only
ERROR = 40      # Error conditions  
WARNING = 30    # Warning messages
INFO = 20       # General information (default)
DEBUG = 10      # Detailed debugging
```

### 📊 **Production Logging**
```bash
# SystemD service logging
journalctl -u py-ldap-server -f

# Log rotation configuration
# /etc/logrotate.d/py-ldap-server
/var/log/py-ldap-server/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    sharedscripts
}
```

## ⚡ **Performance Configuration**

### 🚀 **Memory Usage**
```python
# Memory optimization settings
MEMORY_STORAGE_MAX_ENTRIES = 10000  # Limit for memory storage
JSON_CACHE_SIZE = 1000              # JSON entry cache size
CONNECTION_POOL_SIZE = 100          # Max concurrent connections
```

### 📊 **Connection Limits**
```bash
# System limits (Linux)
# /etc/security/limits.conf
ldap soft nofile 4096
ldap hard nofile 8192

# SystemD service limits
# /etc/systemd/system/py-ldap-server.service
[Service]
LimitNOFILE=8192
```

## 🔧 **Troubleshooting**

### 🐛 **Common Issues**

#### Server Won't Start
```bash
# Check port availability
ss -tuln | grep :1389

# Check permissions
ls -la /etc/ldap/directory.json

# Check configuration syntax
py-ldap-server --storage json --storage-file test.json --debug
```

#### Authentication Failures
```bash
# Check user data
cat directory.json | jq '.entries[] | select(.cn == "username")'

# Test password hashing
python3 -c "
from ldap_server.auth.password import PasswordManager
pm = PasswordManager()
print(pm.verify_password('password', 'hash'))
"

# Enable debug logging
py-ldap-server --debug
```

#### Connection Issues
```bash
# Test connectivity
telnet localhost 1389

# Check firewall
sudo ufw status

# Verify binding
netstat -tuln | grep :1389
```

### 📋 **Configuration Validation**

#### JSON Syntax Validation
```bash
# Validate JSON syntax
python3 -m json.tool directory.json

# Validate LDAP structure
ldapsearch -x -H ldap://localhost:1389 -b "dc=example,dc=com" -s base
```

#### Configuration Testing
```bash
# Test configuration without starting server
py-ldap-server --storage json --storage-file test.json --dry-run

# Validate user entries
ldapsearch -x -H ldap://localhost:1389 -b "ou=people,dc=example,dc=com" "(objectClass=person)"
```

## 📚 **Configuration Examples**

### 🏢 **Small Company Setup**
```json
{
  "base_dn": "dc=acme,dc=com",
  "entries": [
    {
      "dn": "dc=acme,dc=com",
      "objectClass": ["dcObject", "organization"],
      "o": "Acme Corporation",
      "dc": "acme"
    },
    {
      "dn": "ou=employees,dc=acme,dc=com",
      "objectClass": ["organizationalUnit"],
      "ou": "employees"
    },
    {
      "dn": "cn=admin,ou=employees,dc=acme,dc=com",
      "objectClass": ["person", "organizationalPerson"],
      "cn": "admin",
      "sn": "Administrator",
      "userPassword": "$2b$12$secure_hash",
      "mail": "admin@acme.com"
    }
  ]
}
```

### 🎓 **Educational Institution**
```json
{
  "base_dn": "dc=university,dc=edu",
  "entries": [
    {
      "dn": "dc=university,dc=edu",
      "objectClass": ["dcObject", "organization"],
      "o": "State University",
      "dc": "university"
    },
    {
      "dn": "ou=students,dc=university,dc=edu",
      "objectClass": ["organizationalUnit"],
      "ou": "students"
    },
    {
      "dn": "ou=faculty,dc=university,dc=edu",
      "objectClass": ["organizationalUnit"],
      "ou": "faculty"  
    },
    {
      "dn": "ou=staff,dc=university,dc=edu",
      "objectClass": ["organizationalUnit"],
      "ou": "staff"
    }
  ]
}
```

## 🔗 **Related Documentation**

- **[🚀 Quick Start Guide](quick-start.md)** - Get started quickly
- **[🔐 Authentication Guide](authentication.md)** - Security and user management
- **[🚀 Deployment Guide](../deployment/README.md)** - Production deployment
- **[💾 Storage Documentation](../api/storage/README.md)** - Storage backend details

---

**Configuration Status**: Basic configuration complete (Phase 1)  
**Advanced Features**: Coming in Phase 2-4 (schema validation, TLS, clustering)  
**Best Practices**: Security-first configuration with sensible defaults  
**Last Updated**: September 7, 2025

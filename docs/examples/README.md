# Examples & Tutorials

This section provides practical examples, code samples, and step-by-step tutorials for using py-ldap-server in various scenarios.

## 📚 **Available Examples**

### 🚀 **Basic Usage**
- **[📖 Basic Server Usage](basic-usage.md)** - Simple server setup and operation
- **[🔧 Configuration Examples](configuration/)** - Sample configuration files
- **[👤 User Management](basic-usage.md#user-management)** - Managing users and passwords

### 🔌 **Client Integration**
- **[🌐 LDAP Client Examples](client-examples.md)** - Connecting various LDAP clients
- **[🔑 Authentication Examples](client-examples.md#authentication)** - Client authentication patterns
- **[🔍 Search Examples](client-examples.md#search)** - LDAP search operations

### ⚙️ **Configuration Templates**
- **[📄 Basic Configuration](configuration/basic.json)** - Simple server setup
- **[🔐 Secure Configuration](configuration/secure.json)** - Production security setup
- **[📊 Monitoring Configuration](configuration/monitoring.json)** - Operational monitoring

## 🎯 **Example Categories**

### 👶 **Beginner Examples**
Perfect for getting started:
```bash
# Start basic server
py-ldap-server --port 1389

# Test with ldapsearch
ldapsearch -x -H ldap://localhost:1389 -b "dc=example,dc=com"
```

### 👨‍💼 **Administrator Examples**
Production deployment scenarios:
- SystemD service configuration
- Security hardening setup
- Backup and monitoring configuration

### 👨‍💻 **Developer Examples**
Code integration and customization:
- Custom storage backend implementation
- Authentication handler extension
- Client library integration

## 📋 **Tutorial Series**

### 📖 **Tutorial 1: Quick Start**
Get py-ldap-server running in 5 minutes:
1. Installation and setup
2. Basic configuration
3. First LDAP query
4. User authentication

### 🔧 **Tutorial 2: Configuration**
Complete server configuration:
1. Storage backend selection
2. Authentication setup
3. Security configuration
4. Performance tuning

### 🚀 **Tutorial 3: Production Deployment**
Deploy to production environment:
1. SystemD service setup
2. Security hardening
3. Monitoring configuration
4. Backup procedures

### 🔌 **Tutorial 4: Client Integration**
Integrate with common applications:
1. Apache/Nginx authentication
2. PAM configuration
3. Application development
4. Troubleshooting

## 💡 **Common Use Cases**

### 🏢 **Enterprise Directory**
Setting up py-ldap-server as a company directory:
- User and group management
- Application authentication
- System integration (PAM/SSSD)
- Security policies

### 🧪 **Development & Testing**
Using py-ldap-server for development:
- Local LDAP server for testing
- Mock directory data
- Integration testing
- CI/CD pipeline integration

### 🔬 **Learning LDAP**
Educational use of py-ldap-server:
- Understanding LDAP concepts
- Experimenting with LDAP operations
- Learning directory services
- Protocol analysis

## 🛠️ **Code Examples**

### Python Client Example
```python
import ldap3

# Connect to py-ldap-server
server = ldap3.Server('ldap://localhost:1389')
conn = ldap3.Connection(server, auto_bind=True)

# Search for users
conn.search('dc=example,dc=com', '(objectClass=person)')
for entry in conn.entries:
    print(f"User: {entry.cn}")
```

### Shell Script Example
```bash
#!/bin/bash
# Test LDAP authentication

LDAP_SERVER="ldap://localhost:1389"
BASE_DN="dc=example,dc=com"

# Search for all users
ldapsearch -x -H "$LDAP_SERVER" -b "$BASE_DN" "(objectClass=person)" cn mail

# Test authentication
ldapsearch -x -H "$LDAP_SERVER" -b "$BASE_DN" \
    -D "cn=admin,dc=example,dc=com" -W "(cn=*)"
```

### Configuration File Example
```json
{
  "server": {
    "port": 389,
    "bind_host": "0.0.0.0",
    "debug": false
  },
  "storage": {
    "type": "json",
    "file": "/etc/py-ldap-server/data.json"
  },
  "security": {
    "password_rounds": 12,
    "require_tls": false
  }
}
```

## 📊 **Example Data Sets**

### 👥 **Sample Directory Data**
Pre-built directory structures for testing:
- **Small Company**: 10 users, 3 groups
- **Medium Organization**: 100 users, 10 groups, multiple OUs
- **Large Enterprise**: 1000+ users, complex hierarchy

### 🔧 **Configuration Variants**
Different configuration examples:
- **Development**: Basic setup for local development
- **Staging**: Production-like testing environment
- **Production**: Secure enterprise deployment

## 🔍 **Troubleshooting Examples**

### 🐛 **Common Issues**
Real-world problems and solutions:
- Authentication failures
- Connection timeouts
- Performance issues
- Configuration errors

### 🔧 **Debug Techniques**
Debugging approaches with examples:
- Log analysis
- Network troubleshooting
- Performance profiling
- Security audit

## 📚 **Reference Material**

### 📖 **LDAP Concepts**
Quick reference for LDAP concepts:
- Distinguished Names (DN)
- Object Classes and Attributes
- Search Filters and Scope
- Bind Operations

### 🔑 **Authentication Methods**
Examples of different authentication approaches:
- Anonymous bind
- Simple bind
- SASL authentication (future)
- Certificate authentication (future)

## 🎓 **Learning Path**

### 📚 **Recommended Reading Order**
1. **[📖 Basic Usage](basic-usage.md)** - Start here
2. **[🔧 Configuration Examples](configuration/)** - Learn configuration
3. **[🌐 Client Examples](client-examples.md)** - Client integration
4. **[🚀 Deployment Guide](../deployment/README.md)** - Production deployment

### 🎯 **Skill Levels**
- **Beginner**: Basic server operation and simple queries
- **Intermediate**: Configuration, authentication, and integration
- **Advanced**: Custom extensions, performance tuning, security

## 🤝 **Contributing Examples**

Have a useful example? We welcome contributions:
1. **Create Example**: Write clear, documented example
2. **Test Example**: Ensure example works correctly
3. **Submit PR**: Follow contribution guidelines
4. **Update Index**: Add to this README

## 🔗 **External Examples**

### 🌐 **Community Examples**
- **GitHub Repositories**: Community-contributed examples
- **Blog Posts**: Tutorials and use cases
- **Stack Overflow**: Q&A and solutions

### 📖 **Official Documentation**
- **[📚 User Guides](../guides/README.md)** - Comprehensive guides
- **[🔧 API Documentation](../api/README.md)** - Technical reference
- **[🚀 Deployment Docs](../deployment/README.md)** - Production deployment

---

**Examples Status**: Basic examples available (Phase 1)  
**Coming Soon**: Advanced integration examples (Phase 2+)  
**Last Updated**: September 7, 2025

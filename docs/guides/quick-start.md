# Quick Start Guide

Get py-ldap-server running in 5 minutes! This guide will help you install, configure, and test your LDAP server quickly.

## 🚀 **5-Minute Quick Start**

### 1️⃣ **Installation** (1 minute)

```bash
# Clone the repository
git clone https://github.com/evilerbender/py-ldap-server.git
cd py-ldap-server

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with dependencies
pip install -e .[dev]
```

### 2️⃣ **Start the Server** (30 seconds)

```bash
# Start with default settings
py-ldap-server --port 1389 --bind-host localhost --debug

# Server output:
# LDAP Server starting on localhost:1389
# Using MemoryStorage with sample data
# Debug mode enabled
```

### 3️⃣ **Test Basic Operations** (2 minutes)

```bash
# Test 1: Anonymous search (root entry)
ldapsearch -x -H ldap://localhost:1389 -b "dc=example,dc=com" -s base

# Expected output:
# dn: dc=example,dc=com
# objectClass: dcObject
# objectClass: organization
# o: Example Organization
# dc: example

# Test 2: Search for all people
ldapsearch -x -H ldap://localhost:1389 -b "ou=people,dc=example,dc=com" "(objectClass=person)"

# Expected output: Multiple user entries (admin, alice, bob)

# Test 3: Authenticated search
ldapsearch -x -H ldap://localhost:1389 -b "dc=example,dc=com" \
    -D "cn=admin,ou=people,dc=example,dc=com" -w "admin" "(cn=*)"
```

### 4️⃣ **Verify Authentication** (1 minute)

```bash
# Test successful authentication
ldapsearch -x -H ldap://localhost:1389 -b "ou=people,dc=example,dc=com" \
    -D "cn=alice,ou=people,dc=example,dc=com" -w "alice123" "(cn=alice)"

# Test failed authentication (wrong password)
ldapsearch -x -H ldap://localhost:1389 -b "ou=people,dc=example,dc=com" \
    -D "cn=alice,ou=people,dc=example,dc=com" -w "wrongpassword" "(cn=alice)"
# Expected: ldap_bind: Invalid credentials (49)
```

### 5️⃣ **Success!** ✅

Your LDAP server is now running and responding to queries!

## 📋 **Default Directory Structure**

The server comes with sample data pre-loaded:

```
dc=example,dc=com
├── ou=people,dc=example,dc=com
│   ├── cn=admin,ou=people,dc=example,dc=com (password: admin)
│   ├── cn=alice,ou=people,dc=example,dc=com (password: alice123)  
│   └── cn=bob,ou=people,dc=example,dc=com (password: bob456)
├── ou=groups,dc=example,dc=com
│   ├── cn=admins,ou=groups,dc=example,dc=com
│   └── cn=users,ou=groups,dc=example,dc=com
└── ou=services,dc=example,dc=com
    └── cn=ldap,ou=services,dc=example,dc=com
```

## ⚙️ **Basic Configuration**

### 🔧 **Command Line Options**
```bash
# Basic options
py-ldap-server --port 1389 --bind-host localhost --debug

# JSON storage (persistent data)
py-ldap-server --storage json --storage-file data.json

# Production mode (no debug)
py-ldap-server --port 389 --bind-host 0.0.0.0
```

### 📄 **JSON Storage Setup**
```bash
# Create a JSON data file
cat > my_directory.json << 'EOF'
{
  "base_dn": "dc=mycompany,dc=com",
  "entries": [
    {
      "dn": "dc=mycompany,dc=com",
      "objectClass": ["dcObject", "organization"],
      "o": "My Company",
      "dc": "mycompany"
    },
    {
      "dn": "cn=admin,dc=mycompany,dc=com", 
      "objectClass": ["person", "organizationalPerson"],
      "cn": "admin",
      "sn": "Administrator",
      "userPassword": "adminpass"
    }
  ]
}
EOF

# Start server with JSON storage
py-ldap-server --storage json --storage-file my_directory.json --port 1389
```

## 🧪 **Testing Your Setup**

### ✅ **Verification Checklist**

#### Server Status
- [ ] Server starts without errors
- [ ] Server listens on configured port
- [ ] Debug logs show successful initialization

#### Basic Operations
- [ ] Anonymous search returns root entry
- [ ] Search finds user entries
- [ ] Authentication works with correct passwords
- [ ] Authentication fails with wrong passwords

#### LDAP Client Compatibility
- [ ] `ldapsearch` commands work
- [ ] Can connect with LDAP browser tools
- [ ] Python ldap3 library can connect

### 🔧 **Common Issues & Solutions**

#### Server Won't Start
```bash
# Check if port is already in use
ss -tuln | grep :1389

# Try different port
py-ldap-server --port 1390

# Check for permission issues
sudo py-ldap-server --port 389  # Requires root for port < 1024
```

#### ldapsearch Not Found
```bash
# Install LDAP utilities
# Ubuntu/Debian:
sudo apt-get install ldap-utils

# CentOS/RHEL:
sudo yum install openldap-clients

# macOS:
brew install openldap
```

#### Connection Refused
```bash
# Check server is running
ps aux | grep py-ldap-server

# Check bind address
py-ldap-server --bind-host 0.0.0.0  # Listen on all interfaces

# Check firewall
sudo ufw allow 1389  # Ubuntu firewall
```

## 🎯 **Next Steps**

### 📚 **Learn More**
- **[⚙️ Configuration Guide](configuration.md)** - Detailed configuration options
- **[🔐 Authentication Setup](authentication.md)** - User management and security
- **[📋 LDAP Operations](ldap-operations.md)** - Advanced LDAP usage

### 🚀 **Production Deployment**
- **[🛡️ Security Hardening](../deployment/security.md)** - Secure your installation
- **[⚙️ SystemD Setup](../deployment/systemd.md)** - Run as system service
- **[📊 Monitoring](../deployment/README.md#monitoring)** - Operational monitoring

### 🧪 **Development**
- **[🧪 Testing Guide](../development/testing.md)** - Run the test suite
- **[🏗️ Architecture](../development/architecture.md)** - Understand the codebase
- **[🤝 Contributing](../development/contributing.md)** - Join development

## 💡 **Example Use Cases**

### 🏢 **Corporate Directory**
```bash
# Start server for company directory
py-ldap-server --storage json --storage-file company_directory.json --port 389

# Configure applications to authenticate against ldap://ldap.company.com:389
```

### 🧪 **Development Testing**
```bash
# Quick test server for development
py-ldap-server --port 1389 --debug

# Perfect for testing LDAP integrations in applications
```

### 📚 **LDAP Learning**
```bash
# Educational LDAP server
py-ldap-server --port 1389 --debug

# Experiment with LDAP concepts and operations
```

## 🆘 **Getting Help**

- **[🔧 Troubleshooting](configuration.md#troubleshooting)** - Common issues and solutions
- **[📖 Full Documentation](../README.md)** - Complete documentation index
- **[🐛 Report Issues](https://github.com/evilerbender/py-ldap-server/issues)** - Bug reports
- **[💬 Discussions](https://github.com/evilerbender/py-ldap-server/discussions)** - Questions and help

---

**🎉 Congratulations! You now have a working LDAP server!**

**Next**: Explore the **[📖 Configuration Guide](configuration.md)** to customize your setup.

**Last Updated**: September 7, 2025

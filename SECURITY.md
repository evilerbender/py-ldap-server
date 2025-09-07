# Security Features and Password Management

## 🔐 Secure Password Storage

The py-ldap-server implements secure password storage using industry-standard bcrypt hashing. This addresses the critical security issue of storing plain text passwords.

### Password Hashing Features

- **bcrypt encryption**: Uses bcrypt with configurable rounds (default: 12)
- **LDAP-compatible format**: Stores hashes in `{BCRYPT}base64_encoded_hash` format
- **Salt generation**: Each password gets a unique cryptographically secure salt
- **Backwards compatibility**: Still supports plain text and SSHA for legacy systems

### Password Format Support

1. **{BCRYPT}** - Recommended secure format using bcrypt
2. **{SSHA}** - Legacy Salted SHA-1 support (deprecated but functional)
3. **Plain text** - For backwards compatibility (not recommended)

## �️ SystemD Security Hardening

Many security concerns can be effectively mitigated using native systemd capabilities rather than application-level changes. This approach provides robust, OS-level security controls that are well-tested and maintained.

### Recommended SystemD Unit Settings

Create a secure systemd service unit for py-ldap-server with the following security settings:

```ini
[Unit]
Description=Python LDAP Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=ldap-server
Group=ldap-server
ExecStart=/usr/local/bin/py-ldap-server --json /etc/ldap-server/data.json
Restart=always
RestartSec=10

# === SECURITY HARDENING ===

# Process isolation
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectHostname=yes
ProtectClock=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectKernelLogs=yes
ProtectControlGroups=yes

# Network security
IPAddressDeny=any
IPAddressAllow=localhost
IPAddressAllow=10.0.0.0/8
IPAddressAllow=172.16.0.0/12
IPAddressAllow=192.168.0.0/16
# Adjust IP ranges as needed for your environment

# Filesystem access control
ReadWritePaths=/var/lib/ldap-server
ReadOnlyPaths=/etc/ldap-server
# Deny access to sensitive directories
InaccessiblePaths=/proc/sys
InaccessiblePaths=/sys
InaccessiblePaths=/dev

# Capability restrictions
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE
# Only needed if binding to port < 1024

# Resource limits (prevents DoS via resource exhaustion)
LimitNOFILE=1024
LimitNPROC=64
LimitCPU=300
LimitAS=512M

# Memory protection
MemoryDenyWriteExecute=yes
LockPersonality=yes
RestrictRealtime=yes
RestrictSUIDSGID=yes

# System call filtering
SystemCallFilter=@system-service
SystemCallFilter=~@debug @mount @cpu-emulation @obsolete
SystemCallErrorNumber=EPERM

# Namespace isolation
PrivateNetwork=no  # Set to 'yes' if using socket activation
UMask=0077

[Install]
WantedBy=multi-user.target
```

### Security Benefits of SystemD Hardening

| Security Concern | SystemD Mitigation | Benefit |
|------------------|-------------------|---------|
| **Rate Limiting** | `LimitNOFILE`, `LimitNPROC`, `LimitCPU` | Prevents resource exhaustion DoS attacks |
| **File System Access** | `ProtectSystem`, `ReadWritePaths`, `ReadOnlyPaths` | Limits file system access to necessary paths only |
| **Network Security** | `IPAddressDeny`, `IPAddressAllow` | Restricts network access to allowed IP ranges |
| **Privilege Escalation** | `NoNewPrivileges`, `CapabilityBoundingSet` | Prevents privilege escalation attacks |
| **Memory Attacks** | `MemoryDenyWriteExecute`, `LockPersonality` | Mitigates memory-based exploits |
| **System Call Abuse** | `SystemCallFilter` | Restricts to safe system calls only |
| **Directory Traversal** | `ProtectHome`, `InaccessiblePaths` | Prevents access to sensitive directories |
| **Temporary File Attacks** | `PrivateTmp` | Isolates temporary files |

### Installation and Setup

1. **Create dedicated user and group:**
```bash
sudo useradd --system --home-dir /var/lib/ldap-server --create-home ldap-server
sudo usermod -s /usr/sbin/nologin ldap-server
```

2. **Set up directory structure:**
```bash
sudo mkdir -p /etc/ldap-server /var/lib/ldap-server
sudo chown ldap-server:ldap-server /var/lib/ldap-server
sudo chmod 750 /var/lib/ldap-server
sudo chmod 755 /etc/ldap-server
```

3. **Install the service:**
```bash
sudo cp py-ldap-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable py-ldap-server
sudo systemctl start py-ldap-server
```

4. **Verify security settings:**
```bash
# Check service status
sudo systemctl status py-ldap-server

# Verify security restrictions are active
sudo systemd-analyze security py-ldap-server
```

### Additional Security Considerations

- **TLS/SSL**: Use a reverse proxy (nginx/Apache) with TLS termination
- **Firewall**: Configure iptables/ufw to restrict access
- **Monitoring**: Use journald for centralized logging
- **Updates**: Keep system and dependencies updated

## �🔧 Password Management Tools

### Upgrade Existing Data

Use the password upgrade script to convert plain text passwords to secure hashes:

```bash
# Upgrade passwords in data.json file
uv run python scripts/upgrade_passwords.py data.json

# The script will:
# 1. Create a backup of the original file
# 2. Convert all plain text passwords to bcrypt hashes
# 3. Preserve existing hashed passwords
# 4. Show a summary of changes made
```

### Password Verification

The server automatically verifies passwords using the appropriate method:

```python
from ldap_server.auth.password import PasswordManager

# Hash a new password
hashed = PasswordManager.hash_password("mypassword123")
print(hashed)  # {BCRYPT}base64_encoded_hash

# Verify a password
is_valid = PasswordManager.verify_password("mypassword123", hashed)
print(is_valid)  # True
```

### Generate Secure Passwords

Create cryptographically secure passwords:

```python
from ldap_server.auth.password import generate_secure_password

# Generate a 16-character password
password = generate_secure_password()
print(password)  # Example: "Kj9#mP2$nQ8@vL5!"

# Generate custom length (minimum 12)
long_password = generate_secure_password(24)
```

## 🛡️ Security Best Practices

### For Production Use

1. **Always hash passwords**: Never store plain text passwords
2. **Use strong rounds**: Default bcrypt rounds (12) are recommended
3. **Regular password updates**: Encourage users to change passwords periodically
4. **Audit password strength**: Use the password generation tools for strong defaults

### Migration Strategy

When migrating from plain text passwords:

1. **Backup your data**: The upgrade script automatically creates backups
2. **Test thoroughly**: Verify authentication still works after upgrade
3. **Update documentation**: Inform users about the security improvements
4. **Monitor logs**: Check for any authentication issues post-migration

## 🔍 Security Testing

Run the comprehensive password security tests:

```bash
# Run all password-related tests
uv run python -m pytest tests/unit/test_password.py -v

# Test specific functionality
uv run python -m pytest tests/unit/test_password.py::TestPasswordManager::test_verify_correct_password -v
```

## 📊 Example Usage

### Before Security Improvement
```json
{
  "dn": "uid=admin,ou=people,dc=example,dc=com",
  "attributes": {
    "userPassword": ["admin123"]  // ❌ Plain text - INSECURE
  }
}
```

### After Security Improvement
```json
{
  "dn": "uid=admin,ou=people,dc=example,dc=com",
  "attributes": {
    "userPassword": ["{BCRYPT}JDJiJDEyJEpBV29UeXdZclBVUHR1VDFqRGxEVWVSR0pmMFU0NnpkdDdpQ1RVTGdQTFh1dk9oTFdmNXd1"]  // ✅ Secure bcrypt hash
  }
}
```

### Authentication Verification
```python
# Both of these will work correctly:
# 1. User enters "admin123" as password
# 2. Server verifies against bcrypt hash
# 3. Authentication succeeds

original_password = "admin123"
stored_hash = "{BCRYPT}JDJiJDEyJEpBV29UeXdZclBVUHR1VDFqRGxEVWVSR0pmMFU0NnpkdDdpQ1RVTGdQTFh1dk9oTFdmNXd1"

is_authenticated = PasswordManager.verify_password(original_password, stored_hash)
# Returns: True
```

## 🚨 Security Impact

This security improvement addresses:

- **Critical vulnerability**: Plain text password storage
- **Compliance requirements**: Industry standards for password security
- **Data protection**: Credentials are now cryptographically protected
- **Audit readiness**: Secure password handling for security reviews

The bcrypt hashing with salt ensures that even if the database is compromised, passwords remain protected against:
- Rainbow table attacks
- Dictionary attacks  
- Brute force attacks (with sufficient round count)

## 🔄 Backwards Compatibility

The implementation maintains full backwards compatibility:
- Existing plain text passwords continue to work during transition
- SSHA hashes from other LDAP servers are supported
- Gradual migration is supported - passwords can be upgraded over time
- No breaking changes to existing authentication flows

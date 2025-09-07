# SystemD Security Reference

## 🛡️ Quick Security Settings Reference

This reference card shows how systemd unit settings address common security concerns for py-ldap-server.

## Security Concerns → SystemD Solutions

| Security Issue | SystemD Setting | Effect |
|---------------|-----------------|--------|
| **Rate Limiting / DoS** | `LimitNOFILE=1024`<br>`LimitNPROC=64`<br>`LimitCPU=300` | Limits file descriptors, processes, and CPU usage |
| **Memory Exhaustion** | `LimitAS=512M`<br>`LimitRSS=256M`<br>`MemoryDenyWriteExecute=yes` | Caps memory usage and prevents code injection |
| **Filesystem Access** | `ProtectSystem=strict`<br>`ReadWritePaths=/var/lib/ldap-server`<br>`ReadOnlyPaths=/etc/ldap-server` | Restricts filesystem access to required paths only |
| **Network Security** | `IPAddressDeny=any`<br>`IPAddressAllow=192.168.0.0/16` | Allow-lists specific IP ranges |
| **Privilege Escalation** | `NoNewPrivileges=yes`<br>`CapabilityBoundingSet=CAP_NET_BIND_SERVICE` | Prevents privilege escalation |
| **System Access** | `ProtectHome=yes`<br>`ProtectKernelTunables=yes`<br>`InaccessiblePaths=/proc/sys` | Denies access to sensitive system areas |
| **Temporary File Attacks** | `PrivateTmp=yes`<br>`UMask=0077` | Isolates temporary files |
| **System Call Abuse** | `SystemCallFilter=@system-service`<br>`SystemCallFilter=~@debug` | Restricts to safe system calls |

## 🔧 Common Configuration Examples

### Basic Security (Recommended Minimum)
```ini
[Service]
User=ldap-server
Group=ldap-server
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/var/lib/ldap-server
ReadOnlyPaths=/etc/ldap-server
```

### Network Security
```ini
[Service]
# Deny all, then allow specific ranges
IPAddressDeny=any
IPAddressAllow=localhost
IPAddressAllow=10.0.0.0/8
IPAddressAllow=172.16.0.0/12
IPAddressAllow=192.168.0.0/16
```

### Resource Limits (DoS Prevention)
```ini
[Service]
LimitNOFILE=1024        # Max open files
LimitNPROC=64           # Max processes
LimitCPU=300            # Max CPU seconds
LimitAS=512M            # Max virtual memory
LimitRSS=256M           # Max resident memory
```

### Maximum Security Hardening
```ini
[Service]
# Process isolation
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectHostname=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes

# Memory protection
MemoryDenyWriteExecute=yes
LockPersonality=yes
RestrictRealtime=yes
RestrictSUIDSGID=yes

# System call filtering
SystemCallFilter=@system-service
SystemCallFilter=~@debug @mount @obsolete
SystemCallErrorNumber=EPERM

# Filesystem restrictions
InaccessiblePaths=/proc/sys /sys /dev /boot /root
UMask=0077
```

## 🔍 Verification Commands

### Check Security Score
```bash
sudo systemd-analyze security py-ldap-server
```

### View Active Security Settings
```bash
sudo systemctl show py-ldap-server | grep -E "(Protect|Private|NoNew|Capability|SystemCall|Memory|IPAddress|Limit)"
```

### Test Resource Limits
```bash
# Check if limits are enforced
sudo -u ldap-server bash -c 'ulimit -a'
```

### Verify Network Restrictions
```bash
# Test if IP restrictions work (should fail if configured)
sudo -u ldap-server nc -z 8.8.8.8 53
```

### Check Filesystem Access
```bash
# These should fail with proper restrictions
sudo -u ldap-server ls /root
sudo -u ldap-server ls /proc/sys
sudo -u ldap-server touch /tmp/test
```

## 📋 Security Checklist

- [ ] **User Isolation**: Service runs as dedicated non-root user
- [ ] **Filesystem**: Read/write access limited to required paths only
- [ ] **Network**: IP access restricted to allowed ranges
- [ ] **Privileges**: NoNewPrivileges and capability restrictions enabled  
- [ ] **Resources**: CPU, memory, and file descriptor limits set
- [ ] **System Calls**: Filtered to safe subset only
- [ ] **Memory**: Write+execute protection enabled
- [ ] **Temporary Files**: Private tmp directory used
- [ ] **Verification**: Security score analyzed and acceptable

## 🚀 Implementation Benefits

✅ **No Code Changes Required**: Pure configuration-based security  
✅ **Battle-Tested**: SystemD security features used in production worldwide  
✅ **Comprehensive**: Addresses multiple attack vectors simultaneously  
✅ **Maintainable**: Standard systemd configuration, easy to audit  
✅ **Flexible**: Easily adjustable for different environments  
✅ **Observable**: Built-in monitoring and verification tools  

This approach provides enterprise-grade security through proven OS-level controls.

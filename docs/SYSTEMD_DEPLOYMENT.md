# SystemD Deployment Guide

This guide shows how to deploy py-ldap-server as a secure systemd service with comprehensive security hardening.

## 🛡️ Security-First Deployment

The deployment uses native systemd security capabilities to provide enterprise-grade security without requiring application-level changes.

## Prerequisites

- Linux system with systemd
- Python 3.8+ installed
- sudo/root access for service installation

## Installation Steps

### 1. Create Dedicated Service User

```bash
# Create system user for the LDAP server
sudo useradd --system \
    --home-dir /var/lib/ldap-server \
    --create-home \
    --shell /usr/sbin/nologin \
    --comment "LDAP Server Service Account" \
    ldap-server

# Set proper permissions
sudo chmod 750 /var/lib/ldap-server
```

### 2. Set Up Directory Structure

```bash
# Create configuration and data directories
sudo mkdir -p /etc/ldap-server
sudo mkdir -p /var/lib/ldap-server
sudo mkdir -p /var/log/ldap-server

# Set ownership and permissions
sudo chown ldap-server:ldap-server /var/lib/ldap-server
sudo chown root:ldap-server /etc/ldap-server
sudo chown ldap-server:ldap-server /var/log/ldap-server

sudo chmod 750 /var/lib/ldap-server
sudo chmod 750 /etc/ldap-server
sudo chmod 750 /var/log/ldap-server
```

### 3. Install py-ldap-server

```bash
# Install using pip (recommended approach for system deployment)
sudo pip3 install py-ldap-server

# Or install from source
git clone https://github.com/evilerbender/py-ldap-server.git
cd py-ldap-server
sudo pip3 install .

# Verify installation
which py-ldap-server
```

### 4. Configure LDAP Data

```bash
# Copy your LDAP data file to the configuration directory
sudo cp data.json /etc/ldap-server/
sudo chown root:ldap-server /etc/ldap-server/data.json
sudo chmod 640 /etc/ldap-server/data.json

# Ensure passwords are properly hashed
sudo -u ldap-server python3 -c "
from ldap_server.auth.password import PasswordManager
import json

with open('/etc/ldap-server/data.json', 'r') as f:
    data = json.load(f)

# Check if any passwords need upgrading
needs_upgrade = False
for entry in data:
    if 'userPassword' in entry.get('attributes', {}):
        for pwd in entry['attributes']['userPassword']:
            if not pwd.startswith('{'):
                needs_upgrade = True
                break

if needs_upgrade:
    print('WARNING: Plain text passwords detected!')
    print('Run: python3 scripts/upgrade_passwords.py /etc/ldap-server/data.json')
else:
    print('✅ All passwords are properly hashed')
"
```

### 5. Install SystemD Service

```bash
# Copy the service file
sudo cp systemd/py-ldap-server.service /etc/systemd/system/

# Reload systemd configuration
sudo systemctl daemon-reload

# Enable the service (start on boot)
sudo systemctl enable py-ldap-server
```

### 6. Configure Firewall (if applicable)

```bash
# UFW example
sudo ufw allow from 192.168.0.0/16 to any port 1389
sudo ufw allow from 10.0.0.0/8 to any port 1389

# iptables example
sudo iptables -A INPUT -s 192.168.0.0/16 -p tcp --dport 1389 -j ACCEPT
sudo iptables -A INPUT -s 10.0.0.0/8 -p tcp --dport 1389 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 1389 -j DROP
```

### 7. Start and Verify Service

```bash
# Start the service
sudo systemctl start py-ldap-server

# Check status
sudo systemctl status py-ldap-server

# View logs
sudo journalctl -u py-ldap-server -f

# Test LDAP connectivity
ldapsearch -x -H ldap://localhost:1389 -b "dc=example,dc=com" -s base "(objectClass=*)"
```

## 🔍 Security Verification

### Check Security Settings

```bash
# Analyze service security
sudo systemd-analyze security py-ldap-server

# View effective security restrictions
sudo systemctl show py-ldap-server | grep -E "(Protect|Private|NoNew|Capability|SystemCall|Memory)"
```

### Monitor Resource Usage

```bash
# Check resource limits are working
sudo systemctl status py-ldap-server

# Monitor process in real-time
sudo systemctl show py-ldap-server --property=MainPID
ps -p $(sudo systemctl show py-ldap-server --property=MainPID --value) -o pid,user,rss,vsz,pcpu,args
```

### Test Security Restrictions

```bash
# Verify filesystem restrictions
sudo -u ldap-server ls /root 2>&1  # Should fail
sudo -u ldap-server ls /proc/sys 2>&1  # Should fail

# Check network restrictions (if configured)
sudo -u ldap-server nc -z 8.8.8.8 53 2>&1  # Should fail if IP restrictions active
```

## 🚨 Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   ```bash
   # Check file permissions
   ls -la /etc/ldap-server/
   ls -la /var/lib/ldap-server/
   
   # Fix if needed
   sudo chown -R ldap-server:ldap-server /var/lib/ldap-server
   sudo chmod 640 /etc/ldap-server/data.json
   ```

2. **Service Won't Start**
   ```bash
   # Check detailed logs
   sudo journalctl -u py-ldap-server --no-pager
   
   # Test manually
   sudo -u ldap-server py-ldap-server --json /etc/ldap-server/data.json
   ```

3. **Network Access Issues**
   ```bash
   # Check if port is bound
   sudo netstat -tlnp | grep 1389
   
   # Verify IP restrictions
   systemctl show py-ldap-server | grep IPAddress
   ```

### Logs and Monitoring

```bash
# Real-time logs
sudo journalctl -u py-ldap-server -f

# Historical logs
sudo journalctl -u py-ldap-server --since "1 hour ago"

# Export logs for analysis
sudo journalctl -u py-ldap-server --since "24 hours ago" > ldap-server.log
```

## 🔧 Customization

### Modify Security Settings

Edit `/etc/systemd/system/py-ldap-server.service` and adjust:

- **IP restrictions**: Modify `IPAddressAllow` lines
- **Resource limits**: Adjust `Limit*` settings
- **File access**: Change `ReadWritePaths`/`ReadOnlyPaths`
- **Capabilities**: Modify `CapabilityBoundingSet` if binding to port < 1024

After changes:
```bash
sudo systemctl daemon-reload
sudo systemctl restart py-ldap-server
```

### Environment-Specific Configuration

For different environments, create separate service files:

```bash
# Development
sudo cp py-ldap-server.service py-ldap-server-dev.service
# Edit for development-specific settings

# Production  
sudo cp py-ldap-server.service py-ldap-server-prod.service
# Edit for production-specific hardening
```

## 📋 Security Checklist

- [ ] Service runs as dedicated non-root user
- [ ] File permissions properly restricted (640/750)
- [ ] SystemD security settings enabled
- [ ] Firewall configured to restrict access
- [ ] Passwords properly hashed (no plain text)
- [ ] Resource limits configured
- [ ] Network access restricted to required ranges
- [ ] Logs monitored and rotated
- [ ] Security analysis shows good score
- [ ] Regular security updates applied

This deployment approach provides enterprise-grade security using proven systemd capabilities, eliminating the need for complex application-level security implementations.

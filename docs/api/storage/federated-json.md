# Federated JSON Storage Backend

The Federated JSON Storage backend allows py-ldap-server to load and merge LDAP directory data from multiple JSON files, providing a flexible and scalable approach to data management.

## Overview

The `FederatedJSONStorage` class extends the capabilities of the single-file JSON storage by:

- Loading data from multiple JSON files simultaneously
- Merging entries with configurable conflict resolution strategies
- Monitoring all files for changes with hot-reload capability
- Providing detailed statistics and error reporting

## Basic Usage

### Command Line Interface

```bash
# Load from multiple JSON files
py-ldap-server --json-files users.json groups.json systems.json

# Configure merge strategy
py-ldap-server --json-files data1.json data2.json --merge-strategy first_wins

# Disable auto-reload
py-ldap-server --json-files *.json --no-auto-reload

# Custom debounce time for file changes
py-ldap-server --json-files data*.json --debounce-time 1.0
```

### Programmatic Usage

```python
from ldap_server.storage.json import FederatedJSONStorage

# Create federated storage with multiple files
storage = FederatedJSONStorage(
    json_files=['users.json', 'groups.json', 'systems.json'],
    merge_strategy='last_wins',
    enable_watcher=True,
    debounce_time=0.5
)

# Access the LDAP directory tree
root_entry = storage.get_root()

# Get loading statistics
stats = storage.get_stats()
print(f"Loaded {stats['total_entries']} entries from {stats['files_loaded']} files")
```

## Configuration Options

### Merge Strategies

The federated storage supports three merge strategies for handling conflicting entries:

#### `last_wins` (default)
```bash
py-ldap-server --json-files base.json overrides.json --merge-strategy last_wins
```
- Later files in the list override earlier ones
- Conflicts are resolved by keeping the last encountered entry
- Useful for overlay configurations

#### `first_wins`
```bash
py-ldap-server --json-files primary.json fallback.json --merge-strategy first_wins
```
- Earlier files take precedence
- Conflicts are resolved by keeping the first encountered entry
- Useful for priority-based loading

#### `error`
```bash
py-ldap-server --json-files strict1.json strict2.json --merge-strategy error
```
- Any conflicts cause an immediate error
- Ensures no data is silently overwritten
- Useful for validation and testing

### Auto-Reload Configuration

```bash
# Enable auto-reload with custom debounce time
py-ldap-server --json-files data.json --debounce-time 1.0

# Disable auto-reload for static configurations
py-ldap-server --json-files static.json --no-auto-reload
```

## File Structure Examples

### User Data File (`users.json`)
```json
[
  {
    "dn": "dc=company,dc=com",
    "attributes": {
      "objectClass": ["top", "domain"],
      "dc": ["company"]
    }
  },
  {
    "dn": "ou=people,dc=company,dc=com",
    "attributes": {
      "objectClass": ["organizationalUnit"],
      "ou": ["people"]
    }
  },
  {
    "dn": "cn=john.doe,ou=people,dc=company,dc=com",
    "attributes": {
      "objectClass": ["person", "inetOrgPerson"],
      "cn": ["john.doe"],
      "sn": ["Doe"],
      "givenName": ["John"],
      "mail": ["john.doe@company.com"],
      "userPassword": ["secret123"]
    }
  }
]
```

### Group Data File (`groups.json`)
```json
[
  {
    "dn": "ou=groups,dc=company,dc=com",
    "attributes": {
      "objectClass": ["organizationalUnit"],
      "ou": ["groups"]
    }
  },
  {
    "dn": "cn=admins,ou=groups,dc=company,dc=com",
    "attributes": {
      "objectClass": ["groupOfNames"],
      "cn": ["admins"],
      "member": ["cn=john.doe,ou=people,dc=company,dc=com"],
      "description": ["System administrators"]
    }
  }
]
```

## Dynamic File Management

### Adding Files at Runtime

```python
storage = FederatedJSONStorage(json_files=['base.json'])

# Add new file to federation
storage.add_json_file('additional.json')

# Verify file was added
stats = storage.get_stats()
print(f"Now using {len(stats['json_files'])} files")
```

### Removing Files at Runtime

```python
# Remove file from federation
storage.remove_json_file('temporary.json')

# Data is automatically reloaded without the removed file
```

## Monitoring and Statistics

### Available Statistics

```python
stats = storage.get_stats()

# Loading information
print(f"Total entries: {stats['total_entries']}")
print(f"Files loaded: {stats['files_loaded']}")
print(f"Merge conflicts: {stats['merge_conflicts']}")
print(f"Load duration: {stats['load_duration']:.3f}s")

# Configuration
print(f"JSON files: {stats['json_files']}")
print(f"Merge strategy: {stats['merge_strategy']}")
print(f"File watching active: {stats['file_watching_active']}")
```

## Performance Considerations

### File Size Recommendations

- **Small files** (< 1MB): Optimal performance with instant loading
- **Medium files** (1-10MB): Good performance, ~100ms load time
- **Large files** (> 10MB): Consider splitting into smaller files

### Memory Usage

- All file contents are loaded into memory
- Memory usage ≈ 2-3x total JSON file size
- Use multiple smaller files instead of one large file for better memory efficiency

### File Watching Performance

- File watching adds minimal overhead
- Debounce time prevents excessive reloads during rapid changes
- Consider disabling auto-reload for static configurations

## Integration Examples

### With Docker Compose

```yaml
version: '3.8'
services:
  ldap-server:
    image: py-ldap-server
    command: >
      py-ldap-server 
      --json-files /data/users.json /data/groups.json /data/systems.json
      --merge-strategy last_wins
      --port 1389
    volumes:
      - ./ldap-data:/data:ro
    ports:
      - "1389:1389"
```

## Best Practices

### File Organization

1. **Separate by type**: Use different files for users, groups, systems, etc.
2. **Environment-specific overrides**: Use merge strategies for environment differences
3. **Modular structure**: Keep related entries in the same file

### Naming Conventions

```
users.json          # Base user data
groups.json         # Group definitions  
systems.json        # System/device entries
overrides.json      # Environment-specific overrides
local.json          # Local customizations (last in merge order)
```

### Security Considerations

1. **File permissions**: Restrict read access to the LDAP server process
2. **Password handling**: Use pre-hashed bcrypt passwords when possible
3. **Sensitive data**: Store sensitive files separately with restricted access

## Migration Guide

### From Single JSON Storage

```bash
# Old single file approach
py-ldap-server --json data.json

# New federated approach
py-ldap-server --json-files data.json
```

### Splitting Large Files

```bash
# Split users.json into smaller files by department
jq '.[] | select(.attributes.ou[0] == "engineering")' users.json > engineering.json
jq '.[] | select(.attributes.ou[0] == "marketing")' users.json > marketing.json

# Use with federated storage
py-ldap-server --json-files engineering.json marketing.json
```

## Troubleshooting

### Debug Mode

```bash
# Enable debug logging
py-ldap-server --json-files *.json --debug
```

### Validation Tools

```bash
# Validate JSON syntax
python -m json.tool users.json > /dev/null

# Check for duplicate DNs across files
grep -h '"dn":' *.json | sort | uniq -d
```

## Backward Compatibility

The federated JSON storage maintains full backward compatibility with the existing `JSONStorage` class:

- All existing `--json` commands continue to work unchanged
- Existing code using `JSONStorage` works without modification
- All previous configuration options are supported

The `JSONStorage` class now internally uses `FederatedJSONStorage` for enhanced capabilities while maintaining the same public interface.

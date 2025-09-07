# JSON Storage Backend API

The JSON storage backend provides LDAP directory data storage using JSON files with atomic write operations for data integrity and concurrent access safety.

## Overview

The JSON storage implementation includes two main classes:
- `JSONStorage`: Legacy single-file JSON storage
- `FederatedJSONStorage`: Multi-file JSON storage with advanced features
- `AtomicJSONWriter`: Thread-safe atomic write operations with file locking

## AtomicJSONWriter

The `AtomicJSONWriter` class provides thread-safe, atomic write operations for JSON files using file locking and temporary file operations.

### Features

- **Atomic Writes**: Uses temporary files and atomic rename operations
- **File Locking**: Prevents concurrent write conflicts using `fcntl` locking
- **Backup Creation**: Automatically creates timestamped backups before writes
- **Error Recovery**: Automatic rollback on write failures
- **Thread Safety**: Concurrent access protection with configurable timeouts

### Usage

```python
from src.ldap_server.storage.json import AtomicJSONWriter

# Basic atomic write
with AtomicJSONWriter('/path/to/data.json') as writer:
    writer.write_json(data)

# With backup and custom timeout
with AtomicJSONWriter('/path/to/data.json', 
                      backup_enabled=True, 
                      lock_timeout=10.0) as writer:
    writer.write_json(data)
```

### Constructor Parameters

- `file_path` (Path): Path to the JSON file
- `backup_enabled` (bool): Create timestamped backups (default: True)
- `lock_timeout` (float): Lock acquisition timeout in seconds (default: 5.0)

### Methods

#### `write_json(data: list) -> None`

Writes data to the JSON file atomically.

**Parameters:**
- `data` (list): List of LDAP entries to write

**Raises:**
- `RuntimeError`: If write operation fails
- `TimeoutError`: If file lock cannot be acquired within timeout

## FederatedJSONStorage

The `FederatedJSONStorage` class manages multiple JSON files as a federated LDAP directory store with write operations.

### Write Operations

#### `add_entry(dn: str, attributes: dict, target_file: Path) -> bool`

Adds a new LDAP entry to the specified JSON file.

**Parameters:**
- `dn` (str): Distinguished Name of the entry
- `attributes` (dict): Entry attributes
- `target_file` (Path): Target JSON file for the entry

**Returns:**
- `bool`: True if entry was added successfully, False if DN already exists

**Example:**
```python
storage = FederatedJSONStorage(json_files=['/path/to/users.json'])

success = storage.add_entry(
    "uid=john,ou=users,dc=example,dc=com",
    {
        "uid": ["john"],
        "cn": ["John Doe"],
        "sn": ["Doe"],
        "objectClass": ["top", "person", "organizationalPerson", "inetOrgPerson"]
    },
    target_file=Path('/path/to/users.json')
)
```

#### `modify_entry(dn: str, new_attributes: dict) -> bool`

Modifies an existing LDAP entry across all JSON files.

**Parameters:**
- `dn` (str): Distinguished Name of the entry to modify
- `new_attributes` (dict): New attribute values (replaces existing attributes)

**Returns:**
- `bool`: True if entry was found and modified, False if entry not found

**Example:**
```python
success = storage.modify_entry(
    "uid=john,ou=users,dc=example,dc=com",
    {"cn": ["John Smith"], "mail": ["john.smith@example.com"]}
)
```

#### `delete_entry(dn: str) -> bool`

Deletes an LDAP entry from the appropriate JSON file.

**Parameters:**
- `dn` (str): Distinguished Name of the entry to delete

**Returns:**
- `bool`: True if entry was found and deleted, False if entry not found

**Example:**
```python
success = storage.delete_entry("uid=john,ou=users,dc=example,dc=com")
```

#### `bulk_write_entries(entries: list, target_file: Path) -> bool`

Writes multiple entries to a JSON file in a single atomic operation.

**Parameters:**
- `entries` (list): List of entry dictionaries with 'dn' and 'attributes' keys
- `target_file` (Path): Target JSON file

**Returns:**
- `bool`: True if all entries were written successfully, False if any validation failed

**Example:**
```python
entries = [
    {
        "dn": "uid=alice,ou=users,dc=example,dc=com",
        "attributes": {
            "uid": ["alice"],
            "cn": ["Alice Brown"],
            "objectClass": ["top", "person"]
        }
    },
    {
        "dn": "uid=bob,ou=users,dc=example,dc=com",
        "attributes": {
            "uid": ["bob"],
            "cn": ["Bob Wilson"],
            "objectClass": ["top", "person"]
        }
    }
]

success = storage.bulk_write_entries(entries, Path('/path/to/users.json'))
```

## JSONStorage (Legacy)

The `JSONStorage` class provides backward compatibility for single-file JSON storage with write operations.

### Write Operations

All write operations follow the same interface as `FederatedJSONStorage` but operate on a single JSON file:

- `add_entry(dn: str, attributes: dict) -> bool`
- `modify_entry(dn: str, new_attributes: dict) -> bool`
- `delete_entry(dn: str) -> bool`
- `bulk_write_entries(entries: list) -> bool`

**Example:**
```python
storage = JSONStorage(json_path='/path/to/data.json')

# Add entry
storage.add_entry(
    "uid=user1,ou=users,dc=example,dc=com",
    {"uid": ["user1"], "cn": ["User One"]}
)

# Modify entry
storage.modify_entry(
    "uid=user1,ou=users,dc=example,dc=com",
    {"cn": ["Updated User One"]}
)

# Delete entry
storage.delete_entry("uid=user1,ou=users,dc=example,dc=com")
```

## Data Integrity Features

### Atomic Operations

All write operations use the `AtomicJSONWriter` to ensure:

1. **Consistency**: Either all changes are applied or none are
2. **Durability**: Changes are persisted to disk before completion
3. **Isolation**: Concurrent operations don't interfere with each other

### Backup and Recovery

- Automatic timestamped backups before each write operation
- Backup files use format: `{filename}.{timestamp}.bak`
- Failed operations leave original data intact
- Manual recovery possible from backup files

### Concurrent Access Protection

- File-level locking using `fcntl.LOCK_EX`
- Configurable lock timeout (default: 5 seconds)
- Thread-safe operations across multiple processes
- Proper cleanup on exceptions

## Error Handling

### Common Exceptions

- `RuntimeError`: Write operation failures, lock acquisition failures
- `TimeoutError`: Lock timeout exceeded
- `FileNotFoundError`: Target directory doesn't exist (auto-created)
- `PermissionError`: Insufficient file system permissions
- `ValueError`: Invalid entry data or DN format

### Best Practices

1. **Always use context managers** for automatic cleanup
2. **Handle timeouts gracefully** in high-concurrency scenarios
3. **Validate entry data** before write operations
4. **Monitor backup file accumulation** and implement cleanup policies
5. **Use appropriate lock timeouts** based on operation complexity

## Performance Considerations

### Optimization Tips

1. **Batch Operations**: Use `bulk_write_entries()` for multiple entries
2. **File Organization**: Distribute entries across multiple JSON files
3. **Lock Timeouts**: Adjust based on expected operation duration
4. **Backup Management**: Implement periodic backup cleanup
5. **Memory Usage**: Consider file size limits for large directories

### Monitoring

- Monitor backup file disk usage
- Track lock acquisition times
- Log write operation failures
- Monitor concurrent access patterns

## Configuration Examples

### Basic Configuration

```python
# Single file storage
storage = JSONStorage(json_path='/var/lib/ldap/data.json')

# Federated storage
storage = FederatedJSONStorage(json_files=[
    '/var/lib/ldap/users.json',
    '/var/lib/ldap/groups.json',
    '/var/lib/ldap/services.json'
])
```

### Production Configuration

```python
# With custom atomic writer settings
from pathlib import Path

json_files = [
    Path('/var/lib/ldap/users.json'),
    Path('/var/lib/ldap/groups.json')
]

storage = FederatedJSONStorage(json_files=json_files)

# All write operations will use:
# - 10-second lock timeout
# - Backup creation enabled
# - Atomic write operations
```

## Integration with LDAP Server

The JSON storage backend integrates seamlessly with the LDAP server for write operations:

```python
from src.ldap_server.storage.json import FederatedJSONStorage

# Server configuration
storage = FederatedJSONStorage(json_files=[
    Path('/var/lib/ldap/users.json'),
    Path('/var/lib/ldap/groups.json')
])

# Write operations are called automatically by LDAP handlers
# when processing LDAP add/modify/delete requests
```

## See Also

- [Storage Backend Overview](README.md)
- [Federated JSON Storage](federated-json.md)
- [Memory Storage](../../api/storage/README.md#memory-storage)
- [Configuration Guide](../../guides/configuration.md)

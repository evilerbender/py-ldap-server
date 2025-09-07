# Storage Backend Documentation

The storage system in py-ldap-server provides flexible data persistence for LDAP directory information. The system is designed with a plugin architecture that allows multiple storage backends while maintaining a consistent interface.

## 🏗️ **Storage Architecture**

```
storage/
├── memory.py          # MemoryStorage - in-memory backend
└── json.py           # JSONStorage - file-based backend
```

The storage system follows a common interface pattern:
1. **Storage Interface**: Common methods across all backends
2. **Backend Implementations**: Specific storage technologies
3. **LDIF Integration**: ldaptor LDIFTreeEntry compatibility

## 💾 **Available Storage Backends**

### ✅ **Currently Implemented**

#### MemoryStorage (`memory.py`)
- **Purpose**: In-memory directory storage for development and testing
- **Performance**: Fastest access, no I/O overhead
- **Persistence**: Data lost on server restart
- **Use Cases**: Development, testing, temporary directories

#### JSONStorage (`json.py`)
- **Purpose**: File-based persistent storage with JSON format
- **Performance**: Good for small to medium directories
- **Persistence**: Data persists across server restarts
- **Use Cases**: Production deployments, configuration-based setups

### 🚧 **Planned Storage Backends** (Phase 3)

#### DatabaseStorage
- **Purpose**: SQL database backend for large directories
- **Performance**: Optimized for large datasets and concurrent access
- **Features**: Transactions, indexing, replication
- **Databases**: SQLite, PostgreSQL, MySQL

#### LDIFStorage
- **Purpose**: Standard LDIF file format backend
- **Performance**: Standards-compliant directory storage
- **Features**: Import/export compatibility, industry standard
- **Use Cases**: Migration from other LDAP servers

## 🎯 **Storage Interface**

All storage backends implement a common interface:

```python
class StorageBackend:
    def get_root(self) -> LDIFTreeEntry:
        """Return the root entry of the directory tree."""
        
    def cleanup(self) -> None:
        """Clean up resources and connections."""
        
    def find_entry_by_dn(self, dn: str) -> Optional[LDIFTreeEntry]:
        """Find entry by distinguished name."""
        
    def get_all_entries(self) -> List[LDIFTreeEntry]:
        """Return all entries in the directory."""
```

## 📚 **Storage Backend Details**

### 💿 **MemoryStorage**

#### Features
- **Fast Access**: No I/O operations, all data in RAM
- **Sample Data**: Pre-populated with realistic directory structure
- **Easy Testing**: Perfect for unit tests and development
- **Cleanup Support**: Proper resource management

#### Sample Directory Structure
```
dc=example,dc=com (root)
├── ou=people,dc=example,dc=com
│   ├── cn=admin,ou=people,dc=example,dc=com
│   ├── cn=alice,ou=people,dc=example,dc=com
│   └── cn=bob,ou=people,dc=example,dc=com
├── ou=groups,dc=example,dc=com
│   ├── cn=admins,ou=groups,dc=example,dc=com
│   └── cn=users,ou=groups,dc=example,dc=com
└── ou=services,dc=example,dc=com
    └── cn=ldap,ou=services,dc=example,dc=com
```

#### Usage Example
```python
from ldap_server.storage.memory import MemoryStorage

# Create storage with sample data
storage = MemoryStorage()

# Access root entry
root = storage.get_root()
print(f"Root DN: {root.dn}")

# Find specific user
user = storage.find_entry_by_dn("cn=alice,ou=people,dc=example,dc=com")
if user:
    print(f"User: {user.get('cn')[0]}")

# Clean up when done
storage.cleanup()
```

### 📄 **JSONStorage**

#### Features
- **Persistent Storage**: Data survives server restarts
- **Hot Reload**: Automatic file watching and reload
- **Password Security**: Automatic password upgrade to bcrypt
- **Error Handling**: Graceful handling of malformed files

#### JSON Format
```json
{
  "base_dn": "dc=example,dc=com",
  "entries": [
    {
      "dn": "dc=example,dc=com",
      "objectClass": ["dcObject", "organization"],
      "o": "Example Organization",
      "dc": "example"
    },
    {
      "dn": "cn=admin,ou=people,dc=example,dc=com",
      "objectClass": ["person", "organizationalPerson"],
      "cn": "admin",
      "sn": "Administrator",
      "userPassword": "$2b$12$hash..."
    }
  ]
}
```

#### Usage Example
```python
from ldap_server.storage.json import JSONStorage

# Create storage from JSON file
storage = JSONStorage(
    json_file="/path/to/directory.json",
    enable_watcher=True  # Enable hot reload
)

# Access directory data
root = storage.get_root()
entries = storage.get_all_entries()

# Storage automatically reloads when file changes
# No manual reload needed

# Clean up when done
storage.cleanup()
```

#### File Watching
JSONStorage includes automatic file monitoring:
```python
# Enable file watching (default: True)
storage = JSONStorage("data.json", enable_watcher=True)

# File changes are automatically detected and loaded
# Server continues running with new data
# Password upgrades are applied automatically
```

## 🔧 **Configuration**

### MemoryStorage Configuration
```python
# Basic setup
storage = MemoryStorage()

# Custom configuration
storage = MemoryStorage(
    base_dn="dc=mycompany,dc=com",
    create_sample_data=True
)
```

### JSONStorage Configuration
```python
# Basic file storage
storage = JSONStorage("directory.json")

# Advanced configuration
storage = JSONStorage(
    json_file="/etc/ldap/directory.json",
    enable_watcher=True,    # Hot reload
    auto_upgrade=True,      # Password upgrades
    backup_on_upgrade=True  # Backup before changes
)
```

## 🧪 **Testing**

### 🔬 **Test Coverage**
Storage backends have comprehensive test coverage:
- **MemoryStorage**: 6 test cases covering initialization and data access
- **JSONStorage**: 7 test cases covering file operations and error handling
- **Integration Tests**: Cross-component storage testing

### 🧪 **Test Examples**
```python
def test_memory_storage_initialization():
    """Test MemoryStorage creates sample data correctly."""
    storage = MemoryStorage()
    root = storage.get_root()
    
    assert root.dn.getText() == "dc=example,dc=com"
    assert len(storage.get_all_entries()) > 0
    
    storage.cleanup()

def test_json_storage_file_loading():
    """Test JSONStorage loads data from file."""
    # Create temporary JSON file
    data = {
        "base_dn": "dc=test,dc=com",
        "entries": [{"dn": "dc=test,dc=com", "objectClass": ["dcObject"]}]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        
    storage = JSONStorage(f.name, enable_watcher=False)
    root = storage.get_root()
    
    assert root.dn.getText() == "dc=test,dc=com"
    storage.cleanup()
```

## ⚡ **Performance Characteristics**

### 📊 **Backend Comparison**

| Feature | MemoryStorage | JSONStorage | DatabaseStorage* |
|---------|---------------|-------------|------------------|
| **Access Speed** | Fastest | Fast | Medium |
| **Persistence** | None | File-based | Database |
| **Scalability** | Limited by RAM | Medium | High |
| **Concurrency** | Single process | File locking | Full ACID |
| **Memory Usage** | High | Low | Low |
| **Startup Time** | Instant | Fast | Medium |

*DatabaseStorage planned for Phase 3

### 🚀 **Performance Tips**
```python
# For development - use MemoryStorage
storage = MemoryStorage()  # Fastest access

# For small production - use JSONStorage
storage = JSONStorage("data.json")  # Good balance

# For large production - use DatabaseStorage (Phase 3)
# storage = DatabaseStorage("postgresql://...")  # Best scalability
```

## 🔄 **Migration Between Backends**

### 📦 **Export/Import Utilities**
```python
def migrate_storage(source, target):
    """Migrate data between storage backends."""
    # Export from source
    entries = source.get_all_entries()
    
    # Import to target
    for entry in entries:
        target.add_entry(entry)  # (Phase 3 - write operations)

# Example: Memory to JSON migration
memory_storage = MemoryStorage()
json_storage = JSONStorage("exported_data.json")
migrate_storage(memory_storage, json_storage)
```

### 🔄 **Backup Strategies**
```python
# JSON backup (automatic)
storage = JSONStorage("data.json", backup_on_upgrade=True)
# Creates data.json.backup before password upgrades

# Manual backup
def backup_storage(storage, backup_file):
    """Create manual backup of storage."""
    entries = storage.get_all_entries()
    backup_data = {
        "base_dn": storage.base_dn,
        "entries": [entry.to_dict() for entry in entries],
        "backup_date": datetime.now().isoformat()
    }
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)
```

## 🔌 **Custom Storage Backends**

### 🧩 **Creating Custom Backends**
```python
class CustomStorage:
    """Example custom storage backend."""
    
    def __init__(self, connection_string):
        self.connection = self._connect(connection_string)
        self.root = self._load_root()
    
    def get_root(self):
        """Return root directory entry."""
        return self.root
    
    def cleanup(self):
        """Clean up resources."""
        if self.connection:
            self.connection.close()
    
    def find_entry_by_dn(self, dn):
        """Find entry by DN."""
        # Custom lookup logic
        return self._query_by_dn(dn)
    
    def _connect(self, connection_string):
        """Establish connection to storage."""
        # Custom connection logic
        pass
    
    def _load_root(self):
        """Load root entry from storage."""
        # Custom loading logic
        pass
```

### 🔧 **Integration Example**
```python
# Use custom storage backend
custom_storage = CustomStorage("redis://localhost:6379")

# Integrate with server
from ldap_server.factory import LDAPServerFactory
factory = LDAPServerFactory(storage=custom_storage)
```

## 🛡️ **Security Considerations**

### 🔒 **File Security (JSONStorage)**
```bash
# Secure file permissions
chmod 600 /etc/ldap/directory.json
chown ldap:ldap /etc/ldap/directory.json

# Secure directory
chmod 750 /etc/ldap
chown ldap:ldap /etc/ldap
```

### 🔐 **Password Security**
All storage backends integrate with password security:
```python
# Automatic password upgrade in JSONStorage
{
  "userPassword": "plain_text"  # Will be upgraded to bcrypt
}
# Becomes:
{
  "userPassword": "$2b$12$hash..."  # Secure bcrypt hash
}
```

### 🛡️ **Access Control** (Phase 3)
Future security features:
- **Row-level Security**: Database-level access control
- **Encryption at Rest**: Encrypted storage backends
- **Audit Logging**: Track all storage operations

## 🔗 **Related Documentation**

- **[💿 Memory Storage API](memory.md)** - Detailed MemoryStorage documentation
- **[📄 JSON Storage API](json.md)** - Detailed JSONStorage documentation
- **[🏗️ Architecture Guide](../../development/architecture.md)** - System design
- **[🧪 Testing Guide](../../development/testing.md)** - Storage testing

---

**Storage Status**: Phase 1 complete - Memory and JSON backends implemented  
**Performance**: Optimized for small to medium directories  
**Test Coverage**: 13 comprehensive test cases  
**Last Updated**: September 7, 2025

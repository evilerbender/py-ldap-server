# JSONStorage - Unified JSON Storage BackendThe `JSONStorage` class is a unified storage backend that supports both single-file and federated multi-file configurations for persistent LDAP directory data using JSON format.## 🎯 **Overview**JSONStorage provides:- **Unified Interface**: Single class supporting both single-file and federated modes- **Persistent Storage**: Data survives server restarts- **Atomic Operations**: Thread-safe writes with file locking- **Read-Only Support**: For externally managed configurations- **Federation**: Multiple JSON files merged into single directory tree- **Hot Reload**: Automatic file watching and reloading- **Security**: Automatic password hashing and upgrade## 🏗️ **Architecture**```JSONStorage├── Single File Mode     # Traditional single JSON file├── Federation Mode      # Multiple JSON files merged├── Read-Only Mode       # No modifications allowed├── AtomicJSONWriter     # Thread-safe atomic writes└── File Watcher         # Hot reload capability```## 🚀 **Quick Start**### Basic Usage```pythonfrom ldap_server.storage.json import JSONStorage# Single file modestorage = JSONStorage("directory.json")# Multi-file federation mode  storage = JSONStorage(json_files=[    "users.json",    "groups.json",     "services.json"])# Read-only modestorage = JSONStorage(    json_files=["config.json"],    read_only=True)```### Command Line Usage```bash# Single fileuv run py-ldap-server --json directory.json# Multiple files (federation)uv run py-ldap-server --json users.json groups.json services.json# Read-only modeuv run py-ldap-server --json config.json --read-only```## 📋 **API Reference**### Constructor```pythonclass JSONStorage:    def __init__(        self,        json_file: Optional[str] = None,        json_files: Optional[List[str]] = None,        read_only: bool = False,        enable_watcher: bool = True,        hash_plain_passwords: bool = True,        auto_upgrade: bool = True,        backup_on_upgrade: bool = True    ):```#### Parameters- **`json_file`** (str, optional): Path to single JSON file (traditional mode)- **`json_files`** (List[str], optional): List of JSON files for federation mode- **`read_only`** (bool): Enable read-only mode (prevents all write operations)- **`enable_watcher`** (bool): Enable automatic file watching and reload- **`hash_plain_passwords`** (bool): Automatically hash plain text passwords- **`auto_upgrade`** (bool): Automatically upgrade passwords during initialization- **`backup_on_upgrade`** (bool): Create backup before password upgrades### Core Methods#### Directory Access```pythondef get_root(self) -> LDIFTreeEntry:    """Return the root entry of the directory tree."""def find_entry_by_dn(self, dn: str) -> Optional[LDIFTreeEntry]:    """Find entry by distinguished name."""    def get_all_entries(self) -> List[LDIFTreeEntry]:    """Return all entries in the directory."""```#### Write Operations (Not Available in Read-Only Mode)```pythondef add_entry(self, dn: str, attributes: dict) -> bool:    """Add new entry to directory."""    def modify_entry(self, dn: str, new_attributes: dict) -> bool:    """Modify existing entry."""    def delete_entry(self, dn: str) -> bool:    """Delete entry from directory."""    def bulk_write_entries(self, entries: list) -> bool:    """Write multiple entries atomically."""```#### Lifecycle Management```pythondef cleanup(self) -> None:    """Clean up resources and stop file watching."""    def reload_data(self) -> None:    """Manually reload data from files."""```## 🎮 **Usage Modes**### 1. Single File ModeTraditional single JSON file storage:```python# Basic setupstorage = JSONStorage("directory.json")# Advanced configurationstorage = JSONStorage(    json_file="/etc/ldap/directory.json",    enable_watcher=True,    auto_upgrade=True)```**Use Cases:**- Simple deployments- Development and testing- Small directories (< 1000 entries)### 2. Federation ModeMultiple JSON files merged into single directory:```pythonstorage = JSONStorage(json_files=[    "/etc/ldap/users.json",      # User accounts    "/etc/ldap/groups.json",     # Group definitions    "/etc/ldap/services.json"    # Service accounts])```**Benefits:**- Organized data management- Separate team responsibilities- Easier maintenance and updates- Reduced merge conflicts### 3. Read-Only ModeFor externally managed configurations:```pythonstorage = JSONStorage(    json_files=["/etc/app/readonly_config.json"],    read_only=True,    enable_watcher=True  # Still monitors for external changes)```**Use Cases:**- Configuration management systems- Externally managed directories- Preventing accidental modifications- Compliance requirements## 📄 **JSON File Format**### Standard Format```json{  "base_dn": "dc=example,dc=com",  "entries": [    {      "dn": "dc=example,dc=com",      "objectClass": ["dcObject", "organization"],      "dc": "example",      "o": "Example Organization"    },    {      "dn": "cn=admin,ou=people,dc=example,dc=com",      "objectClass": ["person", "organizationalPerson"],      "cn": "admin",      "sn": "Administrator",      "userPassword": "admin"    }  ]}```### Required Fields- **`base_dn`**: Base distinguished name for the directory tree- **`entries`**: Array of LDAP entry objects  - **`dn`**: Distinguished name (unique identifier)  - **`objectClass`**: LDAP object classes (array)### Password Handling```json{  "dn": "cn=user,dc=example,dc=com",  "userPassword": "plaintext"  // Automatically upgraded to bcrypt}```After upgrade:```json{  "dn": "cn=user,dc=example,dc=com",   "userPassword": "$2b$12$hash..."  // Secure bcrypt hash}```## 🔄 **Federation Details**### How Federation Works1. **File Loading**: Each JSON file is loaded independently2. **Entry Merging**: All entries are merged into single directory tree3. **Conflict Resolution**: Later files override earlier entries with same DN4. **Base DN Handling**: First valid base_dn is used as tree root### Federation Example**users.json:**```json{  "base_dn": "dc=company,dc=com",  "entries": [    {"dn": "dc=company,dc=com", "objectClass": ["domain"]},    {"dn": "ou=users,dc=company,dc=com", "objectClass": ["organizationalUnit"]},    {"dn": "cn=alice,ou=users,dc=company,dc=com", "objectClass": ["person"]}  ]}```**groups.json:**```json{  "base_dn": "dc=company,dc=com",  "entries": [    {"dn": "ou=groups,dc=company,dc=com", "objectClass": ["organizationalUnit"]},    {"dn": "cn=staff,ou=groups,dc=company,dc=com", "objectClass": ["groupOfNames"]}  ]}```**Result:** Single directory tree with all entries merged under `dc=company,dc=com`.## ⚡ **Atomic Operations**### AtomicJSONWriterJSONStorage uses `AtomicJSONWriter` for thread-safe operations:```pythonfrom ldap_server.storage.json import AtomicJSONWriterfrom pathlib import Path# Direct usagewith AtomicJSONWriter(    Path("data.json"),    backup_enabled=True,    lock_timeout=10.0) as writer:    writer.write_json(data)```#### Features- **File Locking**: Prevents concurrent writes- **Atomic Writes**: Write to temp file, then atomic rename- **Automatic Backups**: Created before each write- **Error Recovery**: Rollback on failure- **Thread Safety**: Multiple threads handled safely### Write Operation Example```pythonstorage = JSONStorage("directory.json")# Add new user (atomic operation)success = storage.add_entry(    "cn=john,ou=users,dc=example,dc=com",    {
        "cn": ["john"],
        "sn": ["Doe"],
        "objectClass": ["person"],
        "userPassword": ["password123"]  # Will be hashed
    }
)

if success:
    print("User added successfully")
    # File was atomically updated with proper locking
else:
    print("Failed to add user")
```

## 📊 **File Watching & Hot Reload**

### Automatic File Monitoring

```python
# Enable file watching (default)
storage = JSONStorage(
    json_files=["users.json", "groups.json"],
    enable_watcher=True
)

# File changes are automatically detected:
# 1. File modification detected
# 2. Data reloaded from all files
# 3. Directory tree rebuilt
# 4. Password upgrades applied if needed
# 5. Server continues with new data
```

### Manual Reload

```python
# Force reload from files
storage.reload_data()

# Useful for:
# - Debugging file changes
# - Scheduled reloads
# - Error recovery
```

## 🔐 **Security Features**

### Password Security

```python
# Automatic password hashing
storage = JSONStorage(
    "data.json",
    hash_plain_passwords=True,  # Default: True
    auto_upgrade=True,          # Upgrade on startup
    backup_on_upgrade=True      # Backup before upgrade
)
```

### Password Upgrade Process

1. **Detection**: Plain text passwords identified
2. **Backup**: Original file backed up (if enabled)
3. **Hashing**: bcrypt applied with secure salt
4. **Update**: File atomically updated
5. **Verification**: Changes verified

### File Permissions

```bash
# Secure file permissions
chmod 600 /etc/ldap/*.json
chown ldap:ldap /etc/ldap/*.json

# Secure directory
chmod 750 /etc/ldap
chown ldap:ldap /etc/ldap
```

## 🧪 **Testing & Validation**

### Unit Tests

```python
def test_single_file_mode():
    """Test JSONStorage with single file."""
    storage = JSONStorage("test.json", enable_watcher=False)
    root = storage.get_root()
    assert root is not None
    storage.cleanup()

def test_federation_mode():
    """Test JSONStorage with multiple files."""
    storage = JSONStorage(
        json_files=["users.json", "groups.json"],
        enable_watcher=False
    )
    entries = storage.get_all_entries()
    assert len(entries) > 0
    storage.cleanup()

def test_read_only_mode():
    """Test read-only mode prevents writes."""
    storage = JSONStorage(
        json_files=["config.json"],
        read_only=True,
        enable_watcher=False
    )
    
    # Write operations should fail
    success = storage.add_entry("cn=test", {"cn": ["test"]})
    assert success is False
    storage.cleanup()
```

### Integration Tests

```bash
# Test with real LDAP clients
ldapsearch -x -H ldap://localhost:1389 -b "dc=example,dc=com"

# Test authentication
ldapsearch -x -H ldap://localhost:1389 \
    -D "cn=admin,dc=example,dc=com" -w "admin" "(cn=*)"
```

## 🚀 **Performance Characteristics**

### Benchmarks

| Operation | Single File | Federation | Notes |
|-----------|-------------|------------|-------|
| **Startup Time** | Fast | Medium | Multiple file parsing |
| **Memory Usage** | Low | Medium | All entries in memory |
| **Search Speed** | Fast | Fast | In-memory tree structure |
| **Write Speed** | Medium | Medium | Atomic file operations |
| **Reload Time** | Fast | Medium | File watching overhead |

### Optimization Tips

```python
# For better performance
storage = JSONStorage(
    json_files=["data.json"],
    enable_watcher=False,      # Disable if not needed
    auto_upgrade=False,        # Skip if passwords already hashed
    backup_on_upgrade=False    # Disable if backups not needed
)

# For production use
storage = JSONStorage(
    json_files=["users.json", "groups.json"],
    enable_watcher=True,       # Hot reload
    auto_upgrade=True,         # Security
    backup_on_upgrade=True,    # Data protection
    read_only=False            # Allow modifications
)
```

## 🔗 **Related Documentation**

- **[🏗️ Storage Architecture](README.md)** - Storage system overview
- **[💿 Memory Storage](memory.md)** - In-memory storage backend
- **[⚙️ Configuration Guide](../../guides/configuration.md)** - Server configuration
- **[🔐 Authentication Guide](../../guides/authentication.md)** - User authentication
- **[🧪 Testing Guide](../../development/testing.md)** - Testing strategies

---

**Implementation Status**: Complete and Production Ready  
**Test Coverage**: 18 comprehensive test cases  
**Performance**: Optimized for small to medium directories (< 10k entries)  
**Last Updated**: December 2024

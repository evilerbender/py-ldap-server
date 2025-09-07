# Configuration Examples

This directory contains example JSON configuration files for the py-ldap-server unified JSON storage backend.

## Single File Configuration

### basic.json
A complete directory structure in a single file suitable for simple deployments.

```bash
# Start server with single file
uv run py-ldap-server --json docs/examples/configuration/basic.json
```

## Federated Multi-File Configuration

The unified JSON storage backend supports federation across multiple files, allowing you to organize your directory data for easier management.

### federated_users.json
Contains domain root and user account entries.

### federated_groups.json  
Contains group organizational units and group entries.

```bash
# Start server with federated configuration
uv run py-ldap-server --json docs/examples/configuration/federated_users.json docs/examples/configuration/federated_groups.json
```

## Read-Only Mode

For externally managed configurations, you can run the server in read-only mode:

```bash
# Read-only mode prevents any write operations
uv run py-ldap-server --json /etc/ldap/readonly_config.json --read-only
```

## Configuration Features

- **Automatic password hashing**: Plain text passwords are automatically upgraded to bcrypt
- **Hot reload**: File changes are automatically detected and reloaded
- **Atomic writes**: All modifications are atomic with file locking
- **Automatic backups**: Created before password upgrades and modifications
- **Federation**: Multiple files are merged into a single directory tree
- **Read-only support**: Prevents modifications when consuming external configs

## File Format

All JSON files follow the same structure:

```json
{
  "base_dn": "dc=example,dc=com",
  "entries": [
    {
      "dn": "dc=example,dc=com",
      "objectClass": ["dcObject", "organization"],
      "dc": "example",
      "o": "Example Organization"
    }
  ]
}
```

### Required Fields

- `base_dn`: The base distinguished name for the directory
- `entries`: Array of LDAP entry objects
- `dn`: Distinguished name for each entry
- `objectClass`: LDAP object classes (array)

### Optional Fields

- Any valid LDAP attributes as defined by the object classes
- `userPassword`: Automatically hashed with bcrypt if in plain text

## Example Usage

### Single File Mode
```bash
# Basic setup
uv run py-ldap-server --json basic.json

# With custom port
uv run py-ldap-server --json basic.json --port 1389
```

### Federation Mode
```bash
# Multiple files merged together
uv run py-ldap-server --json federated_users.json federated_groups.json

# Read-only federation
uv run py-ldap-server --json federated_users.json federated_groups.json --read-only
```

## Related Documentation

- **[� Quick Start Guide](../guides/quick-start.md)** - Get started quickly
- **[⚙️ Configuration Guide](../guides/configuration.md)** - Detailed configuration
- **[� JSON Storage API](../api/storage/json.md)** - Technical API reference

---

**Last Updated**: December 2024

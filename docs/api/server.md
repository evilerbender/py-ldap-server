# Server API

This document covers the `LDAPServerService` class and main server implementation in py-ldap-server.

## 🎛️ **LDAPServerService Class**

The `LDAPServerService` class is the main entry point for running an LDAP server. It manages the Twisted reactor, server factory, and all server lifecycle operations.

### Class Definition

```python
class LDAPServerService:
    """Main LDAP server service class built on Twisted reactor"""
    
    def __init__(self, port=1389, bind_host='localhost', storage=None, 
                 debug=False, allow_anonymous=True):
        """Initialize LDAP server service"""
        
    def start(self) -> None:
        """Start the LDAP server"""
        
    def stop(self) -> None:
        """Stop the LDAP server gracefully"""
        
    def get_server_info(self) -> dict:
        """Get server status and configuration"""
```

### 🏗️ **Constructor**

#### `LDAPServerService(port=1389, bind_host='localhost', storage=None, debug=False, allow_anonymous=True)`

Creates a new LDAP server service instance.

**Parameters:**
- `port` (int): Port to bind LDAP server (default: 1389)
  - Standard LDAP port: 389 (requires root on Unix)
  - Secure LDAP port: 636 (LDAPS)
  - Development port: 1389 (non-privileged)
- `bind_host` (str): Host interface to bind (default: 'localhost')
  - 'localhost': Local connections only
  - '0.0.0.0': All interfaces
  - Specific IP: Bind to specific interface
- `storage`: Storage backend instance (default: MemoryStorage)
  - MemoryStorage: In-memory directory data
  - JSONStorage: File-based directory data
  - Custom: Any storage implementing the interface
- `debug` (bool): Enable debug logging (default: False)
- `allow_anonymous` (bool): Allow anonymous LDAP binds (default: True)

**Example:**
```python
from ldap_server.server import LDAPServerService
from ldap_server.storage.memory import MemoryStorage
from ldap_server.storage.json import JSONStorage

# Basic server with memory storage
server = LDAPServerService()

# Production server with JSON storage
storage = JSONStorage(json_file='directory.json')
server = LDAPServerService(
    port=389,
    bind_host='0.0.0.0',
    storage=storage,
    debug=False,
    allow_anonymous=False
)

# Development server with debugging
dev_server = LDAPServerService(
    port=1389,
    bind_host='localhost', 
    debug=True
)
```

### 🚀 **Methods**

#### `start() -> None`

Starts the LDAP server and begins listening for connections.

**Behavior:**
- Initializes Twisted reactor
- Creates LDAPServerFactory with configuration
- Binds to specified host and port
- Registers signal handlers for graceful shutdown
- Starts reactor event loop (blocking call)

**Example:**
```python
server = LDAPServerService(port=1389, debug=True)

try:
    print("Starting LDAP server...")
    server.start()  # Blocks until server stops
except KeyboardInterrupt:
    print("Server interrupted by user")
except Exception as e:
    print(f"Server error: {e}")
```

**Output Example:**
```
2025-09-07 10:30:15 [INFO] LDAP Server starting on localhost:1389
2025-09-07 10:30:15 [INFO] Storage backend: MemoryStorage
2025-09-07 10:30:15 [INFO] Anonymous access: Enabled
2025-09-07 10:30:15 [INFO] Debug mode: Enabled
2025-09-07 10:30:15 [INFO] Server ready for connections
```

#### `stop() -> None`

Stops the LDAP server gracefully.

**Behavior:**
- Closes all active LDAP connections
- Stops accepting new connections
- Cleans up storage backend resources
- Stops Twisted reactor
- Exits server process

**Example:**
```python
# Graceful shutdown in signal handler
import signal

def signal_handler(signum, frame):
    print("Received shutdown signal")
    server.stop()
    
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
```

#### `get_server_info() -> dict`

Returns server status and configuration information.

**Returns:**
- `dict`: Server information including status, configuration, and statistics

**Information Included:**
- Server status (running, stopped, starting)
- Configuration (port, host, storage type)
- Connection statistics
- Authentication settings
- Uptime and performance metrics

**Example:**
```python
server = LDAPServerService(port=1389, debug=True)
info = server.get_server_info()

print(f"Status: {info['status']}")
print(f"Port: {info['port']}")
print(f"Host: {info['bind_host']}")
print(f"Storage: {info['storage_type']}")
print(f"Connections: {info['active_connections']}")
print(f"Uptime: {info['uptime_seconds']}s")
```

**Sample Output:**
```python
{
    'status': 'running',
    'port': 1389,
    'bind_host': 'localhost',
    'storage_type': 'MemoryStorage',
    'debug': True,
    'allow_anonymous': True,
    'active_connections': 3,
    'total_connections': 15,
    'successful_binds': 12,
    'failed_binds': 2,
    'uptime_seconds': 3600,
    'version': '1.0.0'
}
```

## 🔧 **Configuration**

### Environment Variables

Configure server via environment variables:

```bash
# Server binding
export LDAP_PORT=1389
export LDAP_BIND_HOST=localhost

# Security settings
export LDAP_ALLOW_ANONYMOUS=true
export LDAP_DEBUG=false

# Storage configuration
export LDAP_STORAGE_TYPE=memory
export LDAP_JSON_FILE=directory.json

# Performance tuning
export LDAP_MAX_CONNECTIONS=100
export LDAP_CONNECTION_TIMEOUT=300
```

### Configuration File Support

```python
import os
from ldap_server.server import LDAPServerService

# Load configuration from environment
config = {
    'port': int(os.getenv('LDAP_PORT', 1389)),
    'bind_host': os.getenv('LDAP_BIND_HOST', 'localhost'),
    'debug': os.getenv('LDAP_DEBUG', 'false').lower() == 'true',
    'allow_anonymous': os.getenv('LDAP_ALLOW_ANONYMOUS', 'true').lower() == 'true'
}

server = LDAPServerService(**config)
```

## 🏗️ **Architecture Integration**

### Component Relationships

```python
LDAPServerService
├── Twisted Reactor (event loop)
├── LDAPServerFactory (connection factory)
│   └── CustomLDAPServer (protocol handler per connection)
│       ├── BindHandler (authentication)
│       │   └── PasswordManager (password security)
│       └── StorageBackend (data storage)
│           ├── MemoryStorage
│           └── JSONStorage
```

### Initialization Flow

```python
# Server startup sequence
def start(self):
    1. self._setup_logging()        # Configure logging
    2. self._initialize_storage()   # Setup storage backend
    3. self._create_factory()       # Create LDAP factory
    4. self._setup_signal_handlers() # Handle SIGTERM/SIGINT
    5. self._bind_port()            # Bind to network port
    6. self._start_reactor()        # Start Twisted reactor
```

### Connection Lifecycle

```
Client Connection → LDAPServerFactory.buildProtocol()
                 → CustomLDAPServer instance created
                 → LDAP protocol handling begins
                 → Client operations (bind, search, etc.)
                 → Connection cleanup on disconnect
```

## 🛡️ **Security Features**

### Network Security
- **Bind Host Control**: Restrict server to specific interfaces
- **Port Configuration**: Use non-privileged ports for development
- **Connection Limits**: Prevent resource exhaustion (future)

### Access Control
- **Anonymous Access**: Configurable anonymous bind support
- **Authentication Required**: Force authentication for write operations
- **Debug Mode**: Disable debug logging in production

### Error Handling
- **Graceful Degradation**: Server continues on non-fatal errors
- **Resource Cleanup**: Proper cleanup on shutdown
- **Signal Handling**: Respond to system shutdown signals

## 🧪 **Testing**

### Unit Tests

The server is tested in `tests/unit/test_server.py`:

```python
def test_server_initialization():
    """Test server initialization with different configurations"""
    server = LDAPServerService(port=1389, debug=True)
    
    assert server.port == 1389
    assert server.bind_host == 'localhost'
    assert server.debug is True
    assert server.allow_anonymous is True

def test_server_info():
    """Test server information retrieval"""
    server = LDAPServerService()
    info = server.get_server_info()
    
    assert 'status' in info
    assert 'port' in info
    assert 'storage_type' in info
    assert info['port'] == 1389

def test_custom_storage():
    """Test server with custom storage backend"""
    from ldap_server.storage.json import JSONStorage
    
    storage = JSONStorage(json_file='test.json')
    server = LDAPServerService(storage=storage)
    
    assert server.storage_backend == storage
    assert isinstance(server.storage_backend, JSONStorage)
```

### Integration Tests

```python
def test_server_start_stop():
    """Test server lifecycle (start/stop)"""
    server = LDAPServerService(port=1389)
    
    # Start server in background thread
    import threading
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to start
    time.sleep(0.5)
    
    # Test connection
    import ldap
    conn = ldap.initialize('ldap://localhost:1389')
    result = conn.simple_bind_s('', '')  # Anonymous bind
    
    # Stop server
    server.stop()
    assert True  # Server started and stopped successfully
```

## 🚀 **Usage Examples**

### Basic Development Server

```python
from ldap_server.server import LDAPServerService

# Simple development server
def run_dev_server():
    server = LDAPServerService(
        port=1389,
        bind_host='localhost',
        debug=True
    )
    
    print("Starting development LDAP server...")
    print("Connect with: ldapsearch -x -H ldap://localhost:1389")
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()

if __name__ == '__main__':
    run_dev_server()
```

### Production Server with JSON Storage

```python
from ldap_server.server import LDAPServerService
from ldap_server.storage.json import JSONStorage
import signal
import sys

def create_production_server():
    # Initialize JSON storage
    storage = JSONStorage(json_file='/etc/ldap/directory.json')
    
    # Create production server
    server = LDAPServerService(
        port=389,              # Standard LDAP port (requires root)
        bind_host='0.0.0.0',   # Listen on all interfaces
        storage=storage,
        debug=False,           # Disable debug in production
        allow_anonymous=False  # Require authentication
    )
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"Received signal {signum}, shutting down...")
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    return server

def main():
    server = create_production_server()
    
    print("Starting production LDAP server...")
    print(f"Listening on all interfaces port 389")
    print(f"Storage: JSON file backend")
    print(f"Authentication required for all operations")
    
    try:
        server.start()
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### Server with Custom Configuration

```python
import os
from ldap_server.server import LDAPServerService
from ldap_server.storage.memory import MemoryStorage
from ldap_server.storage.json import JSONStorage

def create_configured_server():
    # Load configuration from environment
    port = int(os.getenv('LDAP_PORT', 1389))
    host = os.getenv('LDAP_BIND_HOST', 'localhost')
    debug = os.getenv('LDAP_DEBUG', 'false').lower() == 'true'
    storage_type = os.getenv('LDAP_STORAGE_TYPE', 'memory')
    
    # Initialize storage backend
    if storage_type == 'json':
        json_file = os.getenv('LDAP_JSON_FILE', 'directory.json')
        storage = JSONStorage(json_file=json_file)
    else:
        storage = MemoryStorage()
    
    # Create server
    server = LDAPServerService(
        port=port,
        bind_host=host,
        storage=storage,
        debug=debug
    )
    
    return server

# Usage
server = create_configured_server()
info = server.get_server_info()
print(f"Server configured: {info}")
```

## 📋 **Error Handling**

### Common Exceptions

```python
from ldap_server.server import LDAPServerService
import socket

try:
    server = LDAPServerService(port=389)  # Privileged port
    server.start()
except PermissionError:
    print("Error: Port 389 requires root privileges")
    print("Try using port 1389 for development")
except socket.error as e:
    print(f"Network error: {e}")
    print("Check if port is already in use")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Graceful Error Recovery

```python
def robust_server_start(port=1389):
    """Start server with fallback port if primary fails"""
    for attempt_port in [port, port + 1, port + 2]:
        try:
            server = LDAPServerService(port=attempt_port)
            server.start()
            break
        except socket.error:
            print(f"Port {attempt_port} unavailable, trying next...")
            continue
    else:
        raise RuntimeError("Could not find available port")
```

## 🔄 **Future Enhancements** (Phase 2+)

### Advanced Features
- **TLS/SSL Support**: LDAPS on port 636
- **Connection Pooling**: Efficient connection management
- **Rate Limiting**: Prevent abuse and DoS attacks
- **Monitoring**: Metrics and health check endpoints

### Performance Optimizations
- **Async Operations**: Non-blocking LDAP operations
- **Connection Caching**: Reuse established connections
- **Memory Management**: Efficient memory usage for large directories
- **Load Balancing**: Multiple server instance support

### Management Features
- **Hot Reload**: Configuration changes without restart
- **Admin Interface**: Web-based administration
- **Backup/Restore**: Directory data management
- **Clustering**: Multi-node LDAP server deployment

## 🔗 **Integration Points**

### With LDAPServerFactory
```python
# Server creates and manages factory
class LDAPServerService:
    def start(self):
        self.factory = LDAPServerFactory(
            storage_backend=self.storage_backend,
            debug=self.debug
        )
        reactor.listenTCP(self.port, self.factory, interface=self.bind_host)
```

### With Storage Backends
```python
# Server initializes storage and passes to factory
server = LDAPServerService(storage=JSONStorage('data.json'))
# Storage is automatically configured and passed to all components
```

### With Command Line Interface
```python
# Server integrates with CLI entry point
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=1389)
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--debug', action='store_true')
    
    args = parser.parse_args()
    
    server = LDAPServerService(
        port=args.port,
        bind_host=args.host,
        debug=args.debug
    )
    server.start()
```

## 📚 **Related Documentation**

- **[🏭 Factory API](factory.md)** - LDAPServerFactory and CustomLDAPServer
- **[🔐 Authentication](auth/README.md)** - Authentication system integration
- **[💾 Storage](storage/README.md)** - Storage backend integration
- **[🏗️ Architecture Guide](../development/architecture.md)** - System design overview
- **[🚀 Deployment Guide](../deployment/README.md)** - Production deployment

---

**Component**: Server Service  
**Phase**: 1 (Complete)  
**Last Updated**: September 7, 2025

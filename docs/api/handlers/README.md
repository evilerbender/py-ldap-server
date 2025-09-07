# Protocol Handlers Documentation

The protocol handlers system in py-ldap-server will provide modular LDAP message processing for different types of LDAP operations. This system is planned for Phase 2 and beyond.

## 🚧 **Development Status: Phase 2**

The handlers system is currently under development as part of Phase 2. The basic LDAP protocol handling is currently embedded in the main server classes, but will be refactored into modular handlers.

## 🎯 **Planned Architecture**

```
handlers/
├── README.md           # This file - handlers overview
├── search.py           # Advanced search operation handlers
├── bind.py             # Enhanced bind operation handlers  
├── modify.py           # Add/modify/delete operation handlers (Phase 3)
├── base.py             # Base handler interface and utilities
└── filters.py          # LDAP filter parsing and evaluation
```

## 🔧 **Handler Categories**

### 🔍 **Search Handlers** (Phase 2)
Advanced LDAP search operation processing:
- **Filter Parsing**: RFC 4515 LDAP filter syntax
- **Scope Processing**: Base, one-level, and subtree search
- **Result Processing**: Efficient result set handling
- **Pagination**: Large result set paging controls

### 🔑 **Enhanced Bind Handlers** (Phase 2)
Extended authentication operation handling:
- **Multiple Auth Methods**: Simple, SASL, certificate-based
- **Security Features**: Rate limiting, audit logging
- **Error Handling**: Detailed error responses and logging
- **Session Management**: Authentication state tracking

### ✏️ **Modify Handlers** (Phase 3)
Directory modification operation processing:
- **Add Operations**: Create new directory entries
- **Modify Operations**: Update existing entry attributes
- **Delete Operations**: Remove entries with integrity checking
- **Transaction Support**: Atomic operations and rollback

## 📋 **Current Implementation**

### ✅ **Existing Handler Logic**
Currently integrated into main server classes:

#### Basic Search (in CustomLDAPServer)
```python
# Current basic search handling in server.py
def handle_LDAPSearchRequest(self, request, controls, reply):
    """Handle LDAP search requests - basic implementation."""
    # Basic search logic currently in main server
    # Will be moved to dedicated search handlers in Phase 2
```

#### Basic Bind (in BindHandler)
```python
# Current bind handling in auth/bind.py
class BindHandler:
    def handle_bind(self, dn, password, storage):
        """Current basic bind handling."""
        # Will be enhanced and moved to handlers/ in Phase 2
```

## 🚀 **Phase 2 Development Plan**

### 🔍 **Search Handler Development**
```python
# Planned search handler interface
class SearchHandler:
    def handle_search(self, base_dn, scope, filter_expr, attributes):
        """Handle LDAP search with advanced features."""
        
    def parse_filter(self, filter_string):
        """Parse RFC 4515 LDAP filter syntax."""
        
    def evaluate_filter(self, entry, filter_obj):
        """Evaluate filter against directory entry."""
        
    def apply_scope(self, base_entry, scope, entries):
        """Apply search scope to result set."""
```

### 🔧 **Filter Parser Development**
```python
# Planned filter parsing system
class LDAPFilterParser:
    def parse(self, filter_string):
        """Parse LDAP filter into AST."""
        
    def evaluate(self, filter_ast, entry):
        """Evaluate filter AST against entry."""
        
    def optimize(self, filter_ast):
        """Optimize filter for performance."""
```

## 📊 **Handler Integration**

### 🔌 **Server Integration**
Handlers will integrate with the main server:
```python
# Planned server integration
class CustomLDAPServer(LDAPServer):
    def __init__(self):
        self.search_handler = SearchHandler()
        self.bind_handler = EnhancedBindHandler()
        self.modify_handler = ModifyHandler()  # Phase 3
        
    def handle_LDAPSearchRequest(self, request, controls, reply):
        """Delegate to search handler."""
        return self.search_handler.handle_search(
            base_dn=request.baseObject,
            scope=request.scope,
            filter_expr=request.filter,
            attributes=request.attributes
        )
```

### 💾 **Storage Integration**
Handlers will work with storage backends:
```python
# Handler-storage integration
class SearchHandler:
    def __init__(self, storage):
        self.storage = storage
        
    def search_entries(self, base_dn, scope, filter_obj):
        """Search entries using storage backend."""
        base_entry = self.storage.find_entry_by_dn(base_dn)
        candidates = self._get_scope_candidates(base_entry, scope)
        return [e for e in candidates if self._matches_filter(e, filter_obj)]
```

## 🎯 **Handler Features**

### 🔍 **Advanced Search Features** (Phase 2)
- **Complex Filters**: AND, OR, NOT operations with nested expressions
- **Wildcard Matching**: Substring and wildcard attribute matching
- **Case Sensitivity**: Configurable case-sensitive/insensitive matching
- **Attribute Selection**: Efficient attribute filtering in results

### ⚡ **Performance Features** (Phase 2)
- **Filter Optimization**: Reorder filter operations for efficiency
- **Result Caching**: Cache search results for repeated queries
- **Lazy Loading**: Load entries on-demand for large result sets
- **Index Support**: Optimize searches with attribute indexing

### 🛡️ **Security Features** (Phase 3)
- **Access Control**: Fine-grained permission checking
- **Rate Limiting**: Prevent abuse of search operations
- **Audit Logging**: Track all LDAP operations
- **Input Validation**: Prevent injection and malformed requests

## 🧪 **Testing Strategy**

### 📋 **Handler Testing Plan**
Each handler will have comprehensive test coverage:
```python
# Example test structure
class TestSearchHandler:
    def test_simple_filter_parsing(self):
        """Test basic filter parsing."""
        
    def test_complex_filter_evaluation(self):
        """Test nested AND/OR filter evaluation."""
        
    def test_scope_application(self):
        """Test base/one/subtree scope handling."""
        
    def test_performance_optimization(self):
        """Test filter optimization."""
```

### 🔧 **Integration Testing**
```python
# Integration test example
def test_search_handler_integration():
    """Test search handler with real storage backend."""
    storage = MemoryStorage()
    handler = SearchHandler(storage)
    
    results = handler.handle_search(
        base_dn="dc=example,dc=com",
        scope=SCOPE_SUBTREE,
        filter_expr="(&(objectClass=person)(cn=alice*))",
        attributes=["cn", "mail"]
    )
    
    assert len(results) > 0
    assert all("cn" in entry for entry in results)
```

## 🔧 **Configuration**

### ⚙️ **Handler Configuration** (Planned)
```python
# Handler configuration system
HANDLER_CONFIG = {
    "search": {
        "max_results": 1000,
        "enable_caching": True,
        "cache_ttl": 300,
        "filter_optimization": True
    },
    "bind": {
        "rate_limit": 10,  # per minute
        "audit_logging": True,
        "session_timeout": 3600
    },
    "modify": {
        "enable_transactions": True,
        "backup_on_modify": True,
        "validate_schema": True
    }
}
```

## 🚀 **Migration Plan**

### 📋 **Phase 2 Migration Steps**
1. **Extract Search Logic**: Move search handling from server to dedicated handler
2. **Implement Filter Parser**: Create RFC 4515 compliant filter parser
3. **Add Advanced Search**: Implement one-level and subtree search scopes
4. **Performance Optimization**: Add caching and optimization features
5. **Testing**: Comprehensive test coverage for all handler functionality

### 🔄 **Backward Compatibility**
The handler system will maintain backward compatibility:
- **Existing APIs**: Current server interfaces will continue to work
- **Gradual Migration**: Handlers will be introduced incrementally
- **Configuration**: Existing configuration will be preserved

## 🔗 **Related Documentation**

- **[🔍 Search Operations](../../guides/ldap-operations.md#search)** - User guide for search operations
- **[🎛️ Server API](../server.md)** - Main server documentation
- **[🏗️ Architecture Guide](../../development/architecture.md)** - System architecture
- **[📋 Phase 2 Todos](../../PHASE2_TODOS.md)** - Development roadmap

## 💡 **Contributing**

The handler system is a key focus of Phase 2 development. Contributions are welcome:

### 🎯 **Current Priorities**
1. **LDAP Filter Parser** - RFC 4515 implementation
2. **Search Handler** - Advanced search operation handling
3. **Performance Optimization** - Caching and indexing

### 📝 **How to Contribute**
1. **Review Phase 2 Todos**: Check current development priorities
2. **Design Discussion**: Discuss handler design in GitHub issues
3. **Implementation**: Submit PRs following coding standards
4. **Testing**: Ensure comprehensive test coverage

---

**Development Status**: Phase 2 planning complete, implementation in progress  
**Priority**: LDAP filter parsing and advanced search operations  
**Timeline**: Phase 2 (Core LDAP Operations)  
**Last Updated**: September 7, 2025

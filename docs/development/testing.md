# Testing Guide

This guide covers testing practices, tools, and strategies for py-ldap-server development. Our testing approach ensures code quality, reliability, and RFC compliance.

## 🧪 **Testing Philosophy**

### 🎯 **Testing Principles**
- **Comprehensive Coverage**: All critical components have tests
- **Fast Execution**: Tests run quickly for developer productivity
- **Reliable Results**: Tests are deterministic and isolated
- **Clear Purpose**: Each test has a single, clear objective

### 📊 **Current Test Coverage**
```
Total Tests: 42 comprehensive test cases
├── Authentication: 13 tests (test_bind.py, test_password.py)
├── Storage: 13 tests (test_server.py, test_json_storage.py)  
├── Server Core: 6 tests (test_server.py)
└── Password Security: 10 tests (test_password.py)

Success Rate: 100% (42/42 passing)
Execution Time: ~14 seconds
```

## 🚀 **Running Tests**

### 🔧 **Basic Test Execution**
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_server.py -v

# Run specific test method
pytest tests/unit/test_bind.py::TestBindHandler::test_simple_bind_success -v

# Run tests with coverage
pytest tests/ --cov=src/ldap_server --cov-report=html

# Run tests in parallel (if pytest-xdist installed)
pytest tests/ -n auto
```

### 📊 **Test Output Examples**
```bash
# Successful test run
$ pytest tests/ -v
=============================================== test session starts ===============================================
platform linux -- Python 3.12.11, pytest-8.4.2, pluggy-1.6.0 -- /opt/py-ldap-server/.venv/bin/python
cachedir: .pytest_cache
rootdir: /opt/py-ldap-server
configfile: pyproject.toml
collected 42 items                                                                                                

tests/unit/test_bind.py::TestBindHandler::test_anonymous_bind PASSED                                        [  2%]
tests/unit/test_bind.py::TestBindHandler::test_simple_bind_success PASSED                                   [  4%]
...
tests/unit/test_server.py::TestCustomLDAPServer::test_protocol_initialization PASSED                        [100%]

=============================================== 42 passed in 13.85s ===============================================
```

### 🐛 **Debugging Failed Tests**
```bash
# Run with detailed output
pytest tests/ -v -s

# Stop on first failure
pytest tests/ -x

# Drop into debugger on failure
pytest tests/ --pdb

# Run only failed tests from last run
pytest tests/ --lf
```

## 📁 **Test Structure**

### 🗂️ **Test Organization**
```
tests/
├── __init__.py
├── unit/                       # Unit tests for individual components
│   ├── __init__.py
│   ├── mock_storage.py         # Shared test utilities
│   ├── test_bind.py            # Authentication and bind tests
│   ├── test_json_storage.py    # JSON storage backend tests
│   ├── test_password.py        # Password security tests
│   └── test_server.py          # Server and factory tests
├── integration/                # Integration tests (Phase 2)
│   └── test_ldap_clients.py    # Real LDAP client compatibility
└── fixtures/                   # Test data and configurations
    ├── sample_directory.json   # Test LDAP directory data
    └── test_configs/           # Test configuration files
```

### 🧪 **Test Categories**

#### 🔬 **Unit Tests** (Current - 42 tests)
Test individual components in isolation:
- **Server Components**: Factory, protocol, and server initialization
- **Authentication**: Bind operations and password management
- **Storage Backends**: Memory and JSON storage functionality
- **Security**: Password hashing and verification

#### 🔗 **Integration Tests** (Phase 2)
Test component interactions:
- **LDAP Client Compatibility**: ldapsearch, Apache Directory Studio
- **End-to-End Workflows**: Complete LDAP operation flows
- **Storage Integration**: Cross-backend functionality

#### 🚀 **Performance Tests** (Phase 3)
Test system performance:
- **Load Testing**: Multiple concurrent connections
- **Stress Testing**: Large directory sizes
- **Benchmarking**: Operation latency and throughput

#### 🛡️ **Security Tests** (Phase 3)
Test security features:
- **Authentication Security**: Brute force protection
- **Input Validation**: Injection attack prevention
- **Access Control**: Permission enforcement

## 🔧 **Writing Tests**

### 📋 **Test Writing Guidelines**

#### 1️⃣ **Test Structure (AAA Pattern)**
```python
def test_simple_bind_success(self):
    """Test successful simple bind authentication."""
    # Arrange - Set up test data and conditions
    handler = BindHandler()
    storage = MemoryStorage()
    dn = "cn=admin,ou=people,dc=example,dc=com"
    password = "admin"
    
    # Act - Execute the operation being tested
    result = handler.handle_bind(dn, password, storage)
    
    # Assert - Verify the expected outcome
    assert result is True
```

#### 2️⃣ **Test Naming Convention**
```python
# Pattern: test_{component}_{scenario}_{expected_outcome}
def test_password_verification_correct_password_returns_true(self):
def test_json_storage_malformed_file_raises_exception(self):
def test_bind_handler_invalid_dn_returns_false(self):
```

#### 3️⃣ **Test Documentation**
```python
def test_json_storage_file_watching_reloads_data(self):
    """Test that JSONStorage automatically reloads when file changes.
    
    This test verifies the file watching functionality by:
    1. Creating a JSONStorage instance with file watching enabled
    2. Modifying the JSON file externally
    3. Verifying that the storage automatically reloads the new data
    
    This ensures hot reload functionality works correctly in production.
    """
```

### 🛠️ **Test Utilities and Fixtures**

#### 📦 **Shared Test Utilities**
```python
# tests/unit/mock_storage.py
class MockStorage:
    """Mock storage backend for testing without real data."""
    
    def __init__(self, entries=None):
        self.entries = entries or {}
        
    def find_entry_by_dn(self, dn):
        return self.entries.get(dn)
        
    def cleanup(self):
        pass

# Usage in tests
def test_authentication_with_mock_storage(self):
    mock_entries = {
        "cn=test,dc=example,dc=com": MockEntry({"userPassword": "test123"})
    }
    storage = MockStorage(mock_entries)
    handler = BindHandler()
    
    result = handler.handle_bind("cn=test,dc=example,dc=com", "test123", storage)
    assert result is True
```

#### 🔧 **pytest Fixtures**
```python
import pytest
import tempfile
import json

@pytest.fixture
def temp_json_file():
    """Create temporary JSON file for testing."""
    data = {
        "base_dn": "dc=test,dc=com",
        "entries": [
            {
                "dn": "dc=test,dc=com",
                "objectClass": ["dcObject"],
                "dc": "test"
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        yield f.name
    
    os.unlink(f.name)

# Usage
def test_json_storage_loads_file(temp_json_file):
    storage = JSONStorage(temp_json_file, enable_watcher=False)
    assert storage.get_root().dn.getText() == "dc=test,dc=com"
    storage.cleanup()
```

### 🔒 **Testing Security Components**

#### 🔐 **Password Testing**
```python
def test_password_hashing_produces_bcrypt_format(self):
    """Test that password hashing produces valid bcrypt hashes."""
    pm = PasswordManager()
    password = "test_password_123"
    
    hashed = pm.hash_password(password)
    
    # Verify bcrypt format: $2b$rounds$salt+hash
    assert hashed.startswith("$2b$")
    assert len(hashed.split('$')) == 4
    
    # Verify password can be verified
    assert pm.verify_password(password, hashed)
    
    # Verify wrong password fails
    assert not pm.verify_password("wrong_password", hashed)
```

#### 🔑 **Authentication Testing**
```python
def test_bind_timing_attack_protection(self):
    """Test that authentication has consistent timing."""
    import time
    
    handler = BindHandler()
    storage = MemoryStorage()
    
    # Time authentication with valid user
    start_time = time.time()
    handler.handle_bind("cn=admin,ou=people,dc=example,dc=com", "wrong", storage)
    valid_user_time = time.time() - start_time
    
    # Time authentication with invalid user
    start_time = time.time()
    handler.handle_bind("cn=nonexistent,dc=example,dc=com", "wrong", storage)
    invalid_user_time = time.time() - start_time
    
    # Times should be similar (within reasonable variance)
    time_difference = abs(valid_user_time - invalid_user_time)
    assert time_difference < 0.1  # Less than 100ms difference
```

### 🔧 **Testing Twisted Components**

#### ⚡ **Async Testing with pytest-twisted**
```python
from twisted.trial import unittest
from twisted.test import proto_helpers

class TestCustomLDAPServer(unittest.TestCase):
    """Test LDAP server protocol handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.storage = MemoryStorage()
        self.factory = LDAPServerFactory(storage=self.storage, debug=False)
        self.protocol = self.factory.buildProtocol(("127.0.0.1", 12345))
        self.transport = proto_helpers.StringTransport()
        self.protocol.makeConnection(self.transport)
    
    def tearDown(self):
        """Clean up after tests."""
        self.factory.cleanup()
    
    def test_protocol_initialization(self):
        """Test that protocol initializes correctly."""
        self.assertIsInstance(self.protocol, CustomLDAPServer)
        self.assertEqual(self.protocol.factory, self.factory)
```

## 📊 **Test Coverage Analysis**

### 📈 **Generating Coverage Reports**
```bash
# Generate HTML coverage report
pytest tests/ --cov=src/ldap_server --cov-report=html

# Generate terminal coverage report
pytest tests/ --cov=src/ldap_server --cov-report=term-missing

# Generate XML coverage report (for CI)
pytest tests/ --cov=src/ldap_server --cov-report=xml
```

### 📋 **Coverage Targets**
- **Critical Components**: 100% coverage required
  - Authentication and security functions
  - Core server and protocol handling
  - Storage interface implementations
- **Non-Critical Components**: 90% coverage target
  - Utility functions and helpers
  - Configuration and setup code
- **Test Code**: No coverage requirements
  - Test utilities and fixtures
  - Mock implementations

### 📊 **Current Coverage Analysis**
```python
# Example coverage report interpretation
Name                               Stmts   Miss  Cover   Missing
----------------------------------------------------------------
src/ldap_server/__init__.py            5      0   100%
src/ldap_server/server.py             45      2    96%   123, 145
src/ldap_server/factory.py            32      0   100%
src/ldap_server/auth/password.py      67      1    99%   89
src/ldap_server/auth/bind.py           42      0   100%
src/ldap_server/storage/memory.py     38      1    97%   72
src/ldap_server/storage/json.py       89      3    97%   156, 178, 203
----------------------------------------------------------------
TOTAL                                 318      7    98%
```

## 🚀 **Performance Testing**

### ⏱️ **Benchmarking Tests**
```python
import time
import pytest

def test_authentication_performance():
    """Test that authentication completes within acceptable time."""
    handler = BindHandler()
    storage = MemoryStorage()
    
    start_time = time.time()
    
    # Perform 100 authentication attempts
    for i in range(100):
        handler.handle_bind("cn=admin,ou=people,dc=example,dc=com", "admin", storage)
    
    elapsed_time = time.time() - start_time
    avg_time_per_auth = elapsed_time / 100
    
    # Authentication should average under 10ms
    assert avg_time_per_auth < 0.01
```

### 📊 **Memory Usage Testing**
```python
import psutil
import os

def test_memory_usage_growth():
    """Test that memory usage doesn't grow excessively."""
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Perform operations that could cause memory leaks
    storage = MemoryStorage()
    for i in range(1000):
        storage.find_entry_by_dn("cn=admin,ou=people,dc=example,dc=com")
    
    final_memory = process.memory_info().rss
    memory_growth = final_memory - initial_memory
    
    # Memory growth should be minimal (under 10MB)
    assert memory_growth < 10 * 1024 * 1024
    
    storage.cleanup()
```

## 🔧 **Testing Configuration**

### ⚙️ **pytest Configuration**
```ini
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--strict-config",
    "--cov=src/ldap_server",
    "--cov-report=term-missing"
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "security: marks tests as security-related"
]
```

### 🏷️ **Test Markers**
```python
import pytest

@pytest.mark.slow
def test_large_directory_performance():
    """Test performance with large directory (marked as slow)."""
    pass

@pytest.mark.integration
def test_ldapsearch_compatibility():
    """Test compatibility with real ldapsearch client."""
    pass

@pytest.mark.security
def test_password_timing_attack_protection():
    """Test security features (marked as security)."""
    pass

# Run only fast tests
# pytest tests/ -m "not slow"

# Run only security tests  
# pytest tests/ -m security
```

## 🔄 **Continuous Integration**

### 🚀 **CI Test Strategy**
```yaml
# .github/workflows/test.yml (example)
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.12', '3.13']
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .[dev]
    
    - name: Run tests
      run: |
        pytest tests/ --cov=src/ldap_server --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## 📋 **Test Development Guidelines**

### ✅ **Test Checklist**
When adding new tests:
- [ ] Test follows AAA pattern (Arrange, Act, Assert)
- [ ] Test has descriptive name and docstring
- [ ] Test is isolated and doesn't depend on other tests
- [ ] Test cleans up resources (storage.cleanup())
- [ ] Test covers both success and failure cases
- [ ] Test includes edge cases and boundary conditions

### 🔧 **Common Testing Patterns**

#### 🏭 **Factory Pattern for Test Setup**
```python
def create_test_storage(entries=None):
    """Factory function for creating test storage."""
    if entries is None:
        entries = {
            "base_dn": "dc=test,dc=com",
            "entries": [
                {"dn": "dc=test,dc=com", "objectClass": ["dcObject"]}
            ]
        }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(entries, f)
    
    return JSONStorage(f.name, enable_watcher=False)
```

#### 🔄 **Context Manager for Resource Cleanup**
```python
from contextlib import contextmanager

@contextmanager
def temporary_storage(data):
    """Context manager for temporary storage with automatic cleanup."""
    storage = create_test_storage(data)
    try:
        yield storage
    finally:
        storage.cleanup()

# Usage
def test_with_temporary_storage():
    data = {"base_dn": "dc=test,dc=com", "entries": [...]}
    with temporary_storage(data) as storage:
        # Test code here
        result = storage.find_entry_by_dn("dc=test,dc=com")
        assert result is not None
    # Automatic cleanup happens here
```

## 🎯 **Future Testing Plans**

### 🚧 **Phase 2 Testing Additions**
- **LDAP Filter Testing**: Comprehensive filter parsing tests
- **Schema Validation Testing**: Schema constraint tests
- **Integration Testing**: Real LDAP client compatibility tests

### 🔮 **Phase 3 Testing Additions**
- **Write Operation Testing**: Add/modify/delete operation tests
- **Performance Testing**: Load testing and benchmarking
- **Security Testing**: Penetration testing and security validation

### 🚀 **Phase 4 Testing Additions**
- **End-to-End Testing**: Complete workflow testing
- **API Testing**: REST API endpoint testing
- **Deployment Testing**: Container and production deployment tests

---

**Testing Status**: Comprehensive unit test coverage (42 tests, 100% pass rate)  
**Next Priority**: Integration testing with real LDAP clients (Phase 2)  
**Test Philosophy**: Fast, reliable, comprehensive coverage of critical components  
**Last Updated**: September 7, 2025

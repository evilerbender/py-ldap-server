# Contributing to py-ldap-server

Thank you for your interest in contributing to py-ldap-server! This guide will help you get started with contributing to the project, whether you're fixing bugs, adding features, or improving documentation.

## 🚀 **Getting Started**

### � **Prerequisites**

Before contributing to py-ldap-server, ensure you have:

- **Python 3.12+** - Modern Python with enhanced type hints and async support
- **Git** - Version control system
- **Virtual Environment** - For isolated development
- **Basic LDAP Knowledge** - Understanding of LDAP concepts helpful

### 🛠️ **Development Environment Setup**

#### 1️⃣ **Clone and Setup**
```bash
# Fork the repository on GitHub first, then clone your fork
git clone https://github.com/YOUR_USERNAME/py-ldap-server.git
cd py-ldap-server

# Add upstream remote for syncing
git remote add upstream https://github.com/evilerbender/py-ldap-server.git
```

#### 2️⃣ **Create Virtual Environment**
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

#### 3️⃣ **Install Dependencies**
```bash
# Install development dependencies
pip install -e .[dev]

# Verify installation
py-ldap-server --help
pytest --version
```

#### 4️⃣ **Verify Setup**
```bash
# Run tests to ensure everything works
pytest tests/ -v

# Start development server
py-ldap-server --port 1389 --debug

# Test basic functionality
ldapsearch -x -H ldap://localhost:1389 -b "dc=example,dc=com" -s base
```

## 📋 **Coding Standards**

### 🎨 **Code Style**
We use automated tools to maintain consistent code style:

```bash
# Format code with black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Lint with flake8
flake8 src/ tests/

# Type checking with mypy
mypy src/
```

### 📏 **Style Guidelines**
- **Line Length**: 88 characters (black default)
- **Import Sorting**: Standard library, third-party, local imports
- **Type Hints**: Required for all new functions and methods
- **Docstrings**: Google-style docstrings for all public APIs

#### Example Code Style:
```python
from typing import Optional, List
import json

from ldaptor.protocols.ldap.ldiftree import LDIFTreeEntry

from ldap_server.auth.password import PasswordManager


class JSONStorage:
    """JSON file-based storage backend for LDAP directory data.
    
    This storage backend provides persistent storage using JSON files
    with automatic password upgrade and hot reload capabilities.
    
    Args:
        json_file: Path to JSON file containing directory data
        enable_watcher: Enable automatic file watching and reload
        
    Example:
        storage = JSONStorage("directory.json", enable_watcher=True)
        root = storage.get_root()
    """
    
    def __init__(self, json_file: str, enable_watcher: bool = True) -> None:
        self.json_file = json_file
        self.enable_watcher = enable_watcher
        self._load_data()
    
    def find_entry_by_dn(self, dn: str) -> Optional[LDIFTreeEntry]:
        """Find directory entry by distinguished name.
        
        Args:
            dn: Distinguished name to search for
            
        Returns:
            LDIFTreeEntry if found, None otherwise
        """
        # Implementation here
        pass
```

### 🧪 **Testing Standards**
- **Test Coverage**: All new code must have tests
- **Test Types**: Unit tests for components, integration tests for workflows
- **Test Naming**: Descriptive test method names
- **Test Documentation**: Clear docstrings explaining test purpose

#### Example Test:
```python
class TestJSONStorage:
    """Test cases for JSONStorage backend."""
    
    def test_load_valid_json_file(self):
        """Test that JSONStorage correctly loads valid JSON data."""
        # Arrange
        data = {
            "base_dn": "dc=test,dc=com",
            "entries": [{"dn": "dc=test,dc=com", "objectClass": ["dcObject"]}]
        }
        
        # Act
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            
        storage = JSONStorage(f.name, enable_watcher=False)
        
        # Assert
        assert storage.get_root().dn.getText() == "dc=test,dc=com"
        
        # Cleanup
        storage.cleanup()
        os.unlink(f.name)
```

## 🔀 **Git Workflow**

### 🌿 **Branching Strategy**
We use a feature branch workflow:

```bash
# Sync with upstream
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/ldap-filter-parsing

# Make your changes
# ... code, test, commit ...

# Push to your fork
git push origin feature/ldap-filter-parsing

# Create pull request on GitHub
```

### 📝 **Commit Message Format**
Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (no logic changes)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(storage): add database storage backend

Implement PostgreSQL storage backend with connection pooling
and transaction support for Phase 3 write operations.

Closes #42

fix(auth): handle empty password in simple bind

Empty passwords should be rejected for non-anonymous binds
according to RFC 4513 section 5.1.1.

test(json): add comprehensive JSON storage test suite

Add 7 new test cases covering file loading, error handling,
and cleanup scenarios for JSONStorage backend.
```

### 📋 **Pull Request Process**

#### 1️⃣ **Before Submitting**
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Code is formatted: `black src/ tests/`
- [ ] Imports are sorted: `isort src/ tests/`
- [ ] No linting errors: `flake8 src/ tests/`
- [ ] Type checking passes: `mypy src/`
- [ ] Documentation updated if needed

#### 2️⃣ **PR Description Template**
```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that breaks existing functionality)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added for new functionality
- [ ] All tests pass
```

## 🐛 **Bug Reports**

### 📋 **Bug Report Template**
When reporting bugs, please include:

```markdown
## Bug Description
Clear description of the bug and expected behavior.

## Environment
- OS: [e.g., Ubuntu 20.04, macOS 12.0, Windows 11]
- Python Version: [e.g., 3.12.2]
- py-ldap-server Version: [e.g., 0.1.0]
- LDAP Client: [e.g., ldapsearch 2.4.57]

## Steps to Reproduce
1. Start server with: `py-ldap-server --port 1389`
2. Run command: `ldapsearch -x -H ldap://localhost:1389 ...`
3. Observe error: ...

## Expected Behavior
What should happen instead.

## Actual Behavior
What actually happens, including error messages.

## Logs
```
Include relevant server logs with debug enabled
```

## Additional Context
Any other context about the problem.
```

### 🔍 **Before Reporting**
- Search existing issues to avoid duplicates
- Test with latest version if possible
- Include minimal reproduction case
- Test with debug mode enabled

## 💡 **Feature Requests**

### 📋 **Feature Request Template**
```markdown
## Feature Description
Clear description of the proposed feature.

## Problem Solved
What problem does this feature solve?

## Proposed Solution
How should this feature work?

## Alternative Solutions
Other approaches considered.

## Implementation Notes
Technical considerations or suggestions.

## Priority
- [ ] Low - Nice to have
- [ ] Medium - Would improve workflow
- [ ] High - Blocking current work
```

### 🎯 **Feature Guidelines**
- Features should align with project roadmap
- Consider Phase 2/3/4 priorities
- RFC compliance is important
- Maintain backward compatibility
- Include comprehensive tests

## ❓ **Getting Help**

### 💬 **Communication Channels**
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and general discussion
- **Pull Request Comments**: Code review and implementation questions

### 📚 **Documentation Resources**
- **[📖 Architecture Guide](architecture.md)** - Understanding the codebase
- **[🧪 Testing Guide](testing.md)** - Testing practices and tools
- **[📋 Roadmap](roadmap.md)** - Project phases and priorities
- **[📚 API Documentation](../api/README.md)** - Technical API reference

### 🆘 **Common Questions**

#### Q: How do I add a new storage backend?
A: Implement the `StorageBackend` interface and add tests. See [Storage Architecture](../api/storage/README.md).

#### Q: Where should I add LDAP filter parsing?
A: This is a Phase 2 priority. See [Protocol Handlers](../api/handlers/README.md) for the planned architecture.

#### Q: How do I test authentication changes?
A: Use the comprehensive test suite in `tests/unit/test_bind.py` and `tests/unit/test_password.py`.

#### Q: What LDAP RFCs should I follow?
A: Primary: RFC 4511 (protocol), RFC 4515 (filters), RFC 4519 (schema). See [Architecture](architecture.md#-rfc-compliance).

## 🎯 **Development Priorities**

### 🚧 **Phase 2 Focus** (Current)
1. **LDAP Filter Parsing** - RFC 4515 implementation
2. **Search Scope Enhancement** - One-level and subtree search
3. **Schema Validation** - Basic objectClass and attribute validation

### 📋 **Good First Issues**
- Documentation improvements
- Additional test cases
- Code style and typing improvements
- Example configurations

### 🔥 **High Impact Areas**
- LDAP protocol compliance
- Performance optimizations
- Security enhancements
- Test coverage improvements

## 🏆 **Recognition**

Contributors are recognized in:
- **CHANGELOG.md** - All contributions noted in release notes
- **README.md** - Major contributors acknowledged
- **Git History** - Permanent record of contributions

## 📄 **License**

By contributing to py-ldap-server, you agree that your contributions will be licensed under the MIT License.

## 🤝 **Code of Conduct**

We expect all contributors to:
- Be respectful and inclusive
- Provide constructive feedback
- Focus on what's best for the project
- Help others learn and grow

---

**Thank you for contributing to py-ldap-server!**

**Questions?** Open a [GitHub Discussion](https://github.com/evilerbender/py-ldap-server/discussions) or reach out in an issue.

**Last Updated**: September 7, 2025

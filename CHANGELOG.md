# Changelog

All notable changes to py-ldap-server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-09-07

### Added
- **Comprehensive Documentation Structure**: 21 new documentation files across 9 directories
  - User guides (quick-start, configuration, authentication)
  - Complete API documentation for all components
  - Development documentation (architecture, contributing, testing, roadmap)
  - Deployment guides with security hardening
  - Example configurations and templates
- **Enhanced Authentication System**: 
  - New BindHandler class for LDAP bind operations
  - Comprehensive password management with bcrypt security
  - Support for anonymous and simple bind authentication
- **Unified JSON Storage Backend**: 
  - **BREAKING**: Consolidated JSONStorage and FederatedJSONStorage into single unified implementation
  - Single-file and multi-file federation support in one class
  - Atomic write operations with file locking and backup support
  - File watching with hot reload capabilities
  - Read-only mode for externally managed configurations
  - Thread-safe concurrent access protection
  - Enhanced error handling and graceful degradation
- **Enhanced Testing Framework**: 
  - Expanded from 6 to 72 comprehensive unit tests
  - New atomic write operation test suite (19 tests)
  - New unified JSON storage test suite (18 tests)
  - New mock storage backend for isolated testing
  - Dedicated test suites for authentication and storage
- **Developer Experience Improvements**:
  - VSCode integration with optimized settings
  - Enhanced type hints throughout codebase
  - Improved error handling and user feedback
  - Warning-free test execution

### Changed
- **Python Version Requirement**: Updated minimum from Python 3.8+ to Python 3.12+
- **Project Configuration**: Modernized pyproject.toml with updated tool configurations
- **Code Organization**: Better separation of concerns with new handler modules
- **Documentation Structure**: Reorganized SystemD docs into deployment section
- **Storage Architecture**: **BREAKING** - Unified JSON storage implementation replacing separate backends
- **Version Bump**: 0.1.0 → 0.2.0 (minor version increment for significant additions)

### Improved
- **Storage Interface**: Enhanced with consistent get_root() method pattern
- **Error Handling**: More descriptive error messages and proper exception handling
- **Code Quality**: Enhanced type annotations and documentation
- **Test Coverage**: Significantly improved with 72 comprehensive unit tests
- **File Watcher**: Enhanced to handle temporary files gracefully without warnings
- **Data Integrity**: Atomic write operations ensure data consistency

### Removed
- **Obsolete Files**: Removed test_phase1.py (replaced by comprehensive unit tests)
- **Redundant Code**: Eliminated separate JSON and Federated storage implementations
- **Development Artifacts**: Cleaned up temporary files and development leftovers

### Fixed
- **File Watcher Warnings**: Resolved file system event warnings during atomic operations
- **Test Suite**: All 72 tests pass without warnings
- **Documentation**: Updated all references to reflect unified storage approach

### Technical Details
- **Storage Consolidation**: Single JSONStorage class with 808 lines supporting all use cases
- **Test Expansion**: From 42 to 72 comprehensive unit tests
- **Atomic Operations**: Thread-safe writes with file locking and backup creation
- **Hot Reload**: File watching with debounced change detection
- **Architecture**: Enhanced modular design with clear separation of concerns
- **Testing**: Full backward compatibility maintained for LDAP protocol
- **Performance**: Python 3.12+ performance improvements and latest security patches

### Documentation Highlights
- **Multi-Audience Design**: Separate documentation for users, developers, and administrators
- **Progressive Complexity**: From quick-start to deep technical details
- **Cross-Referenced**: Bidirectional links between related sections
- **Mirror Code Structure**: Documentation hierarchy matches codebase organization

This release establishes a professional foundation for py-ldap-server with comprehensive documentation, modern Python requirements, and enhanced developer experience, preparing the project for Phase 2 development.

## [0.1.0] - 2025-07-29

### Added
- Initial release of py-ldap-server
- Complete LDAP server implementation using Ldaptor and Twisted
- Anonymous LDAP access support
- Base and subtree search operations
- In-memory storage with sample organizational directory
- Command-line interface (`py-ldap-server`)
- Comprehensive unit test suite (6 tests, 62% coverage)
- Integration test for server functionality
- Modern Python packaging with pyproject.toml
- Development tools (pytest, black, isort, flake8, mypy)
- GitHub Copilot instructions for AI-assisted development
- Comprehensive documentation (README, release notes)

### Technical Details
- CustomLDAPServer extending Ldaptor's LDAPServer
- LDAPServerFactory with Twisted integration
- MemoryStorage using LDIFTreeEntry
- Sample directory with 7 entries (users, groups, organizational units)
- Clean codebase with deprecation warnings properly handled

### Phase 1 MVP Complete
All Phase 1 success criteria met:
- ✅ Server starts and accepts connections
- ✅ LDAP search operations work with real clients
- ✅ Sample directory accessible via ldapsearch
- ✅ All tests pass without warnings
- ✅ Ready for Phase 2 development

[0.2.0]: https://github.com/evilerbender/py-ldap-server/releases/tag/v0.2.0
[0.1.0]: https://github.com/evilerbender/py-ldap-server/releases/tag/v0.1.0

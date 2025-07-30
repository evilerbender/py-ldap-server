# Changelog

All notable changes to py-ldap-server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/evilerbender/py-ldap-server/releases/tag/v0.1.0

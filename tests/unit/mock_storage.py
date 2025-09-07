"""
Mock storage backend for testing LDAP bind functionality.
"""

from typing import Dict, Any, Optional


class MockLDAPEntry:
    """Mock LDAP entry for testing."""
    
    def __init__(self, dn: str, attributes: Dict[str, Any]):
        self.dn = dn
        self.attributes = attributes
    
    def get(self, attr_name: str, default=None):
        """Get attribute value(s)."""
        return self.attributes.get(attr_name, default)


class MockRoot:
    """Mock root entry to satisfy LDAPServerFactory."""
    
    def __init__(self):
        self.dn = MockDN()
    
    def getText(self):
        return ""


class MockDN:
    """Mock DN object."""
    
    def getText(self):
        return "dc=example,dc=com"


class MockStorage:
    """Mock storage backend for testing."""
    
    def __init__(self, data: Dict[str, Any] = None):
        """Initialize with test data."""
        self.data = data or {}
        self.root = MockRoot()  # Satisfy LDAPServerFactory requirements
    
    def find_entry(self, dn: str) -> Optional[MockLDAPEntry]:
        """Find entry by DN."""
        normalized_dn = dn.lower().strip()
        
        # Look for exact match first
        for stored_dn, attributes in self.data.items():
            if stored_dn.lower().strip() == normalized_dn:
                return MockLDAPEntry(stored_dn, attributes)
        
        # No entry found
        return None

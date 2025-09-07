"""
Test cases for LDAP bind authentication functionality.
"""

import pytest
from twisted.test import proto_helpers
from ldaptor.protocols.pureldap import LDAPBindRequest, LDAPBindResponse

from ldap_server.factory import LDAPServerFactory, CustomLDAPServer
from ldap_server.storage.memory import MemoryStorage
from ldap_server.handlers.bind import BindHandler
from ldap_server.auth.password import PasswordManager
from tests.unit.mock_storage import MockStorage


class TestBindHandler:
    """Test cases for BindHandler."""
    
    @pytest.fixture
    def setup(self):
        """Set up test fixtures."""
        # Create test storage with sample data
        test_data = {
            "dc=example,dc=com": {
                "objectClass": ["domain"],
                "dc": ["example"]
            },
            "ou=people,dc=example,dc=com": {
                "objectClass": ["organizationalUnit"],
                "ou": ["people"]
            },
            "uid=admin,ou=people,dc=example,dc=com": {
                "objectClass": ["inetOrgPerson"],
                "uid": ["admin"],
                "cn": ["Administrator"],
                "sn": ["Admin"],
                "userPassword": ["{BCRYPT}JDJiJDEyJFJoUHVGZ2lzLzN4Vnd5aEx3UHFjTE9yV1ltRTdxWXRkSnoyRFBCTFJXaTVMTzBzUGpQeGZh"]  # admin123
            },
            "uid=user,ou=people,dc=example,dc=com": {
                "objectClass": ["inetOrgPerson"],
                "uid": ["user"],
                "cn": ["Regular User"],
                "sn": ["User"],
                "userPassword": ["{BCRYPT}JDJiJDEyJFJoUHVGZ2lzLzN4Vnd5aEx3UHFjTE9yV1ltRTdxWXRkSnoyRFBCTFJXaTVMTzBzUGpQeGZh"]  # admin123
            }
        }
        
        storage = MockStorage(test_data)
        password_manager = PasswordManager()
        bind_handler = BindHandler(storage, password_manager, debug=False)  # Disable debug for cleaner test output
        
        return {
            'storage': storage,
            'password_manager': password_manager,
            'bind_handler': bind_handler
        }
    
    def test_anonymous_bind(self, setup):
        """Test anonymous bind (empty DN and password)."""
        bind_handler = setup['bind_handler']
        result = bind_handler.handle_simple_bind("", "")
        assert result == (0, "Anonymous bind successful")
    
    def test_simple_bind_success(self, setup):
        """Test successful simple bind with valid credentials."""
        bind_handler = setup['bind_handler']
        dn = "uid=admin,ou=people,dc=example,dc=com"
        password = "admin123"
        result = bind_handler.handle_simple_bind(dn, password)
        assert result == (0, "Authentication successful")
    
    def test_simple_bind_invalid_dn(self, setup):
        """Test simple bind with non-existent DN."""
        bind_handler = setup['bind_handler']
        dn = "uid=nonexistent,ou=people,dc=example,dc=com"
        password = "admin123"
        result = bind_handler.handle_simple_bind(dn, password)
        assert result == (32, "No such object")  # LDAP_NO_SUCH_OBJECT
    
    def test_simple_bind_wrong_password(self, setup):
        """Test simple bind with wrong password."""
        bind_handler = setup['bind_handler']
        dn = "uid=admin,ou=people,dc=example,dc=com"
        password = "wrongpassword"
        result = bind_handler.handle_simple_bind(dn, password)
        assert result == (49, "Invalid credentials")  # LDAP_INVALID_CREDENTIALS
    
    def test_simple_bind_no_password_attribute(self, setup):
        """Test simple bind with DN that has no userPassword attribute."""
        bind_handler = setup['bind_handler']
        dn = "ou=people,dc=example,dc=com"  # This entry has no userPassword
        password = "anypassword"
        result = bind_handler.handle_simple_bind(dn, password)
        assert result == (49, "Invalid credentials")
    
    def test_simple_bind_malformed_dn(self, setup):
        """Test simple bind with malformed DN."""
        bind_handler = setup['bind_handler']
        dn = "invalid-dn-format"
        password = "admin123"
        result = bind_handler.handle_simple_bind(dn, password)
        assert result == (34, "Invalid DN syntax")  # LDAP_INVALID_DN_SYNTAX
    
    def test_simple_bind_empty_password_non_anonymous(self, setup):
        """Test simple bind with valid DN but empty password (should fail)."""
        bind_handler = setup['bind_handler']
        dn = "uid=admin,ou=people,dc=example,dc=com"
        password = ""
        result = bind_handler.handle_simple_bind(dn, password)
        assert result == (49, "Invalid credentials")


class TestCustomLDAPServerBind:
    """Test cases for CustomLDAPServer bind handling."""
    
    @pytest.fixture
    def setup(self):
        """Set up test fixtures."""
        # Create test storage with sample data
        test_data = {
            "dc=example,dc=com": {
                "objectClass": ["domain"],
                "dc": ["example"]
            },
            "uid=admin,ou=people,dc=example,dc=com": {
                "objectClass": ["inetOrgPerson"],
                "uid": ["admin"],
                "cn": ["Administrator"],
                "sn": ["Admin"],
                "userPassword": ["{BCRYPT}JDJiJDEyJFJoUHVGZ2lzLzN4Vnd5aEx3UHFjTE9yV1ltRTdxWXRkSnoyRFBCTFJXaTVMTzBzUGpQeGZh"]  # admin123
            }
        }
        
        # Create factory and server using mock storage
        storage = MockStorage(test_data)
        factory = LDAPServerFactory(storage)
        factory.protocol = CustomLDAPServer
        
        # Create protocol instance
        protocol = factory.buildProtocol(('127.0.0.1', 0))
        transport = proto_helpers.StringTransport()
        protocol.makeConnection(transport)
        
        return {
            'factory': factory,
            'protocol': protocol,
            'transport': transport
        }
    
    def test_anonymous_bind_request(self, setup):
        """Test handling of anonymous bind request."""
        protocol = setup['protocol']
        
        # Create anonymous bind request
        bind_request = LDAPBindRequest(dn=b"", auth=b"", version=3)  # Empty credentials for anonymous
        
        # Create mock reply function
        replies = []
        def mock_reply(response):
            replies.append(response)
        
        # Handle the bind request
        protocol.handle_LDAPBindRequest(bind_request, [], mock_reply)
        
        # Check response
        assert len(replies) == 1
        response = replies[0]
        assert response.resultCode == 0  # Success
        assert protocol.authenticated_dn is None  # Anonymous
    
    def test_simple_bind_success(self, setup):
        """Test successful simple bind."""
        protocol = setup['protocol']
        
        # Create simple bind request with valid credentials
        bind_request = LDAPBindRequest(dn=b"uid=admin,ou=people,dc=example,dc=com", auth=b"admin123", version=3)
        
        # Create mock reply function
        replies = []
        def mock_reply(response):
            replies.append(response)
        
        # Handle the bind request
        protocol.handle_LDAPBindRequest(bind_request, [], mock_reply)
        
        # Check response
        assert len(replies) == 1
        response = replies[0]
        assert response.resultCode == 0  # Success
        assert protocol.authenticated_dn == "uid=admin,ou=people,dc=example,dc=com"
    
    def test_simple_bind_failure(self, setup):
        """Test failed simple bind with wrong password."""
        protocol = setup['protocol']
        
        # Create simple bind request with invalid credentials
        bind_request = LDAPBindRequest(dn=b"uid=admin,ou=people,dc=example,dc=com", auth=b"wrongpassword", version=3)
        
        # Create mock reply function
        replies = []
        def mock_reply(response):
            replies.append(response)
        
        # Handle the bind request
        protocol.handle_LDAPBindRequest(bind_request, [], mock_reply)
        
        # Check response
        assert len(replies) == 1
        response = replies[0]
        assert response.resultCode == 49  # Invalid credentials
        assert protocol.authenticated_dn is None  # Not authenticated
    
    def test_connection_lost_clears_auth(self, setup):
        """Test that losing connection clears authentication state."""
        protocol = setup['protocol']
        
        # First authenticate
        bind_request = LDAPBindRequest(dn=b"uid=admin,ou=people,dc=example,dc=com", auth=b"admin123", version=3)
        
        replies = []
        def mock_reply(response):
            replies.append(response)
        
        protocol.handle_LDAPBindRequest(bind_request, [], mock_reply)
        
        # Verify authentication succeeded
        assert protocol.authenticated_dn == "uid=admin,ou=people,dc=example,dc=com"
        
        # Simulate connection loss
        protocol.connectionLost("test reason")
        
        # Verify authentication state is cleared
        assert protocol.authenticated_dn is None


class TestBindIntegration:
    """Integration tests for bind functionality."""
    
    @pytest.fixture
    def setup(self):
        """Set up test fixtures."""
        # Create test storage with sample data
        test_data = {
            "dc=example,dc=com": {
                "objectClass": ["domain"],
                "dc": ["example"]
            },
            "uid=admin,ou=people,dc=example,dc=com": {
                "objectClass": ["inetOrgPerson"],
                "uid": ["admin"],
                "cn": ["Administrator"],
                "sn": ["Admin"],
                "userPassword": ["{BCRYPT}JDJiJDEyJFJoUHVGZ2lzLzN4Vnd5aEx3UHFjTE9yV1ltRTdxWXRkSnoyRFBCTFJXaTVMTzBzUGpQeGZh"]  # admin123
            }
        }
        
        storage = MockStorage(test_data)
        password_manager = PasswordManager()
        
        return {
            'storage': storage,
            'password_manager': password_manager
        }
    
    def test_bind_handler_integration_with_storage(self, setup):
        """Test that bind handler correctly integrates with storage backend."""
        storage = setup['storage']
        password_manager = setup['password_manager']
        
        bind_handler = BindHandler(storage, password_manager)
        
        # Test successful authentication
        result = bind_handler.handle_simple_bind("uid=admin,ou=people,dc=example,dc=com", "admin123")
        assert result[0] == 0  # Success
        
        # Test failed authentication
        result = bind_handler.handle_simple_bind("uid=admin,ou=people,dc=example,dc=com", "wrongpassword")
        assert result[0] == 49  # Invalid credentials
    
    def test_factory_bind_handler_integration(self, setup):
        """Test that factory correctly integrates bind handler."""
        storage = setup['storage']
        
        factory = LDAPServerFactory(storage)
        factory.protocol = CustomLDAPServer
        
        # Create protocol and make connection to trigger bind_handler creation
        protocol = factory.buildProtocol(('127.0.0.1', 0))
        transport = proto_helpers.StringTransport()
        protocol.makeConnection(transport)
        
        # Verify bind handler is created
        assert protocol.bind_handler is not None
        assert isinstance(protocol.bind_handler, BindHandler)

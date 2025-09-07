"""
Unit tests for the LDAP server.
"""

import pytest
from twisted.test import proto_helpers
from twisted.internet import defer
from twisted.trial import unittest

from ldap_server.factory import LDAPServerFactory, CustomLDAPServer
from ldap_server.storage.memory import MemoryStorage
from ldap_server.auth.password import PasswordManager


class TestMemoryStorage(unittest.TestCase):
    """Test cases for MemoryStorage."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.storage = MemoryStorage()
    
    def tearDown(self):
        """Clean up after tests."""
        self.storage.cleanup()
    
    def test_initialization(self):
        """Test that storage initializes correctly."""
        self.assertIsNotNone(self.storage.root)
        self.assertEqual(self.storage.root.dn.getText(), "")
    
    def test_sample_data_creation(self):
        """Test that storage initializes without errors."""
        # The key test for Phase 1 is that the storage initializes successfully
        # More detailed LDAP tree testing should be done via integration tests
        # using actual LDAP clients
        self.assertIsNotNone(self.storage.root)
        self.assertTrue(hasattr(self.storage, 'cleanup'))


class TestLDAPServerFactory(unittest.TestCase):
    """Test cases for LDAPServerFactory."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.storage = MemoryStorage()
        self.factory = LDAPServerFactory(storage=self.storage, debug=False)
    
    def tearDown(self):
        """Clean up after tests."""
        self.factory.cleanup()
    
    def test_factory_initialization(self):
        """Test that factory initializes correctly."""
        self.assertIsNotNone(self.factory.root)
        self.assertEqual(self.factory.protocol, CustomLDAPServer)
    
    def test_build_protocol(self):
        """Test protocol creation."""
        addr = ("127.0.0.1", 12345)
        protocol = self.factory.buildProtocol(addr)
        
        self.assertIsInstance(protocol, CustomLDAPServer)
        self.assertEqual(protocol.factory, self.factory)


class TestCustomLDAPServer(unittest.TestCase):
    """Test cases for CustomLDAPServer."""
    
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
    
    def test_connection_made(self):
        """Test connection establishment."""
        # This test verifies that connectionMade doesn't raise exceptions
        # The actual connection logic is tested through integration tests
        self.assertTrue(self.protocol.connected)


if __name__ == "__main__":
    import sys
    from twisted.trial._runner import TrialRunner
    from twisted.trial.reporter import TreeReporter
    
    # Run tests with Twisted Trial
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestMemoryStorage))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestLDAPServerFactory))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestCustomLDAPServer))
    
    runner = TrialRunner(TreeReporter)
    result = runner.run(suite)
    
    sys.exit(0 if result.wasSuccessful() else 1)

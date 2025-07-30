"""
LDAP Server Factory implementation using Ldaptor.
"""

from twisted.internet.protocol import ServerFactory
from twisted.python import log
from twisted.python.components import registerAdapter

from ldaptor.interfaces import IConnectedLDAPEntry
from ldaptor.protocols.ldap.ldapserver import LDAPServer

from ldap_server.storage.memory import MemoryStorage


class CustomLDAPServer(LDAPServer):
    """
    Custom LDAP Server extending Ldaptor's LDAPServer.
    """
    
    def __init__(self):
        super().__init__()
        self.debug = False
    
    def connectionMade(self):
        """Called when a connection is established."""
        super().connectionMade()
        if self.debug:
            log.msg(f"LDAP connection established from {self.transport.getPeer()}")
    
    def connectionLost(self, reason):
        """Called when a connection is lost."""
        super().connectionLost(reason)
        if self.debug:
            log.msg(f"LDAP connection lost from {self.transport.getPeer()}: {reason}")


class LDAPServerFactory(ServerFactory):
    """
    Factory for creating LDAP server protocol instances.
    """
    
    protocol = CustomLDAPServer
    _adapter_registered = False  # Class variable to track adapter registration
    
    def __init__(self, storage: MemoryStorage = None, debug: bool = True):
        """
        Initialize the LDAP server factory.
        
        Args:
            storage: Storage backend to use (defaults to MemoryStorage)
            debug: Enable debug logging
        """
        self.debug = debug
        
        if storage is None:
            storage = MemoryStorage()
        
        self.storage = storage
        self.root = storage.get_root()
        
        # Register adapter only once globally
        if not LDAPServerFactory._adapter_registered:
            registerAdapter(
                lambda factory: factory.root,
                LDAPServerFactory,
                IConnectedLDAPEntry
            )
            LDAPServerFactory._adapter_registered = True
        
        if self.debug:
            log.msg("LDAP Server Factory initialized")
            log.msg(f"Root DN: {self.root.dn.getText()}")
    
    def buildProtocol(self, addr):
        """
        Create a new protocol instance for each connection.
        
        Args:
            addr: The address of the connecting client
            
        Returns:
            CustomLDAPServer instance
        """
        protocol = self.protocol()
        protocol.factory = self
        protocol.debug = self.debug
        
        if self.debug:
            log.msg(f"Creating LDAP protocol for {addr}")
        
        return protocol
    
    def cleanup(self):
        """Clean up resources when shutting down."""
        if hasattr(self.storage, 'cleanup'):
            self.storage.cleanup()

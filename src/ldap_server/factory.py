"""
LDAP Server Factory implementation using Ldaptor.
"""

from twisted.internet.protocol import ServerFactory
from twisted.python import log
from twisted.python.components import registerAdapter

from ldaptor.interfaces import IConnectedLDAPEntry
from ldaptor.protocols.ldap.ldapserver import LDAPServer
from ldaptor.protocols.pureldap import LDAPBindRequest, LDAPBindResponse
from ldaptor.protocols.ldap import ldaperrors

from ldap_server.storage.memory import MemoryStorage
from ldap_server.handlers.bind import BindHandler
from ldap_server.auth.password import PasswordManager


class CustomLDAPServer(LDAPServer):
    """
    Custom LDAP Server extending Ldaptor's LDAPServer.
    """
    
    def __init__(self):
        super().__init__()
        self.debug = False
        self.bind_handler = None
        self.authenticated_dn = None  # Track authenticated user
    
    def connectionMade(self):
        """Called when a connection is established."""
        super().connectionMade()
        if self.debug:
            log.msg(f"LDAP connection established from {self.transport.getPeer()}")
        
        # Initialize bind handler when connection is made
        if hasattr(self.factory, 'storage'):
            password_manager = PasswordManager()
            self.bind_handler = BindHandler(self.factory.storage, password_manager, self.debug)
    
    def connectionLost(self, reason):
        """Called when a connection is lost."""
        super().connectionLost(reason)
        if self.debug:
            log.msg(f"LDAP connection lost from {self.transport.getPeer()}: {reason}")
        
        # Clear authentication state
        self.authenticated_dn = None
    
    def handle_LDAPBindRequest(self, request, controls, reply):
        """
        Handle LDAP bind requests with authentication.
        
        Args:
            request: LDAPBindRequest object
            controls: LDAP controls
            reply: Reply function
        """
        if self.debug:
            log.msg(f"Bind request received: DN={request.dn}, auth={request.auth}")
        
        # Initialize bind handler if not available
        if not self.bind_handler and hasattr(self.factory, 'storage'):
            password_manager = PasswordManager()
            self.bind_handler = BindHandler(self.factory.storage, password_manager, self.debug)
        
        if not self.bind_handler:
            # No storage available, reject bind
            response = LDAPBindResponse(resultCode=ldaperrors.LDAPUnavailable.resultCode,
                                     matchedDN='',
                                     errorMessage='Server not properly configured')
            reply(response)
            return
        
        try:
            # Extract DN and password from request
            dn_str = request.dn.decode('utf-8') if isinstance(request.dn, bytes) else str(request.dn)
            password = request.auth.decode('utf-8') if isinstance(request.auth, bytes) else str(request.auth)
            
            # Handle simple bind
            result_code, message = self.bind_handler.handle_simple_bind(dn_str, password)
            
            if result_code == 0:
                self.authenticated_dn = dn_str if dn_str else None  # None for anonymous
                if self.debug:
                    log.msg(f"Authentication successful for: {dn_str or 'anonymous'}")
            else:
                self.authenticated_dn = None
                if self.debug:
                    log.msg(f"Authentication failed for: {dn_str} - {message}")
            
            response = LDAPBindResponse(resultCode=result_code,
                                      matchedDN='',
                                      errorMessage=message)
            reply(response)
                
        except Exception as e:
            # Handle any unexpected errors
            self.authenticated_dn = None
            if self.debug:
                log.msg(f"Error handling bind request: {e}")
            
            response = LDAPBindResponse(resultCode=ldaperrors.LDAPOperationsError.resultCode,
                                      matchedDN='',
                                      errorMessage='Internal server error')
            reply(response)


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
